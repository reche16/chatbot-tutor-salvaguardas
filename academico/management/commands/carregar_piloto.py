"""Carrega a disciplina-piloto (Algoritmos e Programação) e usuários de demonstração.

    python manage.py carregar_piloto [--arquivo dados/disciplina_piloto.json] [--senha ...] [--sem-usuarios]

Idempotente: rodar de novo atualiza o conteúdo sem duplicar.
"""
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from academico.models import Disciplina, Exercicio, ItemConhecimento, ListaExercicios, TopicoEmenta, Turma
from atendimento.models import ConfiguracaoPLN
from contas.models import Perfil, Usuario

USUARIOS_DEMO = [
    ("admin@tutor.local", "Ana", "Administradora", Perfil.ADMINISTRADOR, ""),
    ("professor@tutor.local", "Paulo", "Professor", Perfil.PROFESSOR, ""),
    ("aluno1@tutor.local", "Bruna", "Souza", Perfil.ALUNO, "20260001"),
    ("aluno2@tutor.local", "Carlos", "Lima", Perfil.ALUNO, "20260002"),
    ("avaliacao@tutor.local", "Aluno", "Avaliação", Perfil.ALUNO, ""),
]


class Command(BaseCommand):
    help = "Carrega a disciplina-piloto e usuários de demonstração."

    def add_arguments(self, parser):
        parser.add_argument("--arquivo", default=str(Path(settings.BASE_DIR) / "dados" / "disciplina_piloto.json"))
        parser.add_argument("--senha", default="tutor12345", help="Senha dos usuários de demonstração.")
        parser.add_argument("--sem-usuarios", action="store_true")

    @transaction.atomic
    def handle(self, *args, **opts):
        dados = json.loads(Path(opts["arquivo"]).read_text(encoding="utf-8"))
        d = dados["disciplina"]
        disciplina, _ = Disciplina.objects.update_or_create(codigo=d["codigo"], defaults={"nome": d["nome"]})

        topicos = {}
        for t in dados["topicos"]:
            topicos[t["ordem"]], _ = TopicoEmenta.objects.update_or_create(
                disciplina=disciplina, ordem=t["ordem"],
                defaults={"titulo": t["titulo"], "palavras_chave": ", ".join(t.get("palavras_chave", [])),
                          "descricao": t.get("descricao", "")},
            )

        n_itens = 0
        for it in dados["itens"]:
            ItemConhecimento.objects.update_or_create(
                topico=topicos[it["topico"]], titulo=it["titulo"],
                defaults={"disciplina": disciplina, "tipo": it.get("tipo", "MATERIAL"), "conteudo": it["conteudo"]},
            )
            n_itens += 1

        n_ex = 0
        for lista in dados["listas"]:
            obj, _ = ListaExercicios.objects.update_or_create(
                disciplina=disciplina, titulo=lista["titulo"], defaults={"avaliativa": lista["avaliativa"]}
            )
            for i, ex in enumerate(lista["exercicios"], start=1):
                Exercicio.objects.update_or_create(
                    lista=obj, ordem=i,
                    defaults={"topico": topicos.get(ex.get("topico")), "enunciado": ex["enunciado"],
                              "resposta_esperada": ex["resposta_esperada"], "passos": ex.get("passos", ""),
                              "dicas": "\n".join(ex.get("dicas", []))},
                )
                n_ex += 1

        ConfiguracaoPLN.atual()

        if not opts["sem_usuarios"]:
            turma, _ = Turma.objects.get_or_create(disciplina=disciplina, nome="Turma A", periodo="2026-2")
            for email, nome, sobrenome, perfil, matricula in USUARIOS_DEMO:
                u, criado = Usuario.objects.get_or_create(
                    email=email, defaults={"first_name": nome, "last_name": sobrenome, "perfil": perfil,
                                           "matricula": matricula, "is_superuser": perfil == Perfil.ADMINISTRADOR},
                )
                if criado:
                    u.set_password(opts["senha"])
                    u.save()
                if perfil == Perfil.ALUNO:
                    turma.alunos.add(u)
                elif perfil == Perfil.PROFESSOR:
                    turma.professores.add(u)

        self.stdout.write(self.style.SUCCESS(
            f"{disciplina}: {len(topicos)} tópicos, {n_itens} itens, {len(dados['listas'])} listas, {n_ex} exercícios."
        ))
