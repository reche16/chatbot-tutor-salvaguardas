"""ServicoPLN: adaptador do serviço externo de linguagem natural (Seção 4.3.2, RNF06).

É o único componente que conhece o provedor. Há duas implementações:
- PLNAnthropic: Claude API (modelo configurado, padrão claude-haiku-5-5);
- PLNSimulado: sem chamada externa, determinística, para desenvolvimento e
  testes enquanto não há chave de API. Ela NÃO serve para os resultados do Cap. 5.
"""
import asyncio
import concurrent.futures
import functools
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field

from django.conf import settings

from .recuperacao import classificar_local

log = logging.getLogger("tutor.pln")


class ErroPLN(Exception):
    """Falha do serviço externo. motivo: timeout, indisponivel, cota ou recusa."""

    def __init__(self, motivo, detalhe=""):
        super().__init__(f"{motivo}: {detalhe}")
        self.motivo = motivo


@dataclass
class Interpretacao:
    intencao: str
    topico_ordem: int | None
    confianca: float


@dataclass
class Geracao:
    texto: str
    tokens_entrada: int = 0
    tokens_saida: int = 0


@dataclass
class RequisicaoPLN:
    """O que o controlador manda ao serviço. Os testes de RN06/RN07 inspecionam isto."""

    modo: str  # interpretar | responder | orientar | base
    sistema: str
    mensagens: list
    contexto: dict = field(default_factory=dict)

    def texto_completo(self):
        return self.sistema + "\n" + json.dumps(self.mensagens, ensure_ascii=False)


# ----------------------------------------------------------------- limitador

