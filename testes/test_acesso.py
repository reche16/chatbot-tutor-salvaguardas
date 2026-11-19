"""Perfis e escopo de dados (RF01, RF02, RN03, RN04) e as telas principais."""
import json

import pytest
from django.utils import timezone

from atendimento.models import Avaliacao, Conversa, DuvidaEncaminhada, Interacao
from contas.models import Perfil, Usuario
from pedagogico import metricas


def _interacao(conversa, **kw):
    return Interacao.objects.create(conversa=conversa, disciplina=conversa.disciplina, pergunta="p",
                                    resposta="r", respondida=True, data_hora=timezone.now(), **kw)


def test_login_por_email_e_inicio_por_perfil(client, piloto):
    assert client.post("/entrar/", {"username": "bruna.souza@usjt.br", "password": "senha-forte-1"}).status_code == 302
    # Primeiro acesso: boas-vindas antes de tudo; depois de "Começar", a página inicial.
    assert client.get("/").url == "/boas-vindas/"
    texto = client.get("/boas-vindas/").content.decode()
    assert "Boas-vindas" in texto and "Algoritmos" in texto and "Seus dados" in texto
    client.post("/boas-vindas/")
    r = client.get("/")
    assert r.status_code == 200 and "Abrir tutor" in r.content.decode()
    assert "Como funciona" in client.get("/como-funciona/").content.decode()
    client.logout()
    client.force_login(piloto["prof"])
    assert client.get("/").url == "/boas-vindas/"
    assert "Métricas" in client.get("/boas-vindas/").content.decode()
    client.post("/boas-vindas/")
    assert client.get("/").url == "/professor/"


def test_senha_guardada_com_hash(piloto):
    assert piloto["aluno"].password.startswith(("pbkdf2_", "argon2", "bcrypt"))


def test_professor_nao_entra_no_admin_e_aluno_nao_entra_no_conteudo(client, piloto):
    client.force_login(piloto["prof"])
    assert client.get("/admin/").status_code == 302  # manda para o login do admin
    assert client.get("/conteudo/").status_code == 200
    client.force_login(piloto["aluno"])
    assert client.get("/conteudo/").status_code == 302
    assert client.get("/professor/").status_code == 403


def test_professor_ve_so_conteudo_das_suas_disciplinas(client, piloto):
    from academico.models import Disciplina, ItemConhecimento, TopicoEmenta
    outra = Disciplina.objects.create(codigo="CAL", nome="Cálculo")
    t = TopicoEmenta.objects.create(disciplina=outra, ordem=1, titulo="Limites")
    alheio = ItemConhecimento.objects.create(topico=t, titulo="Limite", conteudo="...")
    client.force_login(piloto["prof"])
    lista = client.get("/conteudo/academico/itemconhecimento/").content.decode()
    assert "O que é uma função?" in lista and "Limite" not in lista
    assert client.get(f"/conteudo/academico/itemconhecimento/{alheio.id}/change/").status_code in (302, 403, 404)


def test_rn03_aluno_nao_avalia_nem_encaminha_interacao_alheia(client, piloto):
    conversa_outro = Conversa.objects.create(aluno=piloto["outro"], disciplina=piloto["disc"])
    alheia = _interacao(conversa_outro)
    client.force_login(piloto["aluno"])
    assert client.post(f"/api/interacao/{alheia.id}/avaliar/", json.dumps({"util": True}),
                       content_type="application/json").status_code == 404
    assert client.post(f"/api/interacao/{alheia.id}/encaminhar/", "{}", content_type="application/json").status_code == 404
    assert client.post(f"/api/conversa/{conversa_outro.id}/mensagem/", json.dumps({"mensagem": "oi"}),
                       content_type="application/json").status_code == 404


def test_rn03_historico_mostra_so_as_proprias(client, piloto):
    Interacao.objects.filter(pk=_interacao(piloto["conversa"]).pk).update(pergunta="minha pergunta")
    conversa_outro = Conversa.objects.create(aluno=piloto["outro"], disciplina=piloto["disc"])
    Interacao.objects.create(conversa=conversa_outro, disciplina=piloto["disc"], pergunta="pergunta do carlos",
                             data_hora=timezone.now())
    client.force_login(piloto["aluno"])
    html = client.get("/historico/").content.decode()
    assert "minha pergunta" in html and "pergunta do carlos" not in html


