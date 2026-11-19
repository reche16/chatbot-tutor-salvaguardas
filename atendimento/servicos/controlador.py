"""ControladorAtendimento (Seções 4.2.1 e 4.2.2).

Orquestra UC01 (dúvida), UC02 (conceito) e UC03 (exercício): prazo de 5 s,
contexto das três últimas interações, filtro de dados pessoais, interpretação,
recuperação por tópico, geração, verificação de saída e registro da interação
antes da exibição — inclusive quando não há resposta (RN05).

A condição (B0, T1, T2) existe para a avaliação do Cap. 5; o sistema usa T2.
"""
import logging
import re
import time
import uuid
from dataclasses import dataclass, field

from asgiref.sync import sync_to_async
from django.db import DatabaseError, transaction
from django.utils import timezone

from academico.models import Exercicio, ItemConhecimento, TopicoEmenta
from atendimento.models import ConfiguracaoPLN, Conversa, Interacao, TipoAtendimento

from . import prompts
from .filtro import filtro_da_disciplina
from .fila import enfileirar
from .pln import ErroPLN, RequisicaoPLN, obter_servico
from .recuperacao import ordenar_itens, semelhanca
from .verificador import VerificadorSaida, _parece_codigo, normalizar, tentativa_confere

log = logging.getLogger("tutor.atendimento")

RESERVA_FINAL_S = 0.3  # verificação + gravação (Quadro 22)
SEMELHANCA_ENUNCIADO = 0.3
REFERENCIA_EXERCICIO = re.compile(r"\b(exerc[ií]cio|quest[aã]o)\s*(n[º°o.]?\s*)?\d+", re.I)


@dataclass
class Resultado:
    interacao_id: int | None
    resposta: str
    respondida: bool
    bloqueada: bool = False
    oferece_encaminhamento: bool = False
    topico: str | None = None
    tempo_ms: int = 0
    motivo: str = ""
    requisicoes: list = field(default_factory=list)  # para os testes e a avaliação


@dataclass
class _Dados:
    conversa: Conversa
    config: ConfiguracaoPLN
    topicos: list
    contexto: list
    filtro: object
    exercicio: Exercicio | None
    avaliativos_abertos: list
    orientacoes_seguidas: int


def _carregar(conversa_id, exercicio_id):
    conversa = Conversa.objects.select_related("disciplina", "aluno").get(pk=conversa_id)
    disciplina = conversa.disciplina
    exercicio = None
    if exercicio_id:
        exercicio = Exercicio.objects.select_related("lista", "topico").get(
            pk=exercicio_id, lista__disciplina=disciplina, lista__aberta=True
        )
    avaliativos = list(
        Exercicio.objects.filter(lista__disciplina=disciplina, lista__avaliativa=True, lista__aberta=True)
    )
    orientacoes = 0
    if exercicio:
        for i in conversa.interacoes.order_by("-data_hora")[:10]:
            if i.exercicio_id != exercicio.id or i.confirmada_localmente:
                break
            orientacoes += 1
    return _Dados(
        conversa=conversa,
        config=ConfiguracaoPLN.atual(),
        topicos=list(TopicoEmenta.objects.filter(disciplina=disciplina)),
        contexto=conversa.obter_contexto(3),
        filtro=filtro_da_disciplina(disciplina, conversa.aluno),
        exercicio=exercicio,
        avaliativos_abertos=avaliativos,
        orientacoes_seguidas=orientacoes,
    )


def _itens_do_topico(topico_id):
    return list(ItemConhecimento.objects.filter(topico_id=topico_id, ativo=True))


def _gravar(dados: _Dados, campos, itens):
    """Grava a interação; se o banco falhar, vai para a fila de reprocessamento (RN05)."""
    try:
        with transaction.atomic():
            inter = Interacao.objects.create(conversa=dados.conversa, disciplina=dados.conversa.disciplina, **campos)
            if itens:
                inter.itens_usados.set(itens)
        return inter.id
    except DatabaseError:
        log.exception("falha ao gravar interação; enfileirada correlacao=%s", campos.get("correlacao"))
        registro = {"conversa_id": dados.conversa.id, "disciplina_id": dados.conversa.disciplina_id,
                    "itens": [i.id for i in itens]}
        for k, v in campos.items():
            if hasattr(v, "pk"):
                registro[f"{k}_id"] = v.pk
            elif v is None or isinstance(v, (str, int, float, bool, dict, list)):
                registro[k] = v
            else:
                registro[k] = v.isoformat() if hasattr(v, "isoformat") else str(v)
        enfileirar(registro)
        return None


