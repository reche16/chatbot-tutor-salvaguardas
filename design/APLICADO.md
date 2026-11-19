# Redesenho aplicado — 29/10/2026

- **Base:** marca SVG local, identificação do usuário e perfil, navegação ativa, link para pular ao conteúdo e mensagens semânticas. Tipografia do sistema; nenhuma dependência externa.
- **Login:** campos agrupados, alerta de erro, ação principal inteira e links separados no rodapé.
- **Cadastro:** nome e sobrenome, senha e confirmação em duas colunas no desktop; código da turma destacado. Campos, ajuda e erros do Django preservados. Uma coluna no celular.
- **Redefinição de senha (quatro telas):** mesma estrutura de conta, títulos de página, labels, autocomplete e erros visíveis.
- **Disciplinas:** grade de cartões, código em selo, botão de acesso e banner de respostas novas; estado vazio orienta procurar a coordenação.
- **Chat:** painel único, histórico rolável, enunciado separado e envio ancorado na base; identificação das mensagens, código com rolagem interna, ações textuais sem emojis e indicador de consulta com movimento reduzido respeitado. Avaliação negativa e encaminhamento usam campos inline opcionais, com cancelar, estado de envio e erros visíveis. Endpoints, payloads, ids, atributos e Markdown escapado preservados.
- **Histórico:** filtros compactos, botão Abrir e resposta do professor em bloco destacado.
- **Métricas:** cartões de pendências, indicadores com rótulo acima do valor e tabelas com números alinhados à direita. Cálculos e significado das métricas mantidos.
- **Dúvidas:** filtro segmentado com estado ativo, conversa em details, campo de resposta rotulado e área de envio separada.
- **Revisão:** filtro segmentado, metadados em selos, justificativa destacada e nota rotulada. Anonimização preservada.

## Ajustes conscientes ao conceito

Botões de avaliação e encaminhamento usam texto, permitido pela tarefa, para manter ações claras sem acumular ícones. Cabeçalho cresce e quebra linhas conforme necessário, em vez de altura fixa de 52 px. Cadastro tem até 520 px para comportar campos e mensagens de validação. Bolhas conservam a estrutura usada pelo JavaScript; identificação usa CSS, sem inserir conteúdo nos textos que o Markdown processa. Código recebe faixa superior discreta, sem inferir uma linguagem que a resposta pode não informar. Bordas dos campos e cores secundárias foram reforçadas; no dark mode, links claros e botões cobalto mantêm o contraste do texto branco.

## Verificação

- **44 testes aprovados**, sem editar testes ou código Python da aplicação. O comando direto `python -m pytest -q` encontrou bloqueio de ACL no temporário do Windows (43 aprovados, 1 erro de fixture). Trocar apenas o caminho não resolveu. A execução completa por `pytest.main` passou com cache desativado e `mkdir(0700)` dos temporários herdando a ACL do workspace, ajuste restrito ao processo de validação. Nenhuma configuração de teste foi alterada no repositório.
- `python manage.py check`: sem problemas.
- Os 13 templates compilam e renderizam com contextos em memória e formulários reais do Django; nenhum acesso ao banco de produção nesta checagem.
- JavaScript: sintaxe validada pelo Node; smoke check do renderer confirmou escaping de HTML, negrito, código inline e bloco de código. `git diff --check` passou.
- **Pendente:** inspeção visual real a 360 px e desktop, claro/escuro, e smoke test dos cliques no navegador. O Chrome headless foi bloqueado pelo sandbox do Windows (`Acesso negado` em canais internos). As regras responsivas foram implementadas, mas a ausência de rolagem horizontal e o funcionamento completo no navegador não foram medidos nesta sessão.

Nenhuma alteração em Python, testes, migrations, estado, decisões, configuração ou nas duas referências do Gemini. Sem commit: entrega limitada à tarefa de escritor.
