from django.contrib.auth import views as auth_views
from django.urls import path

from atendimento import views as at
from contas import views as contas_views
from pedagogico import views as pd
from pedagogico.sites import admin_tutor, conteudo_site

urlpatterns = [
    path("admin/", admin_tutor.urls),
    path("conteudo/", conteudo_site.urls),
    path("entrar/", auth_views.LoginView.as_view(template_name="contas/login.html"), name="login"),
    path("sair/", auth_views.LogoutView.as_view(), name="logout"),
    path("cadastro/", contas_views.cadastro, name="cadastro"),
    path("boas-vindas/", contas_views.boas_vindas, name="boas_vindas"),
    path("como-funciona/", contas_views.boas_vindas, name="como_funciona"),
    path("senha/", auth_views.PasswordResetView.as_view(template_name="contas/redefinir.html"), name="password_reset"),
    path("senha/enviada/", auth_views.PasswordResetDoneView.as_view(template_name="contas/redefinir_enviado.html"),
         name="password_reset_done"),
    path("senha/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(template_name="contas/redefinir_nova.html"),
         name="password_reset_confirm"),
    path("senha/pronto/", auth_views.PasswordResetCompleteView.as_view(template_name="contas/redefinir_pronto.html"),
         name="password_reset_complete"),
    path("", at.inicio, name="inicio"),
    path("chat/<int:disciplina_id>/", at.chat, name="chat"),
    path("historico/", at.historico, name="historico"),
    path("api/conversa/<int:conversa_id>/mensagem/", at.api_mensagem, name="api_mensagem"),
    path("api/interacao/<int:interacao_id>/avaliar/", at.api_avaliar, name="api_avaliar"),
    path("api/interacao/<int:interacao_id>/encaminhar/", at.api_encaminhar, name="api_encaminhar"),
    path("avaliar-sistema/", pd.avaliar_sistema, name="avaliar_sistema"),
    path("professor/", pd.painel, name="professor_painel"),
    path("professor/exportar.csv", pd.exportar_csv, name="professor_csv"),
    path("professor/duvidas/", pd.duvidas, name="professor_duvidas"),
    path("professor/duvidas/<int:duvida_id>/responder/", pd.responder_duvida, name="professor_responder"),
    path("professor/revisao/", pd.revisao, name="professor_revisao"),
    path("professor/revisao/<int:avaliacao_id>/", pd.marcar_revisada, name="professor_revisada"),
]
