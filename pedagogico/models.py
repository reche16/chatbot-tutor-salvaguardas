"""Questionário de usabilidade SUS (System Usability Scale) para o mini piloto.

Pedido do orientador em 27/10. Dez afirmações com concordância de 1 a 5 e pontuação
de 0 a 100 pelo cálculo padrão da escala. O professor vê só os agregados.
"""
from django.conf import settings
from django.db import models

AFIRMACOES_SUS = [
    "Eu acho que gostaria de usar este sistema com frequência.",
    "Eu achei o sistema desnecessariamente complexo.",
    "Eu achei o sistema fácil de usar.",
    "Eu acho que precisaria da ajuda de uma pessoa com conhecimento técnico para conseguir usar este sistema.",
    "Eu achei que as várias funções deste sistema estão bem integradas.",
    "Eu achei que havia muita inconsistência neste sistema.",
    "Eu imagino que a maioria das pessoas aprenderia a usar este sistema rapidamente.",
    "Eu achei o sistema muito trabalhoso de usar.",
    "Eu me senti muito confiante usando o sistema.",
    "Eu precisei aprender muitas coisas antes de conseguir usar este sistema.",
]
ESCALA = [(1, "Discordo totalmente"), (2, "Discordo"), (3, "Neutro"), (4, "Concordo"), (5, "Concordo totalmente")]


class RespostaSUS(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="resposta_sus")
    q1 = models.PositiveSmallIntegerField(choices=ESCALA)
    q2 = models.PositiveSmallIntegerField(choices=ESCALA)
    q3 = models.PositiveSmallIntegerField(choices=ESCALA)
    q4 = models.PositiveSmallIntegerField(choices=ESCALA)
    q5 = models.PositiveSmallIntegerField(choices=ESCALA)
    q6 = models.PositiveSmallIntegerField(choices=ESCALA)
    q7 = models.PositiveSmallIntegerField(choices=ESCALA)
    q8 = models.PositiveSmallIntegerField(choices=ESCALA)
    q9 = models.PositiveSmallIntegerField(choices=ESCALA)
    q10 = models.PositiveSmallIntegerField(choices=ESCALA)
    comentario = models.TextField("comentário", blank=True)
    respondido_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "resposta do SUS"
        verbose_name_plural = "respostas do SUS"

    def notas(self):
        return [getattr(self, f"q{i}") for i in range(1, 11)]

    def pontuacao(self):
        """Ímpares (afirmações positivas) somam nota − 1; pares, 5 − nota; total × 2,5."""
        n = self.notas()
        soma = sum(n[i] - 1 if i % 2 == 0 else 5 - n[i] for i in range(10))
        return soma * 2.5
