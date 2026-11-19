"""FiltroDadosPessoais (RN07, Quadro 23).

Troca por marcadores e-mail, CPF, telefone, matrícula e os nomes cadastrados
de alunos e professores da disciplina, antes de qualquer envio ao serviço externo.
"""
import re

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
TELEFONE = re.compile(r"(\(?\b\d{2}\)?\s?)?\b9?\d{4}[-\s]?\d{4}\b")
# Matrícula/RA: sequência longa de dígitos (8 ou mais), que não é número de exercício.
MATRICULA = re.compile(r"\b\d{8,14}\b")


class FiltroDadosPessoais:
    def __init__(self, nomes=(), identificadores=()):
        # Matrículas e e-mails cadastrados, em qualquer formato (ex.: "RA-2026-A123").
        ids = sorted({str(i).strip() for i in identificadores if i and len(str(i).strip()) >= 4}, key=len, reverse=True)
        self._ids = re.compile("|".join(map(re.escape, ids)), re.I) if ids else None
        partes = set()
        for nome in nomes:
            for p in str(nome).split():
                # Partículas e iniciais não identificam ninguém e quebrariam texto comum.
                if len(p) >= 3 and p.lower() not in {"da", "de", "do", "das", "dos"}:
                    partes.add(p)
        self._nomes = (
            re.compile(r"\b(" + "|".join(sorted(map(re.escape, partes), key=len, reverse=True)) + r")\b", re.I)
            if partes else None
        )

    def aplicar(self, texto):
        if not texto:
            return texto
        if self._ids:
            texto = self._ids.sub("[ID]", texto)
        texto = EMAIL.sub("[EMAIL]", texto)
        texto = CPF.sub("[CPF]", texto)
        texto = MATRICULA.sub("[MATRICULA]", texto)
        texto = TELEFONE.sub(lambda m: "[TELEFONE]" if len(re.sub(r"\D", "", m.group())) >= 8 else m.group(), texto)
        if self._nomes:
            texto = self._nomes.sub("[NOME]", texto)
        return texto


def filtro_da_disciplina(disciplina, *usuarios):
    """Filtro com nomes, matrículas e e-mails de quem está nas turmas da disciplina."""
    nomes, ids = set(), set()
    pessoas = list(usuarios)
    for turma in disciplina.turmas.prefetch_related("alunos", "professores"):
        pessoas += list(turma.alunos.all()) + list(turma.professores.all())
    for u in pessoas:
        nomes.update([u.first_name, u.last_name])
        ids.update([u.matricula, u.email])
    return FiltroDadosPessoais([n for n in nomes if n], [i for i in ids if i])
