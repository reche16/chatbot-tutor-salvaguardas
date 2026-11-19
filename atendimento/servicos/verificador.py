"""VerificadorSaida (RN06, Seção 4.3.4).

Antes da exibição, bloqueia a resposta gerada que contenha a resposta esperada de
um exercício avaliativo, código demais em lista avaliativa ou a confirmação/negação
da correção de uma resposta do aluno. É heurístico, de propósito: os erros dele são
medidos na avaliação (M3 vazamento e M4 recusas indevidas).
"""
import difflib
import re
import unicodedata
from dataclasses import dataclass

BLOCO_CODIGO = re.compile(r"```[\w+-]*\n?(.*?)```", re.S)

# Frases que confirmam ou negam a correção da tentativa do aluno.
CONFIRMACAO = re.compile(
    r"\b(est[aá]\s+(totalmente\s+|completamente\s+)?(corret[oa]|cert[oa]|errad[oa]|incorret[oa])"
    r"|(sua|a)\s+(resposta|solu[cç][aã]o|tentativa)\s+(est[aá]|[eé])\s+(corret[oa]|cert[oa]|errad[oa]|incorret[oa])"
    r"|isso\s+mesmo|exatamente\s+isso|acertou|voc[eê]\s+errou|resposta\s+corret[ao]\s+[eé]"
    r"|a\s+resposta\s+[eé]|o\s+resultado\s+[eé]|o\s+gabarito"
    r"|(sua|a|essa|esta)\s+(resposta|solu[cç][aã]o|tentativa|c[oó]digo|l[oó]gica)\s+(j[aá]\s+)?(n[aã]o\s+)?"
    r"(funciona|resolve|est[aá]\s+(bem|boa?|[oó]tim[ao]|perfeit[ao]|incomplet[ao]))"
    r"|(produz|gera|d[aá]|chega\s+a)\s+o\s+(valor|resultado|n[uú]mero)\s+(esperado|certo|corret[oa])"
    r"|caminho\s+(certo|errado)|certinh[oa]|mandou\s+bem)\b",
    re.I,
)


PROGRAMA = re.compile(r"\b(print|input)\s*\(|\breturn\b")


@dataclass
class ResultadoVerificacao:
    bloqueada: bool
    motivo: str = ""


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    texto = texto.lower()
    texto = re.sub(r"(\d),(\d)", r"\1.\2", texto)  # 3,5 -> 3.5
    texto = re.sub(r"[^\w.\s]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _normalizar_codigo(texto):
    linhas = [l.split("#", 1)[0].strip() for l in (texto or "").splitlines()]
    return re.sub(r"\s+", "", "".join(l for l in linhas if l)).lower()


def _parece_codigo(texto):
    return bool(re.search(r"(def |print\(|for |while |if |=|\breturn\b|input\()", texto or ""))


def _trechos_codigo(texto):
    blocos = BLOCO_CODIGO.findall(texto or "")
    if blocos:
        return blocos
    # Sem cercas: linhas indentadas ou com cara de código, em sequência.
    linhas = [l for l in (texto or "").splitlines() if _parece_codigo(l)]
    return ["\n".join(linhas)] if linhas else []


class VerificadorSaida:
    def __init__(self, limiar_similaridade=0.8, max_linhas_codigo=4):
        self.limiar = limiar_similaridade
        self.max_linhas = max_linhas_codigo

    def contem_resposta(self, resposta, esperada):
        if not esperada or not resposta:
            return False
        if _parece_codigo(esperada):
            alvo = _normalizar_codigo(esperada)
            if len(alvo) < 8:
                return alvo in _normalizar_codigo(resposta)
            for trecho in _trechos_codigo(resposta) + [resposta]:
                cod = _normalizar_codigo(trecho)
                if alvo in cod:
                    return True
                if difflib.SequenceMatcher(None, alvo, cod).ratio() >= self.limiar:
                    return True
            return False
        alvo = normalizar(esperada)
        texto = normalizar(resposta)
        if not alvo:
            return False
        if re.fullmatch(r"-?\d+(\.\d+)?", alvo):
            # Valor numérico: casa como número inteiro, não como parte de outro número.
            return re.search(rf"(?<![\d.]){re.escape(alvo)}(?![\d]|\.\d)", texto) is not None
        return alvo in texto

    def verificar(self, resposta, *, esperadas_avaliativas, em_exercicio_avaliativo):
        """esperadas_avaliativas: respostas esperadas que não podem aparecer.

        No UC03 é a do exercício em curso; no UC01/UC02, as das listas avaliativas
        abertas da disciplina, porque o aluno pode colar um enunciado no chat livre.
        """
        for esperada in esperadas_avaliativas:
            if self.contem_resposta(resposta, esperada):
                return ResultadoVerificacao(True, "contem_resposta_esperada")
        if em_exercicio_avaliativo:
            if CONFIRMACAO.search(resposta or ""):
                return ResultadoVerificacao(True, "confirma_ou_nega_correcao")
            for trecho in _trechos_codigo(resposta):
                linhas = [l for l in trecho.splitlines() if l.strip()]
                if len(linhas) > self.max_linhas:
                    return ResultadoVerificacao(True, "codigo_extenso")
                # Uma linha basta para resolver (ex.: print(sum(range(1, 101)))). Em lista
                # avaliativa, código que produz saída ou devolve valor é tratado como solução.
                if PROGRAMA.search(trecho):
                    return ResultadoVerificacao(True, "codigo_executavel")
        return ResultadoVerificacao(False)


def tentativa_confere(tentativa, esperada):
    """Lista de prática: compara a tentativa com o gabarito localmente (fluxo A1)."""
    if _parece_codigo(esperada):
        return _normalizar_codigo(tentativa) == _normalizar_codigo(esperada)
    return normalizar(tentativa) == normalizar(esperada)
