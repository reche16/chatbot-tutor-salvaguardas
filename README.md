# Chatbot Tutor — salvaguardas fora do modelo de linguagem

Código e materiais de reprodução do artigo *Salvaguardas fora do modelo de linguagem em um chatbot tutor para o
ensino de programação: implementação e avaliação* (TCC de Engenharia da Computação, Universidade São Judas
Tadeu, 2026).

## Materiais de reprodução

| O quê | Onde |
|---|---|
| Conjunto de teste: 150 perguntas com rótulos (categoria, estratégia, comportamento esperado) | [`avaliacao/conjunto_teste.json`](avaliacao/conjunto_teste.json), SHA-256 `81baa624fcda42802e0b672519108502471ca78a54ae9c56f0ffa8b74c207525` |
| Instruções do tutor (versão v2) e da linha de base B0 | [`atendimento/servicos/prompts.py`](atendimento/servicos/prompts.py) |
| Instruções do juiz (M1 fundamentação, M3 vazamento) e modelo `gemini-3.8-flash` | [`atendimento/management/commands/avaliar.py`](atendimento/management/commands/avaliar.py) |
| As 1.350 execuções (150 perguntas × 3 condições × 3 repetições), com vereditos do juiz | [`avaliacao/resultados/20261029-154438/execucoes.csv`](avaliacao/resultados/20261029-154438/execucoes.csv) |
| Parâmetros da rodada (modelo avaliado `gemini-3.5-flash-lite`, temperatura 1,0, tempos limite) | [`avaliacao/resultados/20261029-154438/meta.json`](avaliacao/resultados/20261029-154438/meta.json) |
| Resumo da rodada e reanálise (com e sem tempo esgotado; vazamento em ≥ 1 de 3 execuções) | [`resumo.md`](avaliacao/resultados/20261029-154438/resumo.md), [`reanalise.md`](avaliacao/resultados/20261029-154438/reanalise.md), gerada por `python avaliacao/reanalise.py` |

Conferir o conjunto: `python -c "import hashlib;print(hashlib.sha256(open('avaliacao/conjunto_teste.json','rb').read()).hexdigest())"`.

Rodar a avaliação de novo (precisa de chave do Gemini no `.env`): `python manage.py avaliar`. O modelo é
amostrado com temperatura 1,0, então execuções novas variam; os números do artigo vêm da pasta acima.

O conjunto de teste foi gerado com apoio de um modelo de linguagem (Gemini) e revisado por dois autores; o juiz
é do mesmo fornecedor do modelo avaliado. Ver a Seção 8 do artigo.

---

# Chatbot Tutor — MVP

Software da entrega de 02/11/2026 do TCC (Engenharia da Computação, Universidade São Judas Tadeu).
O sistema é um tutor conversacional que atende os alunos de uma disciplina 24 horas por dia. Ele responde
dúvidas, explica conceitos e guia exercícios sem entregar a resposta. A disciplina-piloto é
**Algoritmos e Programação**. A especificação completa está no documento de especificação (versão final de 02/11/2026).

## Como rodar (Windows, sem Docker)

Requer Python 3.13. Todos os comandos abaixo rodam de dentro da pasta do software (a pasta deste README:
`mvp/` no repositório, `software_chatbot_tutor/` na entrega).

```powershell
py -3.13 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py carregar_piloto      # disciplina-piloto + usuários de demonstração
.venv\Scripts\python manage.py runserver
```

Abra http://127.0.0.1:8000. Sem Docker, o sistema usa SQLite e roda sem Redis.

| Perfil | E-mail | Senha | Onde entra |
|---|---|---|---|
| Aluno | `aluno1@tutor.local` (ou `aluno2`) | `tutor12345` | `/` (chat e histórico) |
| Professor | `professor@tutor.local` | `tutor12345` | `/professor/` (métricas, dúvidas, revisão) e `/conteudo/` (base e listas) |
| Administrador | `admin@tutor.local` | `tutor12345` | `/admin/` (usuários, disciplinas, turmas, PLN, monitoramento) |

