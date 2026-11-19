"""Métricas pedagógicas (RF22): consultas agregadas sobre Interacao, sem classe própria.

Tópicos com perguntas de menos de cinco alunos distintos no período são agrupados,
para o professor não inferir quem perguntou (Seção 4.3.6).
"""
from django.db.models import Count, Q
from django.db.models.functions import TruncWeek

from atendimento.models import Interacao

MIN_ALUNOS = 5


def calcular(disciplina, inicio=None, fim=None):
    qs = Interacao.objects.filter(disciplina=disciplina, anonimizada=False)
    if inicio:
        qs = qs.filter(data_hora__gte=inicio)
    if fim:
        qs = qs.filter(data_hora__lt=fim)

    total = qs.count()
    respondidas = qs.filter(respondida=True).count()
    encaminhadas = qs.filter(encaminhamento__isnull=False).count()
    resolvidas_sem_enc = qs.filter(respondida=True, encaminhamento__isnull=True).count()

    por_topico, agrupado = [], {"total": 0, "nao_respondidas": 0, "topicos": 0}
    linhas = (qs.values("topico__ordem", "topico__titulo")
              .annotate(total=Count("id"), alunos=Count("conversa__aluno", distinct=True),
                        nao_respondidas=Count("id", filter=Q(respondida=False)))
              .order_by("-total"))
    for l in linhas:
        titulo = l["topico__titulo"] or "Sem tópico (fora da ementa ou incerta)"
        if l["alunos"] < MIN_ALUNOS:
            agrupado["total"] += l["total"]
            agrupado["nao_respondidas"] += l["nao_respondidas"]
            agrupado["topicos"] += 1
        else:
            por_topico.append({"titulo": titulo, "total": l["total"], "nao_respondidas": l["nao_respondidas"]})
    if agrupado["total"]:
        por_topico.append({
            "titulo": f"Outros ({agrupado['topicos']} tópicos com menos de {MIN_ALUNOS} alunos)",
            "total": agrupado["total"], "nao_respondidas": agrupado["nao_respondidas"],
        })

    semanas = [
        {"semana": s["semana"].date() if s["semana"] else None, "total": s["total"], "respondidas": s["resp"]}
        for s in qs.annotate(semana=TruncWeek("data_hora")).values("semana")
        .annotate(total=Count("id"), resp=Count("id", filter=Q(respondida=True))).order_by("semana")
    ]
    tempos = sorted(qs.exclude(tempo_resposta_ms=None).values_list("tempo_resposta_ms", flat=True))

    def pct(a, b):
        return round(100 * a / b, 1) if b else None

    return {
        "total": total,
        "respondidas": respondidas,
        "nao_respondidas": total - respondidas,
        "bloqueadas": qs.filter(bloqueada_verificacao=True).count(),
        "encaminhadas": encaminhadas,
        "taxa_resolucao_sem_encaminhamento": pct(resolvidas_sem_enc, total),
        "avaliadas_uteis": qs.filter(avaliacao__util=True).count(),
        "avaliadas_nao_uteis": qs.filter(avaliacao__util=False).count(),
        "p95_ms": tempos[max(0, int(len(tempos) * 0.95) - 1)] if tempos else None,
        "por_topico": por_topico,
        "por_semana": semanas,
    }
