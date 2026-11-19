from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render

from .forms import CadastroAlunoForm


def cadastro(request):
    if request.user.is_authenticated:
        return redirect("inicio")
    form = CadastroAlunoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            usuario = form.salvar()
        login(request, usuario, backend="django.contrib.auth.backends.ModelBackend")
        return redirect("inicio")
    return render(request, "contas/cadastro.html", {"form": form})


@login_required
def boas_vindas(request):
    """Primeiro acesso: o que é o sistema, o que dá para fazer, as regras e o uso dos dados.

    Depois de "Começar", a mesma página fica em /como-funciona/ (link no topo).
    """
    u = request.user
    if request.method == "POST":
        if not u.boas_vindas_vista:
            u.boas_vindas_vista = True
            u.save(update_fields=["boas_vindas_vista"])
        return redirect("inicio")
    if u.eh_administrador and not u.eh_professor:
        return redirect("admin:index")
    from academico.models import Disciplina
    if u.eh_professor:
        disciplinas = Disciplina.objects.filter(turmas__professores=u).distinct()
    else:
        disciplinas = Disciplina.objects.filter(turmas__alunos=u).distinct()
    return render(request, "contas/boas_vindas.html", {
        "primeira_vez": not u.boas_vindas_vista, "disciplinas": disciplinas,
    })
