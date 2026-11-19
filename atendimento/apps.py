import sys
import threading

from django.apps import AppConfig


class AtendimentoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'atendimento'

    def ready(self):
        # Só no servidor: cria o serviço de PLN logo ao subir, para a conexão com o
        # provedor já estar aquecida na 1ª pergunta (fora do ready, numa thread).
        servidor = "runserver" in sys.argv or any("uvicorn" in a for a in sys.argv[:1])
        if servidor:
            threading.Thread(target=_preparar_pln, daemon=True).start()


def _preparar_pln():
    try:
        from atendimento.models import ConfiguracaoPLN
        from atendimento.servicos.pln import obter_servico
        obter_servico(ConfiguracaoPLN.atual())
    except Exception:  # sem chave/credencial: a 1ª pergunta registra o erro normalmente
        pass
