"""Painel pedagógico do professor (RF20–RF23), limitado às disciplinas que leciona (RN04)."""
import csv
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from academico.models import Disciplina
from atendimento.models import Avaliacao, DuvidaEncaminhada, RespostaProfessor, StatusDuvida
from atendimento.servicos.filtro import filtro_da_disciplina

from . import metricas


def _disciplinas(user):
    if not user.is_authenticated or not user.eh_professor:
        raise PermissionDenied("Área do professor.")
    return Disciplina.objects.filter(turmas__professores=user).distinct()


def _periodo(request):
    tz = timezone.get_current_timezone()
    try:
        inicio = datetime.fromisoformat(request.GET["inicio"]).replace(tzinfo=tz) if request.GET.get("inicio") else None
        fim = (datetime.fromisoformat(request.GET["fim"]).replace(tzinfo=tz) + timedelta(days=1)
               if request.GET.get("fim") else None)
    except ValueError:
        inicio = fim = None
    return inicio, fim


@login_required
def painel(request):
    disciplinas = _disciplinas(request.user)
    escolhida = disciplinas.filter(pk=request.GET.get("disciplina")).first() if request.GET.get("disciplina") else None
    escolhida = escolhida or disciplinas.first()
    inicio, fim = _periodo(request)
    dados = metricas.calcular(escolhida, inicio, fim) if escolhida else None
    abertas = DuvidaEncaminhada.objects.filter(disciplina__in=disciplinas, status=StatusDuvida.ABERTA).count()
    revisar = Avaliacao.objects.filter(interacao__disciplina__in=disciplinas, util=False, revisada=False).count()
    return render(request, "pedagogico/painel.html", {
        "disciplinas": disciplinas, "disciplina": escolhida, "m": dados,
        "abertas": abertas, "revisar": revisar, "sus": resumo_sus(),
        "filtro": {"inicio": request.GET.get("inicio", ""), "fim": request.GET.get("fim", "")},
    })


@login_required
def exportar_csv(request):
    """RF23 (desejável): as mesmas métricas do painel, em CSV."""
    disciplina = get_object_or_404(_disciplinas(request.user), pk=request.GET.get("disciplina"))
    inicio, fim = _periodo(request)
    m = metricas.calcular(disciplina, inicio, fim)
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="metricas_{disciplina.codigo}.csv"'
    resp.write("﻿")
    w = csv.writer(resp, delimiter=";")
    w.writerow(["indicador", "valor"])
    for chave in ("total", "respondidas", "nao_respondidas", "bloqueadas", "encaminhadas",
                  "taxa_resolucao_sem_encaminhamento", "avaliadas_uteis", "avaliadas_nao_uteis", "p95_ms"):
        w.writerow([chave, m[chave]])
    w.writerow([])
    w.writerow(["topico", "interacoes", "nao_respondidas"])
    for t in m["por_topico"]:
        w.writerow([t["titulo"], t["total"], t["nao_respondidas"]])
    w.writerow([])
    w.writerow(["semana", "interacoes", "respondidas"])
    for s in m["por_semana"]:
        w.writerow([s["semana"], s["total"], s["respondidas"]])
    return resp


@login_required
def duvidas(request):
    """RF20: dúvidas encaminhadas, com identificação do aluno e o histórico (RN04 i)."""
    disciplinas = _disciplinas(request.user)
    qs = (DuvidaEncaminhada.objects.filter(disciplina__in=disciplinas)
          .select_related("aluno", "interacao__conversa", "resposta", "disciplina"))
    status = request.GET.get("status", StatusDuvida.ABERTA)
    if status in StatusDuvida.values:
        qs = qs.filter(status=status)
    itens = []
    for d in qs[:100]:
        conversa = d.interacao.conversa
        hist = list(conversa.interacoes.filter(data_hora__lte=d.interacao.data_hora).order_by("data_hora")) if conversa else [d.interacao]
        itens.append({"duvida": d, "historico": hist[-6:]})
    return render(request, "pedagogico/duvidas.html", {"itens": itens, "status": status})