def test_fluxo_completo_pelo_chat_com_pln_simulado(client, piloto):
    """HU02 de ponta a ponta: mensagem → resposta → avaliação → encaminhamento → resposta do professor."""
    client.force_login(piloto["aluno"])
    r = client.post(f"/api/conversa/{piloto['conversa'].id}/mensagem/",
                    json.dumps({"mensagem": "o que é uma função em python? def"}), content_type="application/json")
    corpo = r.json()
    assert r.status_code == 200 and corpo["respondida"] and corpo["interacao_id"]
    iid = corpo["interacao_id"]
    assert client.post(f"/api/interacao/{iid}/avaliar/", json.dumps({"util": False, "justificativa": "faltou exemplo"}),
                       content_type="application/json").json()["ok"]
    assert client.post(f"/api/interacao/{iid}/encaminhar/", json.dumps({"mensagem": "pode explicar melhor?"}),
                       content_type="application/json").json()["ok"]
    duvida = DuvidaEncaminhada.objects.get(interacao_id=iid)

    client.force_login(piloto["prof"])
    assert "pode explicar melhor?" in client.get("/professor/duvidas/").content.decode()
    client.post(f"/professor/duvidas/{duvida.id}/responder/", {"texto": "Veja o material 2."})
    revisao = client.get("/professor/revisao/").content.decode()
    assert "faltou exemplo" in revisao and "bruna" not in revisao.lower()  # RN04: sem identificar o aluno

    client.force_login(piloto["aluno"])
    assert "Veja o material 2." in client.get("/historico/").content.decode()


def test_rn04_professor_de_outra_disciplina_nao_ve_duvida(client, piloto):
    from academico.models import Disciplina, Turma
    i = _interacao(piloto["conversa"])
    DuvidaEncaminhada.objects.create(interacao=i, aluno=piloto["aluno"], disciplina=piloto["disc"], mensagem="segredo")
    outro_prof = Usuario.objects.create_user("p2@usjt.br", "x" * 10, perfil=Perfil.PROFESSOR)
    Turma.objects.create(disciplina=Disciplina.objects.create(codigo="CAL", nome="Cálculo"), nome="B",
                         periodo="2026-2").professores.add(outro_prof)
    client.force_login(outro_prof)
    assert "segredo" not in client.get("/professor/duvidas/").content.decode()


def test_metricas_agrupam_topicos_com_menos_de_cinco_alunos(piloto):
    alunos = [Usuario.objects.create_user(f"a{n}@usjt.br", "x" * 10, perfil=Perfil.ALUNO) for n in range(5)]
    for a in alunos:
        _interacao(Conversa.objects.create(aluno=a, disciplina=piloto["disc"]), topico=piloto["t1"])
    _interacao(piloto["conversa"], topico=piloto["t2"])  # só 1 aluno
    Interacao.objects.create(conversa=piloto["conversa"], disciplina=piloto["disc"], pergunta="x",
                             respondida=False, data_hora=timezone.now())
    m = metricas.calcular(piloto["disc"])
    titulos = [t["titulo"] for t in m["por_topico"]]
    assert "Funções" in titulos and "Laços de repetição" not in titulos
    assert any(t.startswith("Outros") for t in titulos)
    assert m["total"] == 7 and m["nao_respondidas"] == 1


def test_csv_de_metricas(client, piloto):
    client.force_login(piloto["prof"])
    r = client.get(f"/professor/exportar.csv?disciplina={piloto['disc'].id}")
    assert r.status_code == 200 and "taxa_resolucao_sem_encaminhamento" in r.content.decode("utf-8-sig")


def test_anonimizacao_rn08(piloto):
    from datetime import timedelta
    from atendimento.servicos.retencao import anonimizar
    velha = _interacao(piloto["conversa"], topico=piloto["t1"])
    Interacao.objects.filter(pk=velha.pk).update(data_hora=timezone.now() - timedelta(days=400))
    Avaliacao.objects.create(interacao=velha, util=False, justificativa="texto livre")
    assert anonimizar() == 1
    velha.refresh_from_db()
    assert velha.conversa is None and velha.anonimizada and velha.topico == piloto["t1"]
    assert velha.avaliacao.justificativa == ""


@pytest.mark.django_db
def test_painel_admin_para_administrador(client):
    adm = Usuario.objects.create_superuser("adm@usjt.br", "x" * 10)
    client.force_login(adm)
    assert client.get("/admin/").status_code == 200
    assert client.get("/admin/atendimento/configuracaopln/").status_code == 200
    assert client.get("/admin/atendimento/interacao/").status_code == 200


@pytest.mark.django_db
def test_administrador_cadastrado_pelo_fluxo_normal_gerencia_usuarios(client):
    adm = Usuario.objects.create_user("adm2@usjt.br", "x" * 10, perfil=Perfil.ADMINISTRADOR)
    client.force_login(adm)
    assert client.get("/admin/contas/usuario/add/").status_code == 200
    adm.perfil = Perfil.PROFESSOR
    adm.save()
    assert not adm.is_superuser


