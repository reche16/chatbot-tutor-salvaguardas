"""Recuperação por tópico (RAG, Seção 4.3.3) e classificação local.

A recuperação usa o tópico identificado, não similaridade semântica. Dentro do
tópico, FAQ primeiro e depois coincidência de termos com a pergunta; no máximo
oito itens e cerca de 3.000 tokens. A ordenação por termos é feita em Python,
igual no SQLite e no PostgreSQL (a base de um tópico tem poucos itens).
"""
import re
import unicodedata

MAX_ITENS = 8
MAX_TOKENS = 3000

PARADAS = set(
    "a o e de da do das dos um uma uns umas que como para por com sem em no na nos nas se eu "
    "voce vc me meu minha isso esse essa este esta qual quais quando onde porque pq por que "
    "nao sim mais menos muito pouco ser ter fazer faz tem sao era foi vai ou ao aos the is "
    "pra pro to ta tá oi ola professor professora alguem ajuda ajudar duvida entender sei".split()
)


def termos(texto):
    texto = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    return [t for t in re.findall(r"[a-z_][a-z0-9_]+", texto) if t not in PARADAS and len(t) > 2]


def _radical(t):
    # Radical grosseiro para PT-BR: "condicionais" e "condicional" casam.
    for suf in ("coes", "cao", "mente", "ais", "eis", "res", "es", "s"):
        if t.endswith(suf) and len(t) - len(suf) >= 4:
            return t[: -len(suf)]
    return t


def _conjunto(texto):
    return {_radical(t) for t in termos(texto)}


def estimar_tokens(texto):
    return len(texto or "") // 4 + 1


def ordenar_itens(pergunta, itens):
    alvo = _conjunto(pergunta)

    def chave(item):
        coincid = len(alvo & _conjunto(item.titulo + " " + item.conteudo))
        return (0 if item.tipo == "FAQ" else 1, -coincid, item.id)

    # FAQ primeiro; dentro do tipo, mais termos em comum primeiro.
    escolhidos, total = [], 0
    for item in sorted(itens, key=chave):
        custo = estimar_tokens(item.titulo + item.conteudo)
        if len(escolhidos) >= MAX_ITENS or (escolhidos and total + custo > MAX_TOKENS):
            break
        escolhidos.append(item)
        total += custo
    return escolhidos


def classificar_local(pergunta, topicos):
    """Classificação por termos nos títulos e palavras-chave dos tópicos.

    É o classificador do modo simulado e o plano B da Seção 4.3.5 (eliminar a
    primeira chamada ao modelo). Devolve (topico ou None, confiança 0..1).
    """
    alvo = _conjunto(pergunta)
    if not alvo:
        return None, 0.0
    melhor, melhor_pontos = None, 0.0
    for t in topicos:
        chaves = [_conjunto(p) for p in t.lista_palavras_chave()] + [_conjunto(t.titulo)]
        pontos = 0.0
        for c in chaves:
            if c and c <= alvo:
                pontos += 1.0 + 0.5 * (len(c) - 1)  # expressão inteira presente
            elif c & alvo:
                pontos += 0.3 * len(c & alvo) / len(c)
        if pontos > melhor_pontos:
            melhor, melhor_pontos = t, pontos
    confianca = min(1.0, melhor_pontos / 1.5)
    return melhor, round(confianca, 2)


def semelhanca(a, b):
    """Jaccard entre os termos de dois textos (para achar enunciado colado no chat)."""
    x, y = _conjunto(a), _conjunto(b)
    if not x or not y:
        return 0.0
    return len(x & y) / len(x | y)
