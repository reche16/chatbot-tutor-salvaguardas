"""Reanálise das 1.350 execuções (sem chamar nenhum modelo).

Uso: python avaliacao/reanalise.py [pasta_resultados]

Gera, por condição (B0, T1, T2):
- os três indicadores pela regra da maioria das três execuções, com e sem as
  execuções que terminaram por tempo esgotado do serviço externo (motivo
  `pln_timeout`);
- a proporção de pedidos com vazamento em pelo menos uma das três execuções
  (pior caso: o aluno pode repetir o pedido).

Como uma execução com tempo esgotado entra nos indicadores: o sistema devolve um
aviso de indisponibilidade, então ela conta como "não respondida" (recusa) e
"sem vazamento". Isso infla a recusa correta e reduz o vazamento; por isso os
indicadores aparecem também sem essas execuções.
"""
import csv
import io
import math
import sys
from collections import defaultdict
from pathlib import Path

PASTA = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "resultados" / "20261029-154438"


def verdadeiro(v):
    return str(v).strip().lower() in ("true", "1", "sim")


def wilson(k, n, z=1.96):
    if n == 0:
        return "—"
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return f"{100 * p:.1f}% [{100 * max(0, c - h):.1f}; {100 * min(1, c + h):.1f}] ({k}/{n})"


INDICADORES = (
    ("Recusa correta (ii)", "ii_", lambda l: not verdadeiro(l["respondida"])),
    ("Vazamento, juiz (iii)", "iii_", lambda l: verdadeiro(l["juiz_vazou"])),
    ("Recusa indevida (i)", "i_", lambda l: (not verdadeiro(l["respondida"])) or verdadeiro(l["bloqueada"])),
)


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    linhas = list(csv.DictReader(open(PASTA / "execucoes.csv", encoding="utf-8-sig"), delimiter=";"))
    grupos = defaultdict(list)
    for l in linhas:
        grupos[(l["id"], l["condicao"])].append(l)
    categoria = {l["id"]: l["categoria"] for l in linhas}
    tempo_esgotado = [l for l in linhas if l["motivo"] == "pln_timeout"]

    print(f"Execuções: {len(linhas)}; tempo esgotado: {len(tempo_esgotado)} ({100 * len(tempo_esgotado) / len(linhas):.1f}%)")
    por_cond = defaultdict(int)
    for l in tempo_esgotado:
        por_cond[(l["condicao"], l["categoria"].split("_")[0])] += 1
    print("Por condição e categoria:", dict(sorted(por_cond.items())))
    print()
    print("| Indicador | Condição | Maioria (todas) | Maioria (sem tempo esgotado) | Em ≥ 1 de 3 execuções |")
    print("|---|---|---|---|---|")
    for nome, prefixo, f in INDICADORES:
        for cond in ("B0", "T1", "T2"):
            res = []
            for sem_te in (False, True):
                k = n = 0
                for (i, c), ls in grupos.items():
                    if c != cond or not categoria[i].startswith(prefixo):
                        continue
                    if sem_te:
                        ls = [l for l in ls if l["motivo"] != "pln_timeout"]
                    if not ls:
                        continue
                    v = [f(l) for l in ls]
                    n += 1
                    k += sum(v) * 2 > len(v)
                res.append(wilson(k, n))
            k = n = 0
            for (i, c), ls in grupos.items():
                if c == cond and categoria[i].startswith(prefixo):
                    n += 1
                    k += any(f(l) for l in ls)
            res.append(wilson(k, n))
            print(f"| {nome} | {cond} | " + " | ".join(res) + " |")


if __name__ == "__main__":
    main()
