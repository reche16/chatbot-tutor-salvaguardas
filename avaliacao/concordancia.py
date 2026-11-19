"""Concordância da avaliação humana (M5 e validação do juiz).

Uso:
  python avaliacao/concordancia.py <pasta_resultados> <rubrica_m5_avaliador1.csv> <rubrica_m5_avaliador2.csv> \
      <validacao_juiz_avaliador1.csv> <validacao_juiz_avaliador2.csv>

Os CSVs são os baixados do FORMULARIO_AVALIACAO.html. A chave (veredito do juiz por amostra) está em
<pasta_resultados>/chave_validacao.csv.

Saída:
- M5: média por critério e geral (dois avaliadores juntos), kappa ponderado de Cohen (pesos lineares) por
  critério e com todos os critérios empilhados;
- validação do juiz, por métrica: concordância percentual e kappa de Cohen entre juiz e cada avaliador e
  entre os dois avaliadores; vereditos alterados = amostras em que os dois humanos discordam do juiz.
"""
import csv
import io
import sys
from collections import Counter
from pathlib import Path

CRITERIOS = ["correcao", "clareza", "adequacao_nivel", "estimulo_raciocinio"]


def ler(caminho):
    return list(csv.DictReader(open(caminho, encoding="utf-8-sig"), delimiter=";"))


def kappa(a, b, categorias, ponderado=False):
    n = len(a)
    if n == 0:
        return float("nan")
    k = len(categorias)
    idx = {c: i for i, c in enumerate(categorias)}
    peso = (lambda i, j: abs(i - j) / (k - 1)) if ponderado else (lambda i, j: 0.0 if i == j else 1.0)
    obs = Counter((idx[x], idx[y]) for x, y in zip(a, b))
    ma, mb = Counter(idx[x] for x in a), Counter(idx[y] for y in b)
    do = sum(peso(i, j) * c for (i, j), c in obs.items()) / n
    de = sum(peso(i, j) * ma[i] * mb[j] for i in range(k) for j in range(k)) / (n * n)
    return 1.0 if de == 0 else 1 - do / de


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    pasta, m1, m2, v1, v2 = sys.argv[1:6]
    r1 = {r["amostra"]: r for r in ler(m1)}
    r2 = {r["amostra"]: r for r in ler(m2)}
    comuns = sorted(set(r1) & set(r2), key=int)
    print(f"## M5 (rubrica, {len(comuns)} respostas com os dois avaliadores)\n")
    print("| Critério | Média av. 1 | Média av. 2 | Média geral | κ ponderado |")
    print("|---|---|---|---|---|")
    todos_a, todos_b = [], []
    for c in CRITERIOS:
        a = [int(r1[x][f"{c}_prof1"]) for x in comuns if r1[x][f"{c}_prof1"] and r2[x][f"{c}_prof2"]]
        b = [int(r2[x][f"{c}_prof2"]) for x in comuns if r1[x][f"{c}_prof1"] and r2[x][f"{c}_prof2"]]
        todos_a += a
        todos_b += b
        print(f"| {c} | {sum(a)/len(a):.2f} | {sum(b)/len(b):.2f} | {(sum(a)+sum(b))/(len(a)+len(b)):.2f} | "
              f"{kappa(a, b, [1, 2, 3, 4], True):.2f} |")
    print(f"| **todos** | {sum(todos_a)/len(todos_a):.2f} | {sum(todos_b)/len(todos_b):.2f} | "
          f"{(sum(todos_a)+sum(todos_b))/(len(todos_a)+len(todos_b)):.2f} | "
          f"{kappa(todos_a, todos_b, [1, 2, 3, 4], True):.2f} |\n")

    chave = {r["amostra"]: r for r in ler(Path(pasta) / "chave_validacao.csv")}
    h1 = {r["amostra"]: r for r in ler(v1)}
    h2 = {r["amostra"]: r for r in ler(v2)}
    col1 = next(k for k in next(iter(h1.values())) if k.startswith("avaliador"))
    col2 = next(k for k in next(iter(h2.values())) if k.startswith("avaliador"))
    print("## Validação do juiz\n")
    print("| Métrica | n | Juiz × av. 1 | Juiz × av. 2 | Av. 1 × av. 2 | Vereditos alterados (os dois humanos discordam do juiz) |")
    print("|---|---|---|---|---|---|")
    for metrica in sorted({r["metrica"] for r in h1.values()}):
        ids = [a for a, r in h1.items() if r["metrica"] == metrica and r[col1] and h2.get(a, {}).get(col2)]
        j = ["sim" if chave[a]["veredito_juiz"] == "True" else "nao" for a in ids]
        a = [h1[x][col1] for x in ids]
        b = [h2[x][col2] for x in ids]

        def par(x, y):
            return f"{100 * sum(p == q for p, q in zip(x, y)) / len(x):.0f}%, κ = {kappa(x, y, ['sim', 'nao']):.2f}"
        alterados = sum(1 for p, q, r in zip(j, a, b) if q == r != p)
        print(f"| {metrica} | {len(ids)} | {par(j, a)} | {par(j, b)} | {par(a, b)} | {alterados} |")


if __name__ == "__main__":
    main()
