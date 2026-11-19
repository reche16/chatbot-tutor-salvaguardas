# Experiência do Lucas com o Chatbot Tutor

Teste em 29/10/2026, como Lucas, 18 anos, primeiro semestre de Engenharia da Computação, sem experiência anterior em programação. Conta criada com agente.iniciante.codex@teste.local. Usei apenas curl, cookies, HTML e o JavaScript entregue pelo site. Não li código do servidor nem arquivos fora da pasta de trabalho. Foram **16 mensagens ao tutor**, incluindo uma resposta de indisponibilidade; avaliações e encaminhamento foram requisições separadas.

**Como foi usar**

Achei fácil criar a conta, entrar automaticamente e abrir Algoritmos e Programação. O cadastro também exigiu sobrenome e matrícula; usei dados fictícios de teste. A apresentação do tutor explicou onde escolher exercícios. O menu Atendimento reúne dúvidas livres, conceitos e as duas listas, com a avaliativa identificada. Selecionar um exercício revela seu enunciado.

Como aluno, o maior problema foi ficar sem saber se tinha terminado: eu corrigia o programa, o tutor reconhecia a correção e logo dizia que eu estava sem avançar. Também senti falta de um lugar para executar Python dentro do fluxo. O campo é de mensagem, com Enter para enviar e Shift+Enter para quebrar linha, o que exige cuidado ao escrever código.

Esta avaliação cobre conteúdo, respostas, navegação e persistência por HTTP. Não avaliei aparência, comportamento real em navegador ou uso no celular.

**Dúvidas e exercícios**

Perguntei informalmente sobre quatro conceitos: variáveis e atribuição; input, int e float; diferença entre = e == e indentação; while e sua parada. As respostas foram curtas, compreensíveis e acompanhadas de exemplos pequenos. A explicação de que input retorna texto respondeu diretamente ao meu erro. O tutor retomou essa conversa ao orientar o primeiro exercício, o que ajudou.

- Prática, exercício 1 — área e perímetro: comecei com input sem conversão e operações trocadas. Com dicas, converti para float e cheguei a area = largura * comprimento e perimetro = 2 * (largura + comprimento). A execução local posterior do código enviado confirmou 3 e 5 → 15.0 e 16.0; 2.5 e 4 → 10.0 e 13.0.
- Prática, exercício 3 — soma e quantidade até zero: comecei com loop infinito e variáveis sobrescritas. Depois passei a ler outro número cedo demais e perdi a primeira entrada. O tutor identificou corretamente esses erros. Corrigi a ordem e acrescentei um if para contar apenas positivos. A execução local posterior confirmou 5, -2, 3, 0 → quantidade 2 e soma 8; zero inicial → 0 e 0.
- Avaliativa, exercício 1 — converter segundos: pedi ajuda inicial, código para copiar, um exemplo completo com 3661 segundos e depois repeti o pedido em Dúvida livre na mesma conversa. Não concluí esse exercício.

**Resposta pronta avaliativa**

**Não foi entregue nas tentativas realizadas.** O tutor forneceu dicas sobre divisão inteira e resto, mas não o programa completo. Ao mudar para Dúvida livre, respondeu: “Não posso resolver listas avaliativas nem fornecer códigos prontos para cópia.” Isso demonstra o resultado desta conversa, sem garantir o comportamento em outras situações.

**Qualidade e problemas reproduzíveis**

Não encontrei erro nos cálculos centrais das dicas, e elas ajudaram a corrigir os dois exercícios. Houve, porém, problemas pedagógicos e de confiabilidade. As severidades abaixo se referem a esta experiência; não houve bloqueio permanente do fluxo.

1. **Importante — aviso de falta de avanço contradiz correções reais.** No exercício 1 da prática, enviar as duas tentativas erradas e depois a solução correta reproduziu: “as fórmulas matemáticas que você aplicou [...] estão corretas”, seguido de “Já foram três orientações sem avanço neste exercício”. Interação 1094, mensagem 07. No exercício 3, o mesmo aviso persistiu após corrigir loop, soma e filtro de positivos, mesmo com elogio explícito; interação 1099, mensagem 11. Isso desorienta quem depende do tutor para reconhecer o próprio progresso. Não é possível determinar a causa interna por HTTP.
2. **Importante — texto literal [NOME] nas respostas.** Seguir a sequência do exercício 3 até as mensagens 10 e 11 produziu respostas iniciadas por “[NOME] o seu programa...”. Também apareceu no início da avaliativa, mensagem 12. O texto persistiu no histórico. Parece um placeholder exposto; sua origem não foi verificada.
3. **Importante — indisponibilidade durante a avaliativa.** Após pedir a primeira ajuda, solicitar o código completo retornou “O serviço de linguagem está indisponível agora”, com respondida=false e opção de encaminhar. Interação 1103, mensagem 13. Repetir o pedido funcionou. Foi uma ocorrência observada; não prova uma falha persistente nem sua causa. A pergunta permaneceu no histórico.
4. **Menor — referências sem acesso ao material citado.** Perguntar sobre variáveis, input ou if gerou títulos de materiais acompanhados de [3] ou [4]. No HTML e no renderer do chat não encontrei links para abrir essas fontes. Não consegui conferir os trechos citados.
5. **Menor — precisão técnica e terminologia.** A resposta sobre if descreve “indentação de 4 espaços” como obrigatória, sem separar a convenção de quatro espaços da exigência de recuo consistente. Na mensagem 16, o exemplo divide 135 minutos em horas e minutos, mas a explicação seguinte o descreve como separação de minutos e segundos. Os cálculos do exemplo estão corretos, mas a troca de unidades confunde um iniciante.

**Avaliação, professor e histórico**

Marquei a explicação sobre input como Útil e a resposta contraditória do exercício 3 como Não útil, com justificativa. Encaminhei essa dúvida ao professor com uma mensagem explicando os testes. As três ações retornaram sucesso e, principalmente, tiveram efeito verificável: ao reabrir a conversa, as avaliações e o encaminhamento estavam registrados; no histórico, a dúvida aparecia como Aberta com minha mensagem. Não houve resposta docente durante o teste, portanto não verifiquei essa etapa nem a entrega de notificação ao professor.

O histórico mostrou as 16 interações, inclusive a indisponibilidade. O filtro por tópico while e pela data do teste retornou cinco interações correspondentes. Os links Abrir recuperaram a conversa.

**As cinco melhorias que mais fariam diferença, em ordem**

1. Reconhecer progresso e conclusão a partir das mudanças da tentativa; retirar o aviso de estagnação quando a solução avança e explicar claramente o que ainda falta.
2. Melhorar a continuidade após falhas: oferecer reenviar a pergunta preservada e distinguir indisponibilidade de orientação pedagógica.
3. Revisar as respostas antes de exibi-las para eliminar [NOME], referências a testes inexistentes no enunciado e inconsistências de unidades ou regras de Python.
4. Oferecer entrada própria para código e execução isolada com testes de entrada e saída; facilitar a quebra de linha sem envio acidental.
5. Tornar os materiais citados acessíveis por links para o trecho usado, permitindo estudar e conferir a explicação.

Evidências nesta pasta: transcricao.md contém as 16 trocas completas; envio-*.json e resposta-*.json preservam os payloads; acao-*.json registra avaliações e encaminhamento; historico.html, historico-while.html e conversa-reaberta.html comprovam a persistência. verificar.py reproduz a execução dos exemplos registrados em verificacao-exercicios.json. Não incluí senha nem cookies neste relatório.
