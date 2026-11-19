from django.core.management.base import BaseCommand

from atendimento.servicos.retencao import anonimizar


class Command(BaseCommand):
    help = "Anonimiza as interações fora do prazo de retenção (RN08)."

    def handle(self, *args, **opts):
        self.stdout.write(f"interações anonimizadas: {anonimizar()}")
