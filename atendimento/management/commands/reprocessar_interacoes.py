from django.core.management.base import BaseCommand

from atendimento.servicos.fila import reprocessar


class Command(BaseCommand):
    help = "Regrava as interações da fila de reprocessamento (RN05)."

    def handle(self, *args, **opts):
        gravadas, pendentes = reprocessar()
        self.stdout.write(f"gravadas: {gravadas} · pendentes: {pendentes}")
