"""Teste de carga do RNF01/RNF08 pela interface HTTP (métrica M6 sob carga).

    python avaliacao/carga.py --usuarios 30 --ondas 3 [--base http://127.0.0.1:8765]

Cada usuário virtual faz login, abre uma conversa nova e, a cada onda, todos enviam
uma pergunta ao mesmo tempo (30 requisições simultâneas, a carga de referência da
especificação). Mede o tempo do envio à resposta no cliente, como o aluno percebe.
As contas carga01..N@teste.local são criadas e removidas pelo comando preparar/limpar
abaixo (o script não lê o banco). A senha vem da variável CARGA_SENHA.
"""
import argparse
import asyncio
import json
import math
import os
import re
import statistics
import sys
import time
from pathlib import Path

import httpx

AQUI = Path(__file__).parent


def perguntas_de_conceito():
    dados = json.loads((AQUI / "conjunto_teste.json").read_text(encoding="utf-8"))
    return [q["pergunta"] for q in dados if q["categoria"] == "i_conceito"]


async def preparar_usuario(base, email, senha):
    c = httpx.AsyncClient(base_url=base, timeout=60, follow_redirects=False)
    r = await c.get("/entrar/")
    csrf = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r.text).group(1)
    r = await c.post("/entrar/", data={"csrfmiddlewaretoken": csrf, "username": email, "password": senha},
                     headers={"Referer": base + "/entrar/"})
    if r.status_code != 302:
        raise RuntimeError(f"login falhou para {email}: {r.status_code}")
    r = await c.get("/chat/1/?nova=1", follow_redirects=True)
    conversa = re.search(r"/api/conversa/(\d+)/mensagem/", r.text).group(1)
    return c, conversa


async def enviar(c, conversa, pergunta, base):
    inicio = time.perf_counter()
    r = await c.post(f"/api/conversa/{conversa}/mensagem/", json={"mensagem": pergunta, "tipo": "DUVIDA"},
                     headers={"X-CSRFToken": c.cookies.get("csrftoken"), "Referer": base + "/"})
    total_ms = (time.perf_counter() - inicio) * 1000
    corpo = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    return {"status": r.status_code, "cliente_ms": round(total_ms), "servidor_ms": corpo.get("tempo_ms"),
            "respondida": corpo.get("respondida"), "motivo": corpo.get("motivo", "")}


def p(valores, q):
    v = sorted(valores)
    return v[max(0, math.ceil(q * len(v)) - 1)] if v else None


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8765")
    ap.add_argument("--usuarios", type=int, default=30)
    ap.add_argument("--ondas", type=int, default=3)
    a = ap.parse_args()
    senha = os.environ["CARGA_SENHA"]
    perguntas = perguntas_de_conceito()

    sessoes = await asyncio.gather(*(preparar_usuario(a.base, f"carga{n:02d}@teste.local", senha)
                                     for n in range(1, a.usuarios + 1)))
    # Aquecimento: uma pergunta antes das ondas (conexão com o provedor e cache de configuração).
    await enviar(*sessoes[0], "o que é uma variável?", a.base)

    resultados = []
    for onda in range(a.ondas):
        lote = [enviar(c, conv, perguntas[(onda * a.usuarios + i) % len(perguntas)], a.base)
                for i, (c, conv) in enumerate(sessoes)]
        t0 = time.perf_counter()
        r = await asyncio.gather(*lote)
        print(f"onda {onda + 1}: {len(r)} simultâneas em {time.perf_counter() - t0:.1f} s", file=sys.stderr)
        resultados += r
        await asyncio.sleep(5)
    for c, _ in sessoes:
        await c.aclose()

    ok = [x for x in resultados if x["status"] == 200]
    cli = [x["cliente_ms"] for x in ok]
    srv = [x["servidor_ms"] for x in ok if x["servidor_ms"] is not None]
    falhas = [x for x in ok if (x["motivo"] or "").startswith("pln_")]
    resumo = {
        "requisicoes": len(resultados), "simultaneas": a.usuarios, "ondas": a.ondas,
        "http_nao_200": len(resultados) - len(ok),
        "cliente_ms": {"p50": round(statistics.median(cli)), "p95": p(cli, .95), "max": max(cli)} if cli else None,
        "servidor_ms": {"p50": round(statistics.median(srv)), "p95": p(srv, .95), "max": max(srv)} if srv else None,
        "respondidas": sum(1 for x in ok if x["respondida"]),
        "falhas_do_provedor": len(falhas), "motivos": sorted({x["motivo"] for x in ok if x["motivo"]}),
        "dentro_de_5s": round(100 * sum(1 for v in cli if v <= 5000) / len(cli), 1) if cli else None,
    }
    saida = AQUI / "resultados" / f"carga-{time.strftime('%Y%m%d-%H%M%S')}.json"
    saida.parent.mkdir(exist_ok=True)
    saida.write_text(json.dumps({"resumo": resumo, "execucoes": resultados}, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    print(json.dumps(resumo, ensure_ascii=False, indent=1))
    print(f"-> {saida}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
