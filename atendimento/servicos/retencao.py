"""Retenção e anonimização (RN08, Quadro 25).

Interações ficam identificadas até o fim do semestre seguinte ao período letivo.
Depois perdem o vínculo com o aluno e os textos livres; ficam só os campos das
métricas agregadas (tópico, tipo, data, tempos, respondida, bloqueio).
"""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from atendimento.models import Avaliacao, DuvidaEncaminhada, Interacao

# Aproximação do "fim do semestre seguinte": 12 meses depois da interação.
PRAZO = timedelta(days=365)


@transaction.atomic
def anonimizar(antes_de=None):
    limite = antes_de or timezone.now() - PRAZO
    qs = Interacao.objects.filter(data_hora__lt=limite, anonimizada=False)
    ids = list(qs.values_list("id", flat=True))
    DuvidaEncaminhada.objects.filter(interacao_id__in=ids).delete()  # tem o aluno e o texto
    Avaliacao.objects.filter(interacao_id__in=ids).update(justificativa="", nota_revisao="")
    n = qs.update(conversa=None, pergunta="[anonimizada]", resposta=None, anonimizada=True)
    return n