class Limitador:
    """Limite de requisições por minuto (balde de fichas).

    Com REDIS_URL, o balde é compartilhado entre processos (Seção 4.3.5);
    sem Redis, vale só para o processo atual.
    """

    def __init__(self, por_minuto):
        self.capacidade = max(1, por_minuto)
        self.taxa = self.capacidade / 60.0
        self.fichas = float(self.capacidade)
        self.ultimo = time.monotonic()
        # Lock de thread: o mesmo limitador atende loops de evento diferentes.
        self._lock = threading.Lock()
        self._redis = None
        if settings.REDIS_URL:
            try:
                import redis.asyncio as aioredis
                self._redis = aioredis.from_url(settings.REDIS_URL)
            except Exception:  # sem Redis, cai no limitador local
                self._redis = None

    async def _tentar_redis(self):
        janela = int(time.time() // 60)
        chave = f"tutor:pln:{janela}"
        n = await self._redis.incr(chave)
        if n == 1:
            await self._redis.expire(chave, 120)
        return n <= self.capacidade

    async def _tentar_local(self):
        with self._lock:
            agora = time.monotonic()
            self.fichas = min(self.capacidade, self.fichas + (agora - self.ultimo) * self.taxa)
            self.ultimo = agora
            if self.fichas >= 1:
                self.fichas -= 1
                return True
            return False

    async def adquirir(self, espera_max_s):
        limite = time.monotonic() + max(0.0, espera_max_s)
        while True:
            ok = await (self._tentar_redis() if self._redis else self._tentar_local())
            if ok:
                return
            if time.monotonic() + 0.1 > limite:
                raise ErroPLN("cota", "limite de requisições atingido")
            await asyncio.sleep(0.1)


# ----------------------------------------------------------------- simulado

def _primeiras_palavras(texto, n):
    """Corta em n palavras sem perder as quebras de linha (o código do material continua legível)."""
    contadas, saida = 0, []
    for linha in texto.splitlines():
        palavras = linha.split()
        if contadas + len(palavras) > n:
            saida.append(" ".join(palavras[: n - contadas]) + " …")
            break
        saida.append(linha)
        contadas += len(palavras)
    texto = "\n".join(saida)
    if texto.count("```") % 2:  # não deixa um bloco de código aberto
        texto += "\n```"
    return texto


class PLNSimulado:
    """Imita o serviço externo sem rede. Classifica por termos e responde com os itens."""

    nome = "simulado"

    def __init__(self, config):
        self.modelo = "simulado-v1"
        # Sem chamada externa, sem cota: o limitador só existe no provedor real.

    async def interpretar(self, req: RequisicaoPLN, timeout_s):
        topicos = req.contexto.get("topicos_obj", [])
        topico, conf = classificar_local(req.contexto.get("mensagem", ""), topicos)
        if topico is None and req.contexto.get("anterior"):
            # Pergunta de acompanhamento ("e como paro ele?"): usa a pergunta anterior.
            topico, conf = classificar_local(req.contexto["anterior"] + " " + req.contexto["mensagem"], topicos)
        if topico is None:
            return Interpretacao("fora_escopo", None, 0.0)
        return Interpretacao("duvida", topico.ordem, conf)

    async def gerar(self, req: RequisicaoPLN, timeout_s, max_tokens):
        itens = req.contexto.get("itens", [])
        if req.modo == "orientar":
            dicas = req.contexto.get("exercicio", {}).get("dicas") or []
            n = req.contexto.get("orientacoes_anteriores", 0)
            if dicas:
                dica = dicas[min(n, len(dicas) - 1)]
                return Geracao(f"Vamos por partes. {dica} O que você acha que deve ser feito primeiro?")
            return Geracao("Qual é a entrada do problema e o que precisa sair? Comece por aí.")
        if not itens:
            return Geracao("Não tenho informação suficiente nos materiais da disciplina para responder.")
        item = itens[0]
        return Geracao(
            f"Segundo o material \"{item.titulo}\": {_primeiras_palavras(item.conteudo, 120)}"
        )


# ----------------------------------------------------------------- Anthropic

ESQUEMA_INTERPRETACAO = {
    "type": "object",
    "properties": {
        "intencao": {"type": "string", "enum": ["duvida", "conceito", "exercicio", "fora_escopo", "vaga"]},
        "topico": {"type": ["integer", "null"]},
        "confianca": {"type": "number"},
    },
    "required": ["intencao", "topico", "confianca"],
    "additionalProperties": False,
}


class PLNAnthropic:
    nome = "anthropic"

    def __init__(self, config):
        import anthropic

        self._anthropic = anthropic
        chave = os.environ.get(config.ref_credencial)
        if not chave:
            raise ErroPLN("indisponivel", f"variável {config.ref_credencial} não definida")
        self._chave = chave
        self._endpoint = config.endpoint or None
        self._clientes = {}
        self.modelo = config.modelo_gerar
        self.modelo_interpretar = config.modelo_interpretar
        self.limitador = Limitador(config.limite_requisicoes)

    def _cliente(self):
        # O cliente HTTP assíncrono fica preso ao loop de evento que o criou;
        # no Uvicorn há um loop só, no runserver há um por requisição.
        loop = asyncio.get_running_loop()
        cliente = self._clientes.get(id(loop))
        if cliente is None:
            if len(self._clientes) > 8:
                self._clientes.clear()
            cliente = self._anthropic.AsyncAnthropic(
                api_key=self._chave, base_url=self._endpoint, max_retries=0
            )
            self._clientes[id(loop)] = cliente
        return cliente

    async def _criar(self, timeout_s, **kwargs):
        a = self._anthropic
        try:
            resp = await self._cliente().with_options(timeout=max(0.2, timeout_s)).messages.create(**kwargs)
        except a.APITimeoutError as e:
            raise ErroPLN("timeout", str(e)) from e
        except a.RateLimitError as e:
            raise ErroPLN("cota", str(e)) from e
        except a.APIStatusError as e:
            raise ErroPLN("indisponivel", f"HTTP {e.status_code}") from e
        except a.APIConnectionError as e:
            raise ErroPLN("indisponivel", str(e)) from e
        if resp.stop_reason == "refusal":
            raise ErroPLN("recusa", "o provedor recusou a requisição")
        texto = "".join(b.text for b in resp.content if b.type == "text")
        return texto, resp.usage

    async def interpretar(self, req: RequisicaoPLN, timeout_s):
        inicio = time.monotonic()
        await self.limitador.adquirir(timeout_s * 0.3)
        texto, _ = await self._criar(
            timeout_s - (time.monotonic() - inicio),
            model=self.modelo_interpretar,
            max_tokens=200,
            system=req.sistema,
            messages=req.mensagens,
            # Classificação curta: pensamento desligado e esforço baixo, pela latência.
            thinking={"type": "disabled"},
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": ESQUEMA_INTERPRETACAO}},
        )
        try:
            dados = json.loads(texto)
        except json.JSONDecodeError as e:
            raise ErroPLN("indisponivel", "JSON inválido na interpretação") from e
        return Interpretacao(dados["intencao"], dados["topico"], float(dados["confianca"]))

    async def gerar(self, req: RequisicaoPLN, timeout_s, max_tokens):
        inicio = time.monotonic()
        await self.limitador.adquirir(timeout_s * 0.3)
        texto, uso = await self._criar(
            timeout_s - (time.monotonic() - inicio),
            model=self.modelo,
            max_tokens=max_tokens,
            system=req.sistema,
            messages=req.mensagens,
            thinking={"type": "disabled"},
            output_config={"effort": "low"},
        )
        return Geracao(texto.strip(), uso.input_tokens, uso.output_tokens)


# ----------------------------------------------------------------- Gemini

# Pool próprio para as chamadas ao provedor (RNF08): o padrão do Python tem cpu+4 threads
# (20 aqui), menos que as 30 perguntas simultâneas da carga de referência.
_POOL_PLN = concurrent.futures.ThreadPoolExecutor(max_workers=64, thread_name_prefix="pln")


class PLNGemini:
    """Google Gemini pelo SDK google-genai.

    Com projeto_gcp preenchido, usa o Vertex AI com a credencial do ambiente (ADC
    local ou conta de serviço na hospedagem): não existe chave para vazar. Sem
    projeto, usa uma API key lida da variável de ambiente em ref_credencial.
    """

    nome = "gemini"

    def __init__(self, config):
        from google import genai
        from google.genai import types

        self._genai, self._types = genai, types
        if config.projeto_gcp:
            self._args = {"vertexai": True, "project": config.projeto_gcp, "location": config.regiao_gcp or "global"}
        else:
            chave = os.environ.get(config.ref_credencial or "GEMINI_API_KEY")
            if not chave:
                raise ErroPLN("indisponivel", f"variável {config.ref_credencial or 'GEMINI_API_KEY'} não definida")
            self._args = {"api_key": chave}
        self.modelo = config.modelo_gerar
        self.modelo_interpretar = config.modelo_interpretar
        self.nivel = config.nivel_raciocinio or "minimal"
        self.temperatura = config.temperatura
        self.limitador = Limitador(config.limite_requisicoes)
        # Um cliente síncrono só, chamado numa thread: a conexão TLS e o token do Google
        # ficam aquecidos entre requisições, mesmo quando cada uma roda num loop novo.
        self._cliente = genai.Client(**self._args)
        # Aquece a conexão e o token sem gerar texto (consulta de metadados, sem custo):
        # sem isso, a 1ª pergunta depois de subir o servidor estoura o prazo.
        threading.Thread(target=self._aquecer, daemon=True).start()

    def _aquecer(self):
        try:
            self._cliente.models.get(model=self.modelo)
        except Exception:
            log.warning("aquecimento do Gemini falhou; a 1ª chamada pode ser lenta")

    @staticmethod
    def _conteudos(mensagens):
        return [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                for m in mensagens]

    async def _gerar(self, modelo, req, timeout_s, max_tokens, esquema=None):
        t = self._types
        cfg = t.GenerateContentConfig(
            system_instruction=req.sistema,
            max_output_tokens=max_tokens,
            temperature=self.temperatura,
            thinking_config=t.ThinkingConfig(thinking_level=self.nivel),
        )
        if esquema:
            cfg.response_mime_type = "application/json"
            cfg.response_json_schema = esquema
        try:
            # O prazo é controlado aqui (wait_for). Passar timeout ao SDK vira prazo no servidor
            # do Vertex, que corta com 504 antes da hora.
            resp = await asyncio.wait_for(
                asyncio.get_running_loop().run_in_executor(
                    _POOL_PLN, functools.partial(self._cliente.models.generate_content, model=modelo,
                                                 contents=self._conteudos(req.mensagens), config=cfg)),
                timeout=max(0.2, timeout_s),
            )
        except asyncio.TimeoutError as e:
            raise ErroPLN("timeout", "tempo limite do Gemini") from e
        except Exception as e:  # erros HTTP e de rede do SDK
            codigo = getattr(e, "code", None)
            raise ErroPLN("cota" if codigo == 429 else "indisponivel", f"{type(e).__name__} {codigo or ''}") from e
        if not resp.candidates or (resp.prompt_feedback and resp.prompt_feedback.block_reason):
            raise ErroPLN("recusa", "o provedor bloqueou a requisição")
        uso = resp.usage_metadata
        entrada = (uso.prompt_token_count or 0) if uso else 0
        saida = ((uso.candidates_token_count or 0) + (uso.thoughts_token_count or 0)) if uso else 0
        return (resp.text or "").strip(), entrada, saida

    async def interpretar(self, req: RequisicaoPLN, timeout_s):
        inicio = time.monotonic()
        await self.limitador.adquirir(timeout_s * 0.3)
        texto, _, _ = await self._gerar(self.modelo_interpretar, req, timeout_s - (time.monotonic() - inicio), 200,
                                        esquema=ESQUEMA_INTERPRETACAO)
        try:
            dados = json.loads(texto)
        except json.JSONDecodeError as e:
            raise ErroPLN("indisponivel", "JSON inválido na interpretação") from e
        return Interpretacao(dados["intencao"], dados["topico"], float(dados["confianca"]))

    async def gerar(self, req: RequisicaoPLN, timeout_s, max_tokens):
        inicio = time.monotonic()
        await self.limitador.adquirir(timeout_s * 0.3)
        texto, ent, sai = await self._gerar(self.modelo, req, timeout_s - (time.monotonic() - inicio), max_tokens)
        return Geracao(texto, ent, sai)


# Modelo padrão quando o campo do admin ainda tem o nome de outro provedor.
MODELO_PADRAO = {"anthropic": "claude-haiku-5-5", "gemini": "gemini-3.5-flash-lite"}


def _ajustar_modelos(config):
    padrao = MODELO_PADRAO.get(config.provedor)
    if not padrao:
        return
    prefixo = "claude" if config.provedor == "anthropic" else "gemini"
    for campo in ("modelo_interpretar", "modelo_gerar"):
        if not getattr(config, campo, "").startswith(prefixo):
            setattr(config, campo, padrao)


# ----------------------------------------------------------------- fábrica

_cache = {}


def obter_servico(config):
    """Uma instância por configuração, para o limitador valer entre requisições."""
    _ajustar_modelos(config)
    chave = (config.pk, config.provedor, config.modelo_gerar, config.modelo_interpretar,
             config.limite_requisicoes, config.endpoint, config.ref_credencial,
             config.projeto_gcp, config.regiao_gcp, config.nivel_raciocinio, config.temperatura)
    if chave not in _cache:
        _cache.clear()
        if config.provedor == "anthropic":
            _cache[chave] = PLNAnthropic(config)
        elif config.provedor == "gemini":
            _cache[chave] = PLNGemini(config)
        else:
            _cache[chave] = PLNSimulado(config)
    return _cache[chave]


def limpar_cache():
    _cache.clear()

