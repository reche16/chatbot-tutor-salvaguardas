"""Os dois sites administrativos (Seção 4.3.1, Quadro 15).

- AdminTutor (/admin/): só administrador. Usuários, disciplinas, turmas e PLN.
- ConteudoSite (/conteudo/): só professor. Base de conhecimento e listas, filtradas
  pelas disciplinas que ele leciona (RF02, RN04). O professor não entra no /admin/.
"""
from django.contrib import admin


class AdminTutor(admin.AdminSite):
    site_header = "Chatbot Tutor — Administração"
    site_title = "Administração"
    index_title = "Painel do administrador"

    def has_permission(self, request):
        u = request.user
        return u.is_active and u.is_authenticated and u.eh_administrador


class ConteudoSite(admin.AdminSite):
    site_header = "Chatbot Tutor — Painel de conteúdo"
    site_title = "Conteúdo"
    index_title = "Base de conhecimento e listas de exercícios"
    site_url = "/professor/"

    def has_permission(self, request):
        u = request.user
        return u.is_active and u.is_authenticated and u.eh_professor


admin_tutor = AdminTutor(name="admin")
conteudo_site = ConteudoSite(name="conteudo")


class EscopoProfessorMixin:
    """Permissões pelo vínculo professor–turma, sem depender de grupos do Django."""

    caminho_disciplina = "disciplina"

    def _disciplinas(self, request):
        from academico.models import Disciplina
        return Disciplina.objects.filter(turmas__professores=request.user).distinct()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(**{f"{self.caminho_disciplina}__in": self._disciplinas(request)})

    def _pode(self, request, obj=None):
        if not request.user.eh_professor:
            return False
        if obj is None:
            return True
        return self.get_queryset(request).filter(pk=obj.pk).exists()

    def has_module_permission(self, request):
        return request.user.eh_professor

    def has_view_permission(self, request, obj=None):
        return self._pode(request, obj)

    has_change_permission = has_view_permission
    has_delete_permission = has_view_permission

    def has_add_permission(self, request):
        return request.user.eh_professor

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        from academico.models import Disciplina, ListaExercicios, TopicoEmenta
        disc = self._disciplinas(request)
        if db_field.related_model is Disciplina:
            kwargs["queryset"] = disc
        elif db_field.related_model is TopicoEmenta:
            kwargs["queryset"] = TopicoEmenta.objects.filter(disciplina__in=disc)
        elif db_field.related_model is ListaExercicios:
            kwargs["queryset"] = ListaExercicios.objects.filter(disciplina__in=disc)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
