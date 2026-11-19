from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from pedagogico.sites import EscopoProfessorMixin, admin_tutor, conteudo_site

from .models import Disciplina, Exercicio, ItemConhecimento, ListaExercicios, TopicoEmenta, Turma


# ---------------------------------------------------------------- administrador (RF24, RF25)

class TurmaInline(admin.TabularInline):
    model = Turma
    extra = 0
    filter_horizontal = ("alunos", "professores")


@admin.register(Disciplina, site=admin_tutor)
class DisciplinaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nome")
    search_fields = ("codigo", "nome")


@admin.register(Turma, site=admin_tutor)
class TurmaAdmin(admin.ModelAdmin):
    list_display = ("__str__", "disciplina", "periodo", "codigo_convite", "cadastro_aberto")
    list_editable = ("cadastro_aberto",)
    list_filter = ("disciplina", "periodo")
    filter_horizontal = ("alunos", "professores")


@admin.register(TopicoEmenta, site=admin_tutor)
class TopicoEmentaAdminTutor(admin.ModelAdmin):
    list_display = ("ordem", "titulo", "disciplina")
    list_filter = ("disciplina",)


# ---------------------------------------------------------------- professor (RF18, RF19, RF28)

class SoProfessorInline:
    def has_view_permission(self, request, obj=None):
        return request.user.eh_professor

    has_change_permission = has_add_permission = has_delete_permission = has_view_permission


@admin.register(TopicoEmenta, site=conteudo_site)
class TopicoEmentaAdmin(EscopoProfessorMixin, admin.ModelAdmin):
    list_display = ("ordem", "titulo", "disciplina", "qtd_itens")
    # RelatedOnly: o filtro só lista o que está no escopo do professor (RN04).
    list_filter = (("disciplina", admin.RelatedOnlyFieldListFilter),)
    search_fields = ("titulo", "palavras_chave")

    @admin.display(description="itens")
    def qtd_itens(self, obj):
        return obj.itens.filter(ativo=True).count()


@admin.register(ItemConhecimento, site=conteudo_site)
class ItemConhecimentoAdmin(EscopoProfessorMixin, SimpleHistoryAdmin):
    list_display = ("titulo", "topico", "tipo", "ativo")
    list_filter = ("tipo", "ativo", ("disciplina", admin.RelatedOnlyFieldListFilter), ("topico", admin.RelatedOnlyFieldListFilter))
    search_fields = ("titulo", "conteudo")
    exclude = ("disciplina",)  # vem do tópico
    history_list_display = ("tipo", "ativo")


class ExercicioInline(SoProfessorInline, admin.StackedInline):
    model = Exercicio
    extra = 0
    fields = ("ordem", "topico", "enunciado", "resposta_esperada", "passos", "dicas")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "topico":
            kwargs["queryset"] = TopicoEmenta.objects.filter(disciplina__turmas__professores=request.user).distinct()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(ListaExercicios, site=conteudo_site)
class ListaExerciciosAdmin(EscopoProfessorMixin, SimpleHistoryAdmin):
    list_display = ("titulo", "disciplina", "avaliativa", "aberta")
    list_filter = ("avaliativa", "aberta", ("disciplina", admin.RelatedOnlyFieldListFilter))
    inlines = [ExercicioInline]


@admin.register(Exercicio, site=conteudo_site)
class ExercicioAdmin(EscopoProfessorMixin, SimpleHistoryAdmin):
    """Para consultar o histórico de alterações de cada exercício (RF28)."""

    caminho_disciplina = "lista__disciplina"
    list_display = ("__str__", "topico")
    list_filter = (("lista", admin.RelatedOnlyFieldListFilter),)