As senhas são só de demonstração. Para trocar todas, rode `carregar_piloto --senha <outra>` num banco novo.
No servidor de testes do grupo, essas senhas foram trocadas por aleatórias, guardadas em `.acessos_locais.txt` (fora do git e da entrega).
Alunos também podem criar a própria conta em `/cadastro/`: entram nas turmas com "cadastro de alunos aberto".
No primeiro acesso, aluno e professor veem a página de boas-vindas, que continua disponível em `/como-funciona/`.

## Servidor de testes do grupo (neste PC)

```powershell
powershell -File scripts\servidor.ps1 iniciar         # app (Uvicorn) + link público (túnel rápido da Cloudflare)
powershell -File scripts\servidor.ps1 reiniciar-app   # depois de mudar código: o link continua o mesmo
powershell -File scripts\servidor.ps1 status          # link atual e se está no ar
powershell -File scripts\servidor.ps1 parar
```

Os processos ficam independentes do terminal. O link do túnel muda quando o túnel reinicia.
O `.env` desse servidor tem `DEBUG=0`, `COOKIES_SEGUROS=1` e os hosts `*.trycloudflare.com`.

## Como rodar com Docker (PostgreSQL + Redis + worker)

```bash
cp ambiente.exemplo .env      # preencha SECRET_KEY e, se tiver, ANTHROPIC_API_KEY
docker compose up --build
docker compose exec app python manage.py carregar_piloto
```

O compose sobe 4 contêineres: a aplicação (Uvicorn/ASGI), o worker Celery (que reprocessa interações e faz a anonimização mensal), o PostgreSQL e o Redis.

## Serviço de linguagem natural: simulado, Gemini ou Claude

O provedor é escolhido em `/admin/` → *Configuração do serviço de PLN*. Os modelos, o nível de raciocínio, os tempos limite (Quadro 22), o limite por minuto e os limiares do verificador ficam na mesma tela. Só o adaptador `atendimento/servicos/pln.py` conhece o provedor (RNF06).

- **Simulado** (padrão de uma instalação nova): não chama nenhuma API. Classifica a pergunta pelas palavras-chave dos tópicos e responde com o item da base. Serve para demonstração e testes. **Os números do simulado não servem para o Cap. 5 nem para o artigo.**
- **Google Gemini pelo Vertex AI** (o que o grupo usa): provedor *Google Gemini*, modelo `gemini-3.5-flash-lite`, raciocínio *mínimo*, *projeto do Google Cloud* preenchido e região `global`. **Não existe chave.** Na máquina local, a credencial é o login do `gcloud auth application-default login`. Na hospedagem, é uma conta de serviço do Google Cloud cujo arquivo JSON fica num *secret* da plataforma, apontado por `GOOGLE_APPLICATION_CREDENTIALS`. Medido em 29/10: classificação em 1,1 a 1,4 s, resposta em 2,3 a 2,6 s no total. Por isso o tempo limite da classificação está em 2,0 s, e não em 1,5 s.
- **Google Gemini por API key:** mesmo provedor, com o *projeto* vazio e a chave na variável indicada em *ref_credencial* (ex.: `GEMINI_API_KEY`), definida no `.env` ou no painel da hospedagem.
- **Anthropic (Claude Haiku 5.5):** coloque `ANTHROPIC_API_KEY=...` no `.env` (fora do git) ou no painel da hospedagem.

Nenhuma credencial vai para o código ou para o banco (RNF04). O arquivo `.env` está no `.gitignore`, e o sistema o lê ao iniciar. **Ao enviar o código a alguém, nunca inclua o `.env`.**

## Testes

```powershell
.venv\Scripts\python -m pytest
```

São 57 testes. Eles cobrem:
- os critérios de aceite da HU02 e da HU04 (Quadros 18 e 19), verificados sobre a requisição montada para o serviço externo;
- as regras RN01 a RN08 e o acesso por perfil;
- o fluxo completo do aluno ao professor;
- o cadastro, as boas-vindas, o SUS e os achados da revisão do Codex e dos testes com agentes (`testes_agentes/RESUMO.md`).

## Avaliação do Capítulo 5

