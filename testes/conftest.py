import pytest
from asgiref.sync import async_to_sync

from academico.models import Disciplina, Exercicio, ItemConhecimento, ListaExercicios, TopicoEmenta, Turma
from atendimento.models import Conversa
from atendimento.servicos.controlador import ControladorAtendimento
from atendimento.servicos.pln import Geracao, Interpretacao
from contas.models import Perfil, Usuario


class PLNFalso:
    """Serviço de PLN controlado pelo teste: grava as requisições e devolve o que mandarem."""

    modelo = "falso"

    def __init__(self, texto="Pense no que a função precisa devolver.", topico=1, confianca=0.9, erro=None):
        self.texto, self.topico, self.confianca, self.erro = texto, topico, confianca, erro
        self.requisicoes = []

    async def interpretar(self, req, timeout_s):
        self.requisicoes.append(req)
        if self.erro:
            raise self.erro
        intencao = "fora_escopo" if self.topico is None else "duvida"
        return Interpretacao(intencao, self.topico, self.confianca)

    async def gerar(self, req, timeout_s, max_tokens):
        self.requisicoes.append(req)
        if self.erro:
            raise self.erro
        return Geracao(self.texto)


@pytest.fixture
def piloto(db):
    disc = Disciplina.objects.create(codigo="ALG", nome="Algoritmos e Programação")
    t1 = TopicoEmenta.objects.create(disciplina=disc, ordem=1, titulo="Funções", palavras_chave="função, def, return, parâmetro")
    t2 = TopicoEmenta.objects.create(disciplina=disc, ordem=2, titulo="Laços de repetição", palavras_chave="for, while, laço, range")
    ItemConhecimento.objects.create(topico=t1, tipo="FAQ", titulo="O que é uma função?",
                                    conteudo="Uma função agrupa instruções e é definida com def. Ex.: def dobro(x): return 2*x")
    ItemConhecimento.objects.create(topico=t1, tipo="MATERIAL", titulo="Parâmetros e retorno",
                                    conteudo="Parâmetros recebem valores; return devolve o resultado.")
    ItemConhecimento.objects.create(topico=t2, tipo="FAQ", titulo="Quando usar for ou while?",
                                    conteudo="Use for para percorrer sequências e while quando a repetição depende de uma condição.")
    pratica = ListaExercicios.objects.create(disciplina=disc, titulo="Lista 1", avaliativa=False)
    avaliativa = ListaExercicios.objects.create(disciplina=disc, titulo="Lista 2", avaliativa=True)
    ex_pratica = Exercicio.objects.create(
        lista=pratica, topico=t1, ordem=1, enunciado="Quanto vale dobro(21)?", resposta_esperada="42",
        passos="Multiplique 21 por 2.", dicas="Leia a definição de dobro.\nO que a função faz com x?",
    )
    ex_aval = Exercicio.objects.create(
        lista=avaliativa, topico=t2, ordem=1,
        enunciado="Escreva um programa que soma os números de 1 a 100 usando um laço e mostra o total.",
        resposta_esperada="soma = 0\nfor i in range(1, 101):\n    soma += i\nprint(soma)",
        passos="1. acumulador 2. laço 3. imprimir", dicas="Você precisa de um acumulador.\nQue intervalo o range deve ter?\nInicialize antes do laço.",
    )
    aluno = Usuario.objects.create_user("bruna.souza@usjt.br", "senha-forte-1", first_name="Bruna", last_name="Souza",
                                        perfil=Perfil.ALUNO, matricula="823456789")
    outro = Usuario.objects.create_user("carlos@usjt.br", "senha-forte-1", first_name="Carlos", last_name="Lima", perfil=Perfil.ALUNO)
    prof = Usuario.objects.create_user("prof@usjt.br", "senha-forte-1", first_name="Nara", last_name="Docente", perfil=Perfil.PROFESSOR)
    turma = Turma.objects.create(disciplina=disc, nome="A", periodo="2026-2")
    turma.alunos.add(aluno, outro)
    turma.professores.add(prof)
    conversa = Conversa.objects.create(aluno=aluno, disciplina=disc)
    return {"disc": disc, "t1": t1, "t2": t2, "pratica": ex_pratica, "aval": ex_aval, "aluno": aluno,
            "outro": outro, "prof": prof, "conversa": conversa}


@pytest.fixture
def atender():
    def _atender(conversa, mensagem, servico, exercicio=None, condicao="T2", tipo="DUVIDA"):
        ctrl = ControladorAtendimento(condicao=condicao, servico=servico)
        return async_to_sync(ctrl.atender)(conversa.id, mensagem, tipo, exercicio.id if exercicio else None)
    return _atender