def test_revisao_nao_mostra_dados_pessoais_no_texto(client, piloto):
    i = _interacao(piloto["conversa"])
    Interacao.objects.filter(pk=i.pk).update(pergunta="Sou Bruna Souza, bruna.souza@usjt.br, me ajuda")
    Avaliacao.objects.create(interacao=i, util=False, justificativa="meu RA é 823456789")
    client.force_login(piloto["prof"])
    html = client.get("/professor/revisao/").content.decode()
    for dado in ("Bruna", "Souza", "bruna.souza@usjt.br", "823456789"):
        assert dado not in html


def test_cadastro_de_aluno_entra_na_turma(client, piloto):
    from academico.models import Turma
    turma = Turma.objects.get(disciplina=piloto["disc"])
    dados = {"first_name": "Davi", "last_name": "Teste", "email": "Davi@Usjt.br", "matricula": "RA123",
             "senha": "uma-senha-boa-9", "senha2": "uma-senha-boa-9"}
    r = client.post("/cadastro/", dados)
    assert r.status_code == 302
    u = Usuario.objects.get(email="davi@usjt.br")
    assert u.perfil == Perfil.ALUNO and not u.is_staff and turma.alunos.filter(pk=u.pk).exists()
    client.logout()
    assert client.post("/entrar/", {"username": "DAVI@usjt.br", "password": "uma-senha-boa-9"}).status_code == 302


def test_cadastro_recusa_email_repetido_senha_diferente_e_cadastro_fechado(client, piloto):
    from academico.models import Turma
    base = {"first_name": "X", "last_name": "Y", "matricula": "1", "senha": "uma-senha-boa-9", "senha2": "uma-senha-boa-9"}
    assert client.post("/cadastro/", {**base, "email": "bruna.souza@usjt.br"}).status_code == 200
    assert client.post("/cadastro/", {**base, "email": "n1@usjt.br", "senha2": "outra-senha-9"}).status_code == 200
    Turma.objects.update(cadastro_aberto=False)
    assert client.post("/cadastro/", {**base, "email": "n2@usjt.br"}).status_code == 200
    assert not Usuario.objects.filter(email__in=["n1@usjt.br", "n2@usjt.br"]).exists()


def test_tipos_invalidos_no_json_dao_400_e_nao_500(client, piloto):
    i = _interacao(piloto["conversa"])
    client.force_login(piloto["aluno"])
    casos = [
        (f"/api/conversa/{piloto['conversa'].id}/mensagem/", {"mensagem": {"x": 1}}),
        (f"/api/conversa/{piloto['conversa'].id}/mensagem/", {"mensagem": "oi", "exercicio_id": "abc"}),
        (f"/api/interacao/{i.id}/avaliar/", {"util": "sim"}),
        (f"/api/interacao/{i.id}/avaliar/", {"util": True, "justificativa": ["x"]}),
        (f"/api/interacao/{i.id}/encaminhar/", {"mensagem": {"x": 1}}),
    ]
    for url, corpo in casos:
        assert client.post(url, json.dumps(corpo), content_type="application/json").status_code == 400, (url, corpo)
    assert client.post(f"/api/interacao/{i.id}/avaliar/", "[1,2]", content_type="application/json").status_code == 400


def test_questionario_sus_calcula_a_pontuacao_padrao(client, piloto):
    from pedagogico.models import RespostaSUS
    from pedagogico.views import resumo_sus
    client.force_login(piloto["aluno"])
    assert client.get("/avaliar-sistema/").status_code == 200
    incompleto = {f"q{i}": "3" for i in range(1, 10)}  # falta a 10
    assert client.post("/avaliar-sistema/", incompleto).status_code == 200 and not RespostaSUS.objects.exists()
    melhor = {f"q{i}": ("5" if i % 2 else "1") for i in range(1, 11)}
    assert client.post("/avaliar-sistema/", {**melhor, "comentario": "bom"}).status_code == 302
    assert RespostaSUS.objects.get(usuario=piloto["aluno"]).pontuacao() == 100.0
    client.force_login(piloto["outro"])
    client.post("/avaliar-sistema/", {f"q{i}": "3" for i in range(1, 11)})  # neutro = 50
    assert resumo_sus() == {"n": 2, "media": 75.0, "dp": 35.4}
    client.force_login(piloto["prof"])
    piloto["prof"].boas_vindas_vista = True
    piloto["prof"].save()
    assert "usabilidade (SUS" in client.get("/professor/").content.decode()


def test_markdown_nas_telas_do_professor_escapa_html():
    from atendimento.templatetags.tutor_extras import markdown_simples
    html = str(markdown_simples("**negrito** e `x = 1` <script>alert(1)</script>\n```python\nprint('<b>')\n```"))
    assert "<strong>negrito</strong>" in html and "<code>x = 1</code>" in html
    assert "<script>" not in html and "&lt;script&gt;" in html and "<pre><code>print(&#x27;&lt;b&gt;&#x27;)</code></pre>" in html
