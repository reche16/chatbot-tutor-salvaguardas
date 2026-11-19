"""Tempo de cada etapa do atendimento (ponto 5 do orientador), a partir do log técnico.

    python avaliacao/tempos_etapas.py --de "2026-10-29 15:43" --ate "2026-10-29 16:30"

O log (logs/tecnico.log*) traz, por atendimento, a condição e os tempos de cada etapa em ms,
sem o texto das perguntas. Saída: p50 e p95 de interpretar, buscar, gerar, verificar e total por condição.
"""
import argparse
import ast
import math
import re
import statistics
from collections import defaultdict
from pathlib import Path

LINHA = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d),\d+ INFO tutor\.atendimento atendimento cond=(\w+) "
                   r"tipo=(\w+) respondida=(\w+) bloqueada=(\w+) motivo=(\S*) tempos=(\{.*\})\s*$")


def percentil(v, q):
    v = sorted(v)
    return v[max(0, math.ceil(q * len(v)) - 1)] if v else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--de", required=True)
    ap.add_argument("--ate", required=True)
    a = ap.parse_args()
    logs = sorted((Path(__file__).resolve().parent.parent / "logs").glob("tecnico.log*"))
    etapas = defaultdict(lambda: defaultdict(list))
    for arq in logs:
        for linha in arq.read_text(encoding="utf-8", errors="replace").splitlines():
            m = LINHA.match(linha)
            if not m or not (a.de <= m.group(1) <= a.ate):
                continue
            cond, tempos = m.group(2), ast.literal_eval(m.group(7))
            for k in ("interpretar", "buscar", "gerar", "verificar", "total"):
                if isinstance(tempos.get(k), int):
                    etapas[cond][k].append(tempos[k])
    for cond in sorted(etapas):
        print(f"== {cond}")
        for k, v in etapas[cond].items():
            print(f"  {k:11} n={len(v):4}  p50={statistics.median(v):6.0f} ms  p95={percentil(v, .95):5} ms  "
                  f"max={max(v):5} ms")


if __name__ == "__main__":
    main()
