"""Fila de reprocessamento das interações cuja gravação falhou (RN05, Seção 4.2.1).

Com REDIS_URL, a fila é uma lista no Redis; sem ele, um arquivo JSONL local.
O worker (Celery) ou o comando `reprocessar_interacoes` regrava os itens, com
recuo exponencial entre tentativas, e alerta depois de 24 h pendente.
"""
import json
import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

log = logging.getLogger("tutor.fila")
CHAVE = "tutor:fila_reprocessamento"
ALERTA_APOS = timedelta(hours=24)


def _redis():
    if not settings.REDIS_URL:
        return None
    import redis
    return redis.from_url(settings.REDIS_URL)


def enfileirar(registro):
    registro.setdefault("tentativas", 0)
    registro.setdefault("enfileirada_em", timezone.now().isoformat())
    linha = json.dumps(registro, ensure_ascii=False)
    r = _redis()
    if r:
        r.rpush(CHAVE, linha)
    else:
        with open(settings.FILA_REPROCESSAMENTO_ARQUIVO, "a", encoding="utf-8") as f:
            f.write(linha + "\n")


PROCESSANDO = CHAVE + ":processando"


def _ler_todos():
    """Move a fila para uma área de processamento em vez de apagá-la.

    Se o worker cair no meio, os registros continuam lá e voltam na próxima rodada
    (a gravação é idempotente pela correlação).
    """
    r = _redis()
    if r:
        while r.rpoplpush(CHAVE, PROCESSANDO) is not None:
            pass
        return [json.loads(l) for l in r.lrange(PROCESSANDO, 0, -1)]
    arq = settings.FILA_REPROCESSAMENTO_ARQUIVO
    proc = arq.with_suffix(".processando")
    if arq.exists():
        with open(proc, "a", encoding="utf-8") as f:
            f.write(arq.read_text(encoding="utf-8"))
        arq.unlink()
    if not proc.exists():
        return []
    return [json.loads(l) for l in proc.read_text(encoding="utf-8").splitlines() if l.strip()]


def _concluir_leitura():
    r = _redis()
    if r:
        r.delete(PROCESSANDO)
    else:
        settings.FILA_REPROCESSAMENTO_ARQUIVO.with_suffix(".processando").unlink(missing_ok=True)


def reprocessar():
    """Tenta regravar tudo. Devolve (gravadas, pendentes).

    Com Redis, uma trava impede dois reprocessadores ao mesmo tempo: um apagaria a
    área de processamento com registros que o outro ainda não gravou.
    """
    r = _redis()
    if r and not r.set(CHAVE + ":trava", "1", nx=True, ex=600):
        return 0, -1  # outro reprocessador está rodando
    try:
        return _reprocessar()
    finally:
        if r:
            r.delete(CHAVE + ":trava")


def _reprocessar():
    from atendimento.models import Interacao

    gravadas, pendentes = 0, []
    agora = timezone.now()
    for reg in _ler_todos():
        espera = timedelta(seconds=min(3600, 30 * 2 ** reg["tentativas"]))  # recuo exponencial
        ultima = datetime.fromisoformat(reg.get("ultima_tentativa", reg["enfileirada_em"]))
        if reg["tentativas"] and agora - ultima < espera:
            pendentes.append(reg)
            continue
        dados = {k: v for k, v in reg.items() if k not in ("itens", "tentativas", "enfileirada_em", "ultima_tentativa")}
        try:
            if not dados.get("disciplina_id"):  # falhou antes de carregar a conversa
                from atendimento.models import Conversa
                dados["disciplina_id"] = Conversa.objects.get(pk=dados["conversa_id"]).disciplina_id
            if not Interacao.objects.filter(correlacao=dados.get("correlacao")).exists():
                inter = Interacao.objects.create(**dados)
                inter.itens_usados.set(reg["itens"])
            gravadas += 1
        except Exception:
            reg["tentativas"] += 1
            reg["ultima_tentativa"] = agora.isoformat()
            pendentes.append(reg)
            if agora - datetime.fromisoformat(reg["enfileirada_em"]) > ALERTA_APOS:
                log.error("ALERTA ADMIN: interação pendente há mais de 24 h correlacao=%s", reg.get("correlacao"))
    for reg in pendentes:
        enfileirar(reg)
    _concluir_leitura()  # só depois de cada registro ser gravado ou devolvido à fila
    return gravadas, len(pendentes)
