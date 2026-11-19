from celery import shared_task

from .servicos.fila import reprocessar
from .servicos.retencao import anonimizar


@shared_task
def reprocessar_interacoes():
    return reprocessar()


@shared_task
def anonimizar_interacoes():
    return anonimizar()
