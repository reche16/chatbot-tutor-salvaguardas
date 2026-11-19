"""Interface de conversação do aluno (UC01–UC06) e histórico (RF15)."""
import json
from datetime import datetime

from asgiref.sync import sync_to_async
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from academico.models import Disciplina, Exercicio, ListaExercicios, TopicoEmenta

from .models import Avaliacao, Conversa, DuvidaEncaminhada, Interacao, TipoAtendimento
from .servicos.controlador import ControladorAtendimento


def _exigir_aluno(user):
    if not user.is_authenticated or not user.eh_aluno:
        raise PermissionDenied("Área do aluno.")


def _disciplinas_do_aluno(user):
    return Disciplina.objects.filter(turmas__alunos=user).distinct()


@login_required
def inicio(request):
    u = request.user
    if not u.boas_vindas_vista and (u.eh_aluno or u.eh_professor):
        return redirect("boas_vindas")
    if u.eh_professor:
        return redirect("professor_painel")
    if u.eh_administrador:
        return redirect("admin:index")
    disciplinas = _disciplinas_do_aluno(u)
    respostas_novas = DuvidaEncaminhada.objects.filter(aluno=u, lida_pelo_aluno=False).count()
    # Depois de algum uso, convida para o questionário SUS do mini piloto.
    from pedagogico.models import RespostaSUS
    pedir_sus = (not RespostaSUS.objects.filter(usuario=u).exists()
                 and Interacao.objects.filter(conversa__aluno=u).count() >= 5)
    return render(request, "atendimento/inicio.html", {
        "disciplinas": disciplinas, "respostas_novas": respostas_novas, "pedir_sus": pedir_sus,
    })


@login_required
def chat(request, disciplina_id):
    _exigir_aluno(request.user)
    disciplina = get_object_or_404(_disciplinas_do_aluno(request.user), pk=disciplina_id)
    conversa = None
    if request.GET.get("conversa"):
        conversa = get_object_or_404(Conversa, pk=request.GET["conversa"], aluno=request.user, disciplina=disciplina)
    elif not request.GET.get("nova"):
        conversa = Conversa.objects.filter(aluno=request.user, disciplina=disciplina).first()
    if conversa is None:
        conversa = Conversa.objects.create(aluno=request.user, disciplina=disciplina)
        if request.GET.get("nova"):
            return redirect(f"{request.path}?conversa={conversa.pk}")
    interacoes = (conversa.interacoes.select_related("avaliacao", "exercicio")
                  .prefetch_related("encaminhamento").order_by("data_hora"))
    listas = ListaExercicios.objects.filter(disciplina=disciplina, aberta=True).prefetch_related("exercicios")
    return render(request, "atendimento/chat.html", {
        "disciplina": disciplina, "conversa": conversa, "interacoes": interacoes, "listas": listas,
    })


def _json(request):
    try:
        corpo = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return corpo if isinstance(corpo, dict) else None


def _texto(corpo, campo):
    """Campo de texto do JSON; outro tipo (objeto, lista, número) vira erro 400, não 500."""
    valor = corpo.get(campo)
    if valor is None:
        return ""
    if not isinstance(valor, str):
        raise ValueError(campo)
    return valor