@login_required
@require_POST
def responder_duvida(request, duvida_id):
    duvida = get_object_or_404(DuvidaEncaminhada, pk=duvida_id, disciplina__in=_disciplinas(request.user))
    texto = (request.POST.get("texto") or "").strip()
    if not texto:
        messages.error(request, "Escreva a resposta.")
        return redirect("professor_duvidas")
    with transaction.atomic():
        RespostaProfessor.objects.update_or_create(duvida=duvida, defaults={"professor": request.user, "texto": texto})
        duvida.status = StatusDuvida.RESPONDIDA
        duvida.lida_pelo_aluno = False  # notificação ao aluno, na tela inicial e no histórico
        duvida.save(update_fields=["status", "lida_pelo_aluno"])
    messages.success(request, "Resposta enviada ao aluno.")
    return redirect("professor_duvidas")


@login_required
def revisao(request):
    """RF21: respostas avaliadas como não úteis, sem identificar o aluno (RN04 ii)."""
    disciplinas = _disciplinas(request.user)
    pendentes = request.GET.get("todas") != "1"
    qs = (Avaliacao.objects.filter(interacao__disciplina__in=disciplinas, util=False)
          .select_related("interacao__topico").prefetch_related("interacao__itens_usados")
          .order_by("-criada_em"))
    if pendentes:
        qs = qs.filter(revisada=False)
    # RN04: o texto livre pode trazer nome, e-mail ou RA; passa pelo mesmo filtro do envio ao PLN.
    filtros = {d.id: filtro_da_disciplina(d) for d in disciplinas}
    avaliacoes = []
    for av in qs[:100]:
        f = filtros[av.interacao.disciplina_id]
        av.pergunta_anonima = f.aplicar(av.interacao.pergunta)
        av.resposta_anonima = f.aplicar(av.interacao.resposta or "")
        av.justificativa_anonima = f.aplicar(av.justificativa)
        avaliacoes.append(av)
    return render(request, "pedagogico/revisao.html", {"avaliacoes": avaliacoes, "pendentes": pendentes})


@login_required
@require_POST
def marcar_revisada(request, avaliacao_id):
    av = get_object_or_404(Avaliacao, pk=avaliacao_id, interacao__disciplina__in=_disciplinas(request.user))
    av.revisada = True
    av.nota_revisao = (request.POST.get("nota") or "").strip()
    av.save(update_fields=["revisada", "nota_revisao"])
    messages.success(request, "Revisão registrada. Corrija o item no painel de conteúdo, se for o caso.")
    return redirect("professor_revisao")


@login_required
def avaliar_sistema(request):
    """Questionário SUS do mini piloto. Uma resposta por pessoa; responder de novo atualiza."""
    from .models import AFIRMACOES_SUS, ESCALA, RespostaSUS

    u = request.user
    if not (u.eh_aluno or u.eh_professor):
        raise PermissionDenied("Questionário para quem usa o tutor.")
    atual = RespostaSUS.objects.filter(usuario=u).first()
    erros = []
    if request.method == "POST":
        valores = {}
        for i in range(1, 11):
            v = request.POST.get(f"q{i}", "")
            if v not in {"1", "2", "3", "4", "5"}:
                erros.append(i)
            else:
                valores[f"q{i}"] = int(v)
        if not erros:
            valores["comentario"] = (request.POST.get("comentario") or "").strip()[:2000]
            RespostaSUS.objects.update_or_create(usuario=u, defaults=valores)
            messages.success(request, "Obrigado! Sua avaliação foi registrada.")
            return redirect("inicio")
    itens = [
        {"n": i, "texto": t, "marcado": (request.POST.get(f"q{i}") if request.method == "POST"
                                         else (str(getattr(atual, f"q{i}")) if atual else ""))}
        for i, t in enumerate(AFIRMACOES_SUS, start=1)
    ]
    return render(request, "pedagogico/avaliar_sistema.html", {
        "itens": itens, "escala": ESCALA, "erros": erros, "ja_respondeu": bool(atual),
        "comentario": request.POST.get("comentario", atual.comentario if atual else ""),
    })


def resumo_sus():
    """Agregado do SUS para o painel do professor e para o artigo."""
    import statistics

    from .models import RespostaSUS
    pontos = [r.pontuacao() for r in RespostaSUS.objects.all()]
    if not pontos:
        return None
    return {"n": len(pontos), "media": round(statistics.mean(pontos), 1),
            "dp": round(statistics.stdev(pontos), 1) if len(pontos) > 1 else None}
