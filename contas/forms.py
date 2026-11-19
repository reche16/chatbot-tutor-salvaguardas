from django import forms
from django.contrib.auth.password_validation import validate_password

from academico.models import Turma

from .models import Usuario


class CadastroAlunoForm(forms.Form):
    """Autocadastro de aluno: entra nas turmas com cadastro aberto (no MVP, a turma-piloto)."""

    first_name = forms.CharField(label="Nome", max_length=150)
    last_name = forms.CharField(label="Sobrenome", max_length=150)
    email = forms.EmailField(label="E-mail institucional")
    matricula = forms.CharField(label="Matrícula (RA)", max_length=20)
    senha = forms.CharField(label="Senha", widget=forms.PasswordInput, strip=False)
    senha2 = forms.CharField(label="Confirme a senha", widget=forms.PasswordInput, strip=False)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Já existe uma conta com este e-mail.")
        return email

    def clean(self):
        dados = super().clean()
        self.turmas = list(Turma.objects.filter(cadastro_aberto=True))
        if not self.turmas:
            raise forms.ValidationError("O cadastro de alunos está fechado no momento.")
        s1, s2 = dados.get("senha"), dados.get("senha2")
        if s1 and s2 and s1 != s2:
            self.add_error("senha2", "As senhas não conferem.")
        elif s1:
            provisorio = Usuario(email=dados.get("email", ""), first_name=dados.get("first_name", ""),
                                 last_name=dados.get("last_name", ""))
            try:
                validate_password(s1, provisorio)
            except forms.ValidationError as e:
                self.add_error("senha", e)
        return dados

    def salvar(self):
        d = self.cleaned_data
        usuario = Usuario.objects.create_user(
            d["email"], d["senha"], first_name=d["first_name"].strip(), last_name=d["last_name"].strip(),
            matricula=d["matricula"].strip(),
        )
        for turma in self.turmas:
            turma.alunos.add(usuario)
        return usuario
