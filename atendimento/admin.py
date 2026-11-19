from django.contrib import admin
from django.db.models import Avg, Count, Q

from pedagogico.sites import admin_tutor

from .models import ConfiguracaoPLN, Interacao


@admin.register(ConfiguracaoPLN, site=admin_tutor)
class ConfiguracaoPLNAdmin(admin.ModelAdmin):
    """RF26. A chave fica no ambiente; aqui só o nome da variável."""

    list_display = ("provedor", "modelo_interpretar", "modelo_gerar", "limite_requisicoes")
    fieldsets = (
        ("Provedor", {"fields": ("provedor", "modelo_interpretar", "modelo_gerar", "nivel_raciocinio", "temperatura", "endpoint",
                                 "ref_credencial", "projeto_gcp", "regiao_gcp")}),
        ("Limites e tempos (Quadro 22)", {"fields": ("limite_requisicoes", "timeout_interpretar_ms",
                                                    "timeout_gerar_ms", "prazo_total_ms", "max_tokens_resposta")}),
        ("Salvaguardas (Seção 4.3.4)", {"fields": ("limiar_confianca", "limiar_similaridade_codigo",
                                                   "max_linhas_codigo_avaliativa")}),
    )

    def has_add_permission(self, request):
        return not ConfiguracaoPLN.objects.exists()


@admin.register(Interacao, site=admin_tutor)
class InteracaoMonitorAdmin(admin.ModelAdmin):
    """Monitoramento técnico (RF27). Sem o texto das perguntas (Quadro 24)."""

    list_display = ("data_hora", "disciplina", "tipo", "respondida", "motivo_sem_resposta",
                    "bloqueada_verificacao", "tempo_resposta_ms", "modelo_pln", "versao_prompt")
    list_filter = ("disciplina", "tipo", "respondida", "bloqueada_verificacao", "modelo_pln")
    fields = list_display + ("tempos_etapas", "correlacao")
    readonly_fields = fields
    date_hierarchy = "data_hora"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        resp = super().changelist_view(request, extra_context)
        try:
            qs = resp.context_data["cl"].queryset
        except (AttributeError, KeyError):
            return resp
        tempos = sorted(qs.exclude(tempo_resposta_ms=None).values_list("tempo_resposta_ms", flat=True))
        p95 = tempos[max(0, int(len(tempos) * 0.95) - 1)] if tempos else None
        agg = qs.aggregate(total=Count("id"), media=Avg("tempo_resposta_ms"),
                           erros=Count("id", filter=Q(motivo_sem_resposta__startswith="pln_")))
        resp.context_data["title"] = (
            f"Interações: {agg['total']} · p95 {p95 or '-'} ms · média {int(agg['media'] or 0)} ms · "
            f"falhas do PLN {agg['erros']}"
        )
        return resp