async def api_mensagem(request, conversa_id):
    """POST assíncrono: enquanto espera o serviço externo, o processo atende outros (RNF08)."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST")
    user = await request.auser()
    if not user.is_authenticated or not user.eh_aluno:
        return JsonResponse({"erro": "não autorizado"}, status=403)
    corpo = _json(request)
    if corpo is None:
        return HttpResponseBadRequest("JSON inválido")
    try:
        mensagem = _texto(corpo, "mensagem").strip()
    except ValueError:
        return JsonResponse({"erro": "mensagem deve ser texto"}, status=400)
    if not mensagem:
        return JsonResponse({"erro": "mensagem vazia"}, status=400)
    if len(mensagem) > 4000:
        return JsonResponse({"erro": "mensagem longa demais (máx. 4000 caracteres)"}, status=400)
    existe = await sync_to_async(Conversa.objects.filter(pk=conversa_id, aluno=user).exists)()
    if not existe:
        return JsonResponse({"erro": "conversa não encontrada"}, status=404)
    tipo = corpo.get("tipo") if corpo.get("tipo") in TipoAtendimento.values else TipoAtendimento.DUVIDA
    exercicio_id = corpo.get("exercicio_id") or None
    if exercicio_id is not None:
        try:
            exercicio_id = int(exercicio_id)
        except (TypeError, ValueError):
            return JsonResponse({"erro": "exercicio_id inválido"}, status=400)
    try:
        res = await ControladorAtendimento().atender(conversa_id, mensagem, tipo, exercicio_id)
    except Exercicio.DoesNotExist:  # de outra disciplina ou lista fechada
        return JsonResponse({"erro": "exercício indisponível"}, status=404)
    return JsonResponse({
        "interacao_id": res.interacao_id, "resposta": res.resposta, "respondida": res.respondida,
        "oferece_encaminhamento": res.oferece_encaminhamento, "topico": res.topico, "tempo_ms": res.tempo_ms,
        "motivo": res.motivo,
    })


def _interacao_do_aluno(request, interacao_id):
    _exigir_aluno(request.user)
    return get_object_or_404(Interacao, pk=interacao_id, conversa__aluno=request.user)


@login_required
@require_POST
def api_avaliar(request, interacao_id):
    """RF16: útil ou não útil, com justificativa opcional."""
    inter = _interacao_do_aluno(request, interacao_id)
    corpo = _json(request) or {}
    if not isinstance(corpo.get("util"), bool):
        return JsonResponse({"erro": "informe util (true ou false)"}, status=400)
    try:
        justificativa = _texto(corpo, "justificativa")[:2000]
    except ValueError:
        return JsonResponse({"erro": "justificativa deve ser texto"}, status=400)
    Avaliacao.objects.update_or_create(interacao=inter, defaults={"util": corpo["util"], "justificativa": justificativa})
    return JsonResponse({"ok": True})


@login_required
@require_POST
def api_encaminhar(request, interacao_id):
    """RF12: encaminha ao professor, com o histórico da conversa de origem."""
    inter = _interacao_do_aluno(request, interacao_id)
    corpo = _json(request) or {}
    try:
        texto = _texto(corpo, "mensagem")[:2000]
    except ValueError:
        return JsonResponse({"erro": "mensagem deve ser texto"}, status=400)
    duvida, criada = DuvidaEncaminhada.objects.get_or_create(
        interacao=inter, defaults={"aluno": request.user, "disciplina": inter.disciplina, "mensagem": texto},
    )
    return JsonResponse({"ok": True, "ja_encaminhada": not criada})


@login_required
def historico(request):
    """RF15 e RN03: só as próprias interações, com filtro por período e tópico."""
    _exigir_aluno(request.user)
    qs = (Interacao.objects.filter(conversa__aluno=request.user)
          .select_related("topico", "disciplina", "avaliacao").order_by("-data_hora"))
    inicio, fim, topico_id = request.GET.get("inicio"), request.GET.get("fim"), request.GET.get("topico")
    tz = timezone.get_current_timezone()
    try:
        if inicio:
            qs = qs.filter(data_hora__gte=datetime.fromisoformat(inicio).replace(tzinfo=tz))
        if fim:
            qs = qs.filter(data_hora__lt=datetime.fromisoformat(fim).replace(tzinfo=tz) + timezone.timedelta(days=1))
    except ValueError:
        pass
    if topico_id and topico_id.isdigit():
        qs = qs.filter(topico_id=topico_id)
    duvidas = (DuvidaEncaminhada.objects.filter(aluno=request.user)
               .select_related("interacao", "resposta").order_by("-criada_em"))
    lidas = list(duvidas.filter(lida_pelo_aluno=False).values_list("id", flat=True))
    pagina = render(request, "atendimento/historico.html", {
        "interacoes": qs[:200], "duvidas": duvidas, "novas": set(lidas),
        "topicos": TopicoEmenta.objects.filter(disciplina__in=_disciplinas_do_aluno(request.user)),
        "filtro": {"inicio": inicio or "", "fim": fim or "", "topico": topico_id or ""},
    })
    DuvidaEncaminhada.objects.filter(id__in=lidas).update(lida_pelo_aluno=True)
    return pagina