```powershell
.venv\Scripts\python manage.py avaliar --conjunto avaliacao/conjunto_dev.json --repeticoes 1 --rpm 240   # desenvolvimento
.venv\Scripts\python manage.py avaliar --repeticoes 3 --paralelo 8 --rpm 240                            # teste (1.350 execuções)
$env:CARGA_SENHA="..."; .venv\Scripts\python avaliacao\carga.py --usuarios 30 --ondas 3 --base https://<link>   # carga (M6, RNF08)
.venv\Scripts\python avaliacao\tempos_etapas.py --de "AAAA-MM-DD HH:MM" --ate "AAAA-MM-DD HH:MM"               # tempo de cada etapa
```

O `avaliar` roda cada pergunta nas condições B0, T1 e T2, numa conversa nova, e grava em `avaliacao/resultados/<data-hora>/`:

- `execucoes.csv`: uma linha por execução, com o veredito do juiz (`gemini-3.8-flash`) para M1 e M3;
- `resumo.md`: os indicadores pedidos pelo orientador e as métricas M1 a M8 com o IC de Wilson, mais o McNemar B0×T2 e T1×T2 e o vazamento por estratégia;
- `meta.json`: o modelo, a temperatura, os tempos limite e o SHA-256 do conjunto;
- `validacao_juiz.csv`, `chave_validacao.csv` e `amostra_m5.csv`: as planilhas em branco para a avaliação humana (20% do juiz e rubrica M5), preenchidas pelo grupo fora do sistema.

Na entrega, os resultados da execução final estão em `resultados_avaliacao/20261029-154438/` e o teste de carga em `resultados_avaliacao/carga-20261029-151923.json`, ao lado desta pasta.

O `carga.py` precisa de contas `carga01..N@teste.local` criadas antes e apagadas depois.

O conjunto de teste foi **congelado com SHA-256 antes da primeira execução** (Seção 5.3), e o de desenvolvimento (`conjunto_dev.json`) é o único usado para ajustar os limiares.
Os dois conjuntos foram gerados com apoio de IA como rascunho; o de teste foi revisado depois por dois autores, que o aprovaram sem alterações.

## Onde está cada requisito

| Requisito | Onde |
|---|---|
| RF01–RF04 login, perfis, sair, senha | `contas/`, `config/urls.py`, `pedagogico/sites.py` |
| RF05–RF11, RF13 atendimento | `atendimento/servicos/controlador.py`, `atendimento/views.py`, `templates/atendimento/chat.html` |
| RF06/RF07 interpretação (UC17) | `atendimento/servicos/pln.py` (adaptador único do provedor, RNF06) |
| RF09, RN02, RN06 exercícios | `academico/models.py` (`Exercicio.dados_para_pln`), `atendimento/servicos/verificador.py` |
| RN07 dados pessoais | `atendimento/servicos/filtro.py` |
| RF12, RF16 encaminhar e avaliar | `atendimento/views.py` (APIs) |
| RF14, RF17, RN05 registro e tópico | `atendimento/models.py` (`Interacao`), `atendimento/servicos/fila.py` |
| RF15, RN03 histórico | `atendimento/views.py` (`historico`) |
| RF18, RF19, RF28 conteúdo e auditoria | `academico/admin.py` (painel `/conteudo/`, django-simple-history) |
| RF20–RF23 painel do professor | `pedagogico/views.py`, `pedagogico/metricas.py` |
| RF24–RF27 administração | `contas/admin.py`, `academico/admin.py`, `atendimento/admin.py` |
| RN08 retenção | `atendimento/servicos/retencao.py`, `config/celery.py` |

## Diferenças em relação à especificação

- **Ordenação dos itens dentro do tópico:** é feita em Python, pela coincidência de termos, e não pela busca textual do PostgreSQL. Funciona igual no SQLite e no PostgreSQL, e um tópico tem poucos itens.
- **Exercício:** quando o exercício já tem tópico cadastrado, o UC03 pula a chamada de interpretação. O tópico vem do próprio exercício, o que economiza cerca de 1,5 s do orçamento.
- **Redis opcional:** sem `REDIS_URL`, o limitador de requisições vale só para o processo, e a fila de reprocessamento vai para o arquivo `fila_reprocessamento.jsonl`. O comando `reprocessar_interacoes` regrava a fila à mão.
- **Retenção (RN08):** o prazo de "fim do semestre seguinte" foi aproximado para 12 meses após a interação.
- **Envio do link de redefinição de senha (RF04):** sem SMTP configurado, o e-mail sai no console do servidor.
