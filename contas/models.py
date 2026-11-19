"""Usuários (Seção 4.1, grupo Usuários).

A classe abstrata Usuario do diagrama vira um único modelo; as especializações
Aluno, Professor e Administrador são os valores do campo perfil, porque têm os
mesmos dados de acesso. O login é pelo e-mail institucional (RF01).
"""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class Perfil(models.TextChoices):
    ALUNO = "ALUNO", "Aluno"
    PROFESSOR = "PROFESSOR", "Professor"
    ADMINISTRADOR = "ADMINISTRADOR", "Administrador"


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("O e-mail é obrigatório.")
        usuario = self.model(email=self.normalize_email(email).lower(), **extra)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def get_by_natural_key(self, email):
        # Login sem diferenciar maiúsculas no e-mail.
        return self.get(email__iexact=email)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("perfil", Perfil.ADMINISTRADOR)
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra)


class Usuario(AbstractUser):
    username = None
    email = models.EmailField("e-mail institucional", unique=True)
    perfil = models.CharField(max_length=20, choices=Perfil.choices, default=Perfil.ALUNO)
    matricula = models.CharField(max_length=20, blank=True)
    boas_vindas_vista = models.BooleanField(
        "já viu as boas-vindas", default=False,
        help_text="No primeiro acesso, aluno e professor veem a página que explica o sistema.",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UsuarioManager()

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"

    def __str__(self):
        return self.get_full_name() or self.email

    @property
    def eh_aluno(self):
        return self.perfil == Perfil.ALUNO

    @property
    def eh_professor(self):
        return self.perfil == Perfil.PROFESSOR

    @property
    def eh_administrador(self):
        return self.perfil == Perfil.ADMINISTRADOR or self.is_superuser

    def save(self, *args, **kwargs):
        # RF02: o painel do Django (is_staff) só para administrador e professor;
        # cada um entra no seu site (admin ou conteúdo), não no do outro.
        # O administrador tem todas as permissões do /admin/ (RF24–RF27); os outros perfis, nenhuma.
        self.is_superuser = self.perfil == Perfil.ADMINISTRADOR
        self.is_staff = self.perfil in (Perfil.ADMINISTRADOR, Perfil.PROFESSOR)
        super().save(*args, **kwargs)
