from django.contrib import admin

from .models import RespostaSUS
from .sites import admin_tutor


@admin.register(RespostaSUS, site=admin_tutor)
class RespostaSUSAdmin(admin.ModelAdmin):
    list_display = ("usuario", "pontuacao", "respondido_em")
    readonly_fields = ("usuario", "respondido_em")

    @admin.display(description="SUS (0–100)")
    def pontuacao(self, obj):
        return obj.pontuacao()
