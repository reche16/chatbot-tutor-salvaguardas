"""Atendimento (Seção 4.1): conversa, interação, avaliação, dúvida encaminhada e
a configuração do serviço de PLN (RF26)."""
import uuid

from django.conf import settings
from django.db import models

from academico.models import Disciplina, Exercicio, ItemConhecimento, TopicoEmenta


class Provedor(models.TextChoices):
    SIMULADO = "simulado", "Simulado (sem chamada externa)"
    ANTHROPIC = "anthropic", "Anthropic (Claude API)"
    GEMINI = "gemini", "Google Gemini (Vertex AI ou API key)"


class NivelRaciocinio(models.TextChoices):
    MINIMO = "minimal", "Mínimo (mais barato e rápido)"
    BAIXO = "low", "Baixo"
    MEDIO = "medium", "Médio"


class ConfiguracaoPLN(models.Model):
    """Classe ServicoPLN do diagrama: os parâmetros que o administrador configura.

    A credencial não fica no banco (RNF04): ref_credencial é só o nome da
    variável de ambiente que guarda a chave.
    """

    provedor = models.CharField(max_length=20, choices=Provedor.choices, default=Provedor.SIMULADO)
    modelo_interpretar = models.CharField(max_length=100, default="claude-haiku-5-5")
    modelo_gerar = models.CharField(max_length=100, default="claude-haiku-5-5")
    endpoint = models.URLField(blank=True, help_text="Vazio = endpoint padrão do provedor.")
    ref_credencial = models.CharField(
        max_length=100, default="ANTHROPIC_API_KEY", blank=True,
        help_text="Nome da variável de ambiente com a chave. No Gemini via Vertex AI fica vazio (usa ADC).",
    )
    projeto_gcp = models.CharField(
        "projeto do Google Cloud", max_length=100, blank=True,
        help_text="Gemini: preenchido = Vertex AI com credencial ADC/conta de serviço (sem chave); vazio = API key.",
    )
    regiao_gcp = models.CharField("região do Vertex AI", max_length=40, default="global", blank=True)
    nivel_raciocinio = models.CharField(
        max_length=10, choices=NivelRaciocinio.choices, default=NivelRaciocinio.MINIMO,
        help_text="Esforço de raciocínio do modelo (Gemini). Mínimo gasta menos e responde mais rápido.",
    )
    limite_requisicoes = models.PositiveIntegerField("limite de requisições por minuto", default=50)
    timeout_interpretar_ms = models.PositiveIntegerField(default=1500)
    timeout_gerar_ms = models.PositiveIntegerField(default=3500)
    prazo_total_ms = models.PositiveIntegerField(default=5000)
    max_tokens_resposta = models.PositiveIntegerField(default=350)
    temperatura = models.FloatField(
        default=1.0, help_text="Gemini 3: o Google recomenda manter 1,0 (valores menores podem degradar o raciocínio). "
                               "O Claude Haiku 5.5 não aceita ajuste e ignora este campo.",
    )
    limiar_confianca = models.FloatField(default=0.5, help_text="Abaixo disso, a pergunta fica sem tópico (RF11).")
    limiar_similaridade_codigo = models.FloatField(default=0.8)
    max_linhas_codigo_avaliativa = models.PositiveIntegerField(default=4)

    class Meta:
        verbose_name = "configuração do serviço de PLN"
        verbose_name_plural = "configuração do serviço de PLN"

    def __str__(self):
        return f"{self.get_provedor_display()} · {self.modelo_gerar}"

    @classmethod
    def atual(cls):
        obj = cls.objects.first()
        return obj or cls.objects.create()


class Conversa(models.Model):
    aluno = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversas")
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE, related_name="conversas")
    iniciada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-iniciada_em"]

    def __str__(self):
        return f"Conversa {self.pk} ({self.disciplina.codigo})"

    def obter_contexto(self, n=3):
        """As n interações anteriores, da mais antiga para a mais nova (RF10)."""
        anteriores = list(self.interacoes.order_by("-data_hora")[:n])
        return list(reversed(anteriores))


class TipoAtendimento(models.TextChoices):
    DUVIDA = "DUVIDA", "Dúvida (UC01)"
    CONCEITO = "CONCEITO", "Explicação de conceito (UC02)"
    EXERCICIO = "EXERCICIO", "Orientação em exercício (UC03)"


class Interacao(models.Model):
    """Par pergunta–resposta (RF14). Registrada mesmo sem resposta (RN05)."""

    conversa = models.ForeignKey(Conversa, on_delete=models.CASCADE, related_name="interacoes", null=True)
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE, related_name="interacoes")
    tipo = models.CharField(max_length=10, choices=TipoAtendimento.choices, default=TipoAtendimento.DUVIDA)
    exercicio = models.ForeignKey(Exercicio, on_delete=models.SET_NULL, null=True, blank=True)
    pergunta = models.TextField()
    resposta = models.TextField(null=True, blank=True)
    respondida = models.BooleanField(default=False)
    motivo_sem_resposta = models.CharField(max_length=40, blank=True)
    topico = models.ForeignKey(TopicoEmenta, on_delete=models.SET_NULL, null=True, blank=True)
    confianca = models.FloatField(null=True, blank=True)
    itens_usados = models.ManyToManyField(ItemConhecimento, blank=True, related_name="interacoes")
    modelo_pln = models.CharField(max_length=100, blank=True)
    versao_prompt = models.CharField(max_length=20, blank=True)
    bloqueada_verificacao = models.BooleanField(default=False)
    motivo_bloqueio = models.CharField(max_length=60, blank=True)
    confirmada_localmente = models.BooleanField(default=False)
    oferece_encaminhamento = models.BooleanField(default=False)
    tempo_resposta_ms = models.PositiveIntegerField(null=True)
    tempos_etapas = models.JSONField(default=dict, blank=True)
    correlacao = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    data_hora = models.DateTimeField()
    anonimizada = models.BooleanField(default=False)

    class Meta:
        ordering = ["-data_hora"]
        verbose_name = "interação"
        verbose_name_plural = "interações"
        indexes = [models.Index(fields=["disciplina", "data_hora"])]

    def __str__(self):
        return f"Interação {self.pk}"


class Avaliacao(models.Model):
    interacao = models.OneToOneField(Interacao, on_delete=models.CASCADE, related_name="avaliacao")
    util = models.BooleanField()
    justificativa = models.TextField(blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    revisada = models.BooleanField(default=False)
    nota_revisao = models.TextField("correção registrada pelo professor", blank=True)

    class Meta:
        verbose_name = "avaliação"
        verbose_name_plural = "avaliações"


class StatusDuvida(models.TextChoices):
    ABERTA = "ABERTA", "Aberta"
    RESPONDIDA = "RESPONDIDA", "Respondida"


class DuvidaEncaminhada(models.Model):
    interacao = models.OneToOneField(Interacao, on_delete=models.CASCADE, related_name="encaminhamento")
    aluno = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="duvidas_enviadas")
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE, related_name="duvidas")
    mensagem = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=StatusDuvida.choices, default=StatusDuvida.ABERTA)
    criada_em = models.DateTimeField(auto_now_add=True)
    lida_pelo_aluno = models.BooleanField(default=True)

    class Meta:
        ordering = ["-criada_em"]
        verbose_name = "dúvida encaminhada"
        verbose_name_plural = "dúvidas encaminhadas"


class RespostaProfessor(models.Model):
    duvida = models.OneToOneField(DuvidaEncaminhada, on_delete=models.CASCADE, related_name="resposta")
    professor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    texto = models.TextField()
    respondida_em = models.DateTimeField(auto_now_add=True)
