"""Contexto acadêmico (Seção 4.1): disciplina, turma, ementa, base e exercícios."""
from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords


class Disciplina(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nome = models.CharField(max_length=200)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return f"{self.codigo} — {self.nome}"


def gerar_codigo_convite():
    import secrets
    alfabeto = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sem 0/O e 1/I, que se confundem
    return "".join(secrets.choice(alfabeto) for _ in range(8))


class Turma(models.Model):
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE, related_name="turmas")
    nome = models.CharField(max_length=100)
    periodo = models.CharField("período letivo", max_length=20, help_text="ex.: 2026-2")
    codigo_convite = models.CharField(
        "código de convite", max_length=12, unique=True, default=gerar_codigo_convite,
        help_text="Reservado para convite por código (não usado no MVP).",
    )
    cadastro_aberto = models.BooleanField(
        "cadastro de alunos aberto", default=True,
        help_text="Quem se cadastra pela página /cadastro/ entra nas turmas com esta opção ligada.",
    )
    alunos = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="turmas_matriculado", blank=True,
        limit_choices_to={"perfil": "ALUNO"},
    )
    professores = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="turmas_leciona", blank=True,
        limit_choices_to={"perfil": "PROFESSOR"},
    )

    def __str__(self):
        return f"{self.disciplina.codigo} {self.nome} ({self.periodo})"


class TopicoEmenta(models.Model):
    """Tópico da ementa. A Ementa do diagrama é o conjunto de tópicos da disciplina."""

    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE, related_name="topicos")
    ordem = models.PositiveIntegerField()
    titulo = models.CharField(max_length=200)
    palavras_chave = models.CharField(
        max_length=500, blank=True, help_text="Separadas por vírgula. Usadas na classificação local."
    )
    descricao = models.TextField(blank=True)

    class Meta:
        ordering = ["disciplina", "ordem"]
        unique_together = [("disciplina", "ordem")]
        verbose_name = "tópico da ementa"
        verbose_name_plural = "tópicos da ementa"

    def __str__(self):
        return f"{self.ordem}. {self.titulo}"

    def lista_palavras_chave(self):
        return [p.strip() for p in self.palavras_chave.split(",") if p.strip()]


class TipoConteudo(models.TextChoices):
    FAQ = "FAQ", "Pergunta frequente"
    MATERIAL = "MATERIAL", "Material de apoio"


class ItemConhecimento(models.Model):
    """Item da base de conhecimento; pertence a um tópico (associação "agrupa")."""

    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE, related_name="itens")
    topico = models.ForeignKey(TopicoEmenta, on_delete=models.CASCADE, related_name="itens")
    tipo = models.CharField(max_length=10, choices=TipoConteudo.choices, default=TipoConteudo.MATERIAL)
    titulo = models.CharField(max_length=300)
    conteudo = models.TextField()
    ativo = models.BooleanField(default=True)
    history = HistoricalRecords()  # RF28

    class Meta:
        ordering = ["topico__ordem", "tipo", "id"]
        verbose_name = "item de conhecimento"
        verbose_name_plural = "base de conhecimento"

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        self.disciplina_id = self.topico.disciplina_id
        super().save(*args, **kwargs)


class ListaExercicios(models.Model):
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE, related_name="listas")
    titulo = models.CharField(max_length=200)
    avaliativa = models.BooleanField(
        default=False, help_text="Em lista avaliativa, gabarito e passos nunca vão ao serviço de PLN (RN06)."
    )
    aberta = models.BooleanField(default=True, help_text="Lista disponível aos alunos.")
    history = HistoricalRecords()

    class Meta:
        verbose_name = "lista de exercícios"
        verbose_name_plural = "listas de exercícios"

    def __str__(self):
        tipo = "avaliativa" if self.avaliativa else "prática"
        return f"{self.titulo} ({tipo})"


class Exercicio(models.Model):
    lista = models.ForeignKey(ListaExercicios, on_delete=models.CASCADE, related_name="exercicios")
    topico = models.ForeignKey(TopicoEmenta, on_delete=models.SET_NULL, null=True, blank=True)
    ordem = models.PositiveIntegerField(default=1)
    enunciado = models.TextField()
    resposta_esperada = models.TextField()
    passos = models.TextField("passos de resolução", blank=True)
    dicas = models.TextField(blank=True, help_text="Uma dica por linha, da mais vaga para a mais concreta.")
    history = HistoricalRecords()  # RF28

    class Meta:
        ordering = ["lista", "ordem"]
        verbose_name = "exercício"

    def __str__(self):
        return f"{self.lista.titulo} — exercício {self.ordem}"

    def lista_dicas(self):
        return [d.strip() for d in self.dicas.splitlines() if d.strip()]

    def dados_para_pln(self):
        """O que pode ir ao serviço externo (Seção 4.2.2, RN06).

        Em lista avaliativa, só enunciado e dicas; gabarito e passos ficam no sistema.
        """
        dados = {"enunciado": self.enunciado, "dicas": self.lista_dicas()}
        if not self.lista.avaliativa:
            dados["passos"] = self.passos
            dados["resposta_esperada"] = self.resposta_esperada
        return dados
