from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from pedagogico.sites import admin_tutor

from .models import Usuario


@admin.register(Usuario, site=admin_tutor)
class UsuarioAdmin(UserAdmin):
    """RF24: cadastrar, editar, inativar e atribuir perfil."""

    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "perfil", "is_active")
    list_filter = ("perfil", "is_active")
    search_fields = ("email", "first_name", "last_name", "matricula")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Dados pessoais", {"fields": ("first_name", "last_name", "matricula")}),
        ("Acesso", {"fields": ("perfil", "is_active")}),
        ("Datas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "first_name", "last_name", "perfil",
                                                 "matricula", "password1", "password2")}),
    )
    readonly_fields = ("last_login", "date_joined")
    actions = ["inativar"]

    @admin.action(description="Inativar usuários selecionados")
    def inativar(self, request, queryset):
        queryset.update(is_active=False)