class ControladorAtendimento:
    def __init__(self, condicao="T2", servico=None):
        assert condicao in ("B0", "T1", "T2")
        self.condicao = condicao
        self._servico = servico

    async def atender(self, conversa_id, mensagem, tipo=TipoAtendimento.DUVIDA, exercicio_id=None):
        inicio = time.monotonic()
        tempos = {}
        try:
            dados = await sync_to_async(_carregar)(conversa_id, exercicio_id)
        except DatabaseError:
            # Banco fora do ar antes de tudo: a pergunta vai para a fila mesmo assim (RN05).
            log.exception("falha ao carregar o atendimento; pergunta enfileirada")
            await sync_to_async(enfileirar)({
                "conversa_id": conversa_id, "exercicio_id": exercicio_id, "pergunta": mensagem, "tipo": tipo,
                "respondida": False, "motivo_sem_resposta": "falha_banco", "data_hora": timezone.now().isoformat(),
                "correlacao": str(uuid.uuid4()), "itens": [],
            })
            return Resultado(None, prompts.AVISO_INDISPONIVEL, False, motivo="falha_banco")
        cfg = dados.config
        prazo = cfg.prazo_total_ms / 1000
        try:
            servico = self._servico or obter_servico(cfg)
        except ErroPLN as e:
            log.error("serviço de PLN não configurado: %s", e)
            servico = _SemServico(e)
        disciplina = dados.conversa.disciplina
        exercicio = dados.exercicio
        avaliativa = bool(exercicio and exercicio.lista.avaliativa)
        if exercicio:
            tipo = TipoAtendimento.EXERCICIO

        filtro = dados.filtro
        msg = filtro.aplicar(mensagem)
        historico = []
        for i in dados.contexto:
            historico.append({"role": "user", "content": filtro.aplicar(i.pergunta)})
            historico.append({"role": "assistant", "content": filtro.aplicar(i.resposta or "(sem resposta)")})
        tempos["preparo"] = _ms(inicio)

        def restante():
            return prazo - (time.monotonic() - inicio)

        campos = {
            "tipo": tipo, "exercicio": exercicio, "pergunta": mensagem, "data_hora": timezone.now(),
            "versao_prompt": f"{prompts.VERSAO_PROMPT}-{self.condicao}", "modelo_pln": servico.modelo,
            "correlacao": uuid.uuid4(),
        }
        requisicoes = []

        async def concluir(resposta, respondida, *, itens=(), topico=None, confianca=None, bloqueada=False,
                           motivo="", motivo_sem_resposta="", confirmada=False, oferece=False):
            campos.update(
                resposta=resposta, respondida=respondida, topico=topico, confianca=confianca,
                bloqueada_verificacao=bloqueada, motivo_bloqueio=motivo, motivo_sem_resposta=motivo_sem_resposta,
                confirmada_localmente=confirmada, oferece_encaminhamento=oferece,
            )
            campos["tempo_resposta_ms"] = _ms(inicio)
            tempos["total"] = campos["tempo_resposta_ms"]
            campos["tempos_etapas"] = tempos
            iid = await sync_to_async(_gravar)(dados, campos, list(itens))
            log.info("atendimento cond=%s tipo=%s respondida=%s bloqueada=%s motivo=%s tempos=%s",
                     self.condicao, tipo, respondida, bloqueada, motivo or motivo_sem_resposta, tempos)
            return Resultado(iid, resposta, respondida, bloqueada, oferece, topico.titulo if topico else None,
                             campos["tempo_resposta_ms"], motivo or motivo_sem_resposta, requisicoes)

        # Fluxo A1 do UC03: lista de prática, tentativa igual ao gabarito, sem serviço externo.
        if exercicio and not avaliativa and tentativa_confere(mensagem, exercicio.resposta_esperada):
            return await concluir(prompts.CONFIRMACAO_PRATICA, True, topico=exercicio.topico, confirmada=True)
        # Lista avaliativa com a solução na própria mensagem: não confirma nem nega (RN02) e não
        # chama o modelo, que tenderia a repetir o código e ser bloqueado com uma dica sem relação.
        if avaliativa and VerificadorSaida().contem_resposta(mensagem, exercicio.resposta_esperada):
            return await concluir(prompts.TENTATIVA_AVALIATIVA, True, topico=exercicio.topico)

        # Pedido sobre "o exercício 3" sem escolher o exercício: as listas têm números repetidos,
        # então o tutor pede para escolher no menu em vez de adivinhar (sem chamar o serviço).
        if self.condicao == "T2" and not exercicio and REFERENCIA_EXERCICIO.search(mensagem):
            return await concluir(prompts.ESCOLHA_O_EXERCICIO, False, motivo_sem_resposta="exercicio_sem_selecao")

        # ---- interpretação (UC17)
        topico, confianca = None, None
        if self.condicao != "B0":
            if exercicio and exercicio.topico:
                topico, confianca = exercicio.topico, 1.0
            else:
                req = RequisicaoPLN(
                    "interpretar",
                    prompts.INTERPRETAR.format(
                        disciplina=disciplina.nome,
                        topicos="\n".join(
                            f"{t.ordem}: {t.titulo}" + (f" (assuntos: {t.palavras_chave})" if t.palavras_chave else "")
                            for t in dados.topicos
                        ),
                    ),
                    historico[-2:] + [{"role": "user", "content": msg}] if historico else
                    [{"role": "user", "content": msg}],
                    {"mensagem": msg, "topicos_obj": dados.topicos,
                     "anterior": historico[-2]["content"] if historico else ""},
                )
                requisicoes.append(req)
                t = time.monotonic()
                try:
                    interp = await servico.interpretar(req, min(cfg.timeout_interpretar_ms / 1000, restante()))
                except ErroPLN as e:
                    tempos["interpretar"] = _ms(t)
                    return await concluir(prompts.AVISO_INDISPONIVEL, False, motivo_sem_resposta=f"pln_{e.motivo}",
                                          oferece=True)
                tempos["interpretar"] = _ms(t)
                topico = next((x for x in dados.topicos if x.ordem == interp.topico_ordem), None)
                confianca = interp.confianca
                lista_topicos = prompts.formatar_topicos(dados.topicos)
                if interp.intencao == "vaga":
                    return await concluir(prompts.PERGUNTA_VAGA.format(topicos=lista_topicos), False,
                                          confianca=confianca, motivo_sem_resposta="pergunta_vaga")
                if topico is None or interp.intencao == "fora_escopo" or confianca < cfg.limiar_confianca:
                    return await concluir(prompts.RECUSA_FORA_ESCOPO.format(topicos=lista_topicos), False,
                                          topico=None, confianca=confianca,
                                          motivo_sem_resposta="fora_da_ementa", oferece=True)

        # ---- recuperação por tópico (Seção 4.3.3)
        t = time.monotonic()
        itens = []
        if topico is not None:
            try:
                itens = ordenar_itens(msg, await sync_to_async(_itens_do_topico)(topico.id))
            except DatabaseError:
                # O banco caiu no meio: o registro abaixo também falha e vai para a fila (RN05).
                log.exception("falha ao buscar itens do tópico")
                return await concluir(prompts.AVISO_INDISPONIVEL, False, topico=topico, confianca=confianca,
                                      motivo_sem_resposta="falha_banco", oferece=True)
            if not itens and not exercicio:
                tempos["buscar"] = _ms(t)
                return await concluir(prompts.RECUSA_SEM_CONTEUDO, False, topico=topico, confianca=confianca,
                                      motivo_sem_resposta="sem_conteudo", oferece=True)
        tempos["buscar"] = _ms(t)

        # ---- geração
        modo, sistema, contexto_req = self._montar(disciplina, topico, itens, exercicio, dados)
        req = RequisicaoPLN(modo, sistema, historico + [{"role": "user", "content": msg}], contexto_req)
        requisicoes.append(req)
        t = time.monotonic()
        try:
            ger = await servico.gerar(
                req, min(cfg.timeout_gerar_ms / 1000, restante() - RESERVA_FINAL_S), cfg.max_tokens_resposta
            )
        except ErroPLN as e:
            tempos["gerar"] = _ms(t)
            return await concluir(prompts.AVISO_INDISPONIVEL, False, topico=topico, confianca=confianca,
                                  itens=itens, motivo_sem_resposta=f"pln_{e.motivo}", oferece=True)
        tempos["gerar"] = _ms(t)
        tempos["tokens"] = [ger.tokens_entrada, ger.tokens_saida]
        resposta = ger.texto

        # ---- verificação de saída (RN06), só no tutor completo
        bloqueada, motivo = False, ""
        if self.condicao == "T2":
            t = time.monotonic()
            esperadas, em_avaliativo = self._alvos_verificacao(mensagem, exercicio, avaliativa, dados)
            verif = VerificadorSaida(cfg.limiar_similaridade_codigo, cfg.max_linhas_codigo_avaliativa).verificar(
                resposta, esperadas_avaliativas=esperadas, em_exercicio_avaliativo=em_avaliativo
            )
            tempos["verificar"] = _ms(t)
            if verif.bloqueada:
                bloqueada, motivo = True, verif.motivo
                # Alterna as dicas do professor em vez de repetir a última; depois, a genérica.
                dicas = (exercicio.lista_dicas() if exercicio else []) + [prompts.DICA_GENERICA]
                resposta = prompts.BLOQUEIO_PREFIXO + dicas[dados.orientacoes_seguidas % len(dicas)]

        resposta = prompts.limpar_marcadores(resposta)
        # A oferta aparece uma vez, na 3ª orientação seguida do mesmo exercício. O sistema não
        # sabe se o aluno avançou (não executa o código), então o texto não afirma que travou.
        oferece = bool(exercicio) and dados.orientacoes_seguidas + 1 == 3
        if oferece:
            resposta += prompts.OFERTA_ENCAMINHAR
        return await concluir(resposta, True, itens=itens, topico=topico, confianca=confianca,
                              bloqueada=bloqueada, motivo=motivo, oferece=oferece)

    def _montar(self, disciplina, topico, itens, exercicio, dados):
        titulo_topico = topico.titulo if topico else "-"
        ctx = {"itens": itens, "orientacoes_anteriores": dados.orientacoes_seguidas}
        if self.condicao == "B0":
            sistema = prompts.LINHA_DE_BASE.format(disciplina=disciplina.nome)
            if exercicio:
                ctx["exercicio"] = {"enunciado": exercicio.enunciado, "dicas": []}
                sistema += "\n\nExercício: " + exercicio.enunciado
            return ("base", sistema, ctx)
        if exercicio:
            if self.condicao == "T1":
                # T1 = versão anterior da especificação: gabarito e passos vão ao modelo.
                ex = {"enunciado": exercicio.enunciado, "dicas": exercicio.lista_dicas(),
                      "passos": exercicio.passos, "resposta_esperada": exercicio.resposta_esperada}
            else:
                ex = exercicio.dados_para_pln()
            ctx["exercicio"] = ex
            sistema = prompts.ORIENTAR.format(
                disciplina=disciplina.nome, exercicio=prompts.formatar_exercicio(ex),
                regra_codigo=prompts.REGRA_CODIGO_AVALIATIVA if exercicio.lista.avaliativa else prompts.REGRA_CODIGO_PRATICA,
                topico=titulo_topico, itens=prompts.formatar_itens(itens),
            )
            return ("orientar", sistema + "\n\n" + prompts.AVISO_MARCADORES + "\n" + prompts.ESTILO, ctx)
        sistema = prompts.RESPONDER.format(
            disciplina=disciplina.nome, topico=titulo_topico, itens=prompts.formatar_itens(itens)
        )
        return ("responder", sistema + "\n\n" + prompts.AVISO_MARCADORES + "\n" + prompts.ESTILO, ctx)

    @staticmethod
    def _alvos_verificacao(mensagem, exercicio, avaliativa, dados):
        """Que gabaritos não podem aparecer na resposta (Seção 4.3.4)."""
        # O gabarito do exercício em curso, se avaliativo, e os de todos os avaliativos
        # abertos: o aluno pode colar outro enunciado no chat livre ou num exercício de prática.
        esperadas, parece_exercicio = ([exercicio.resposta_esperada] if avaliativa else []), avaliativa
        for ex in dados.avaliativos_abertos:
            if exercicio and ex.id == exercicio.id:
                continue
            if semelhanca(mensagem, ex.enunciado) >= SEMELHANCA_ENUNCIADO:
                esperadas.append(ex.resposta_esperada)
                parece_exercicio = True
            elif _parece_codigo(ex.resposta_esperada) or len(normalizar(ex.resposta_esperada)) >= 12:
                # Gabarito longo/código é distintivo o bastante para checar sempre.
                esperadas.append(ex.resposta_esperada)
        return esperadas, parece_exercicio


class _SemServico:
    """Provedor indisponível (ex.: chave ausente): toda chamada falha e vira aviso registrado."""

    modelo = "indisponivel"

    def __init__(self, erro):
        self.erro = erro

    async def interpretar(self, req, timeout_s):
        raise self.erro

    async def gerar(self, req, timeout_s, max_tokens):
        raise self.erro


def _ms(inicio):
    return int((time.monotonic() - inicio) * 1000)
