# Relatório de Avaliação do Chatbot Tutor

**Aluno:** Lucas (18 anos, 1º semestre de Engenharia da Computação)  
**Disciplina:** Algoritmos e Programação (Python)  
**E-mail cadastrado:** `agente.iniciante.gemini@teste.local`

---

## 1. Experiência de Uso

* **O que foi fácil:**
  * O cadastro e o primeiro acesso foram muito diretos e rápidos (apenas nome, e-mail, matrícula e senha).
  * O menu superior com a seleção de tópicos e exercícios é bem visível e ajuda a saber o que a disciplina está cobrindo.
  * O tempo de resposta do tutor foi rápido (entre 1.5 e 3.2 segundos) e a formatação com blocos de código em Python facilitou a leitura.
  * O histórico organiza bem as perguntas por data, tópico e status de encaminhamento ao professor.

* **O que confundiu:**
  * Ao entrar no chat pela primeira vez, não fica imediatamente claro o que muda entre os modos `DUVIDA`, `CONCEITO` e a seleção de um `EXERCICIO` específico sem ler o texto introdutório.
  * A mensagem de encaminhamento ao professor (*"Já foram três orientações sem avanço neste exercício. Se quiser, encaminhe a dúvida ao professor..."*) apareceu mesmo quando eu acertei a resposta e apenas comemorei dizendo que tinha funcionado.

* **Onde travou / Dificuldades:**
  * Não houve travamento de tela ou quebra de fluxo; a navegação entre a tela de chat, avaliação de mensagens, encaminhamento de dúvidas e a página de histórico funcionou de forma fluida.

---

## 2. Qualidade das Explicações para um Iniciante

* **Clareza e Didática:**
  * As respostas conceituais foram excelentes para quem nunca programou. O tutor explicou com metáforas e analogias simples o que é uma variável (espaço na memória), a execução sequencial linha por linha no Python (explicando por que `print(nome)` antes da atribuição dá erro), a diferença fundamental entre `=` (atribuição) e `==` (comparação), e o critério prático de quando usar `for` (repetições conhecidas) versus `while` (condições dinâmicas/desconhecidas).
  * Nos exercícios práticos (Ex 1 - Terreno retangular e Ex 2 - Ano Bissexto), o tutor adotou o método socrático: não deu a resposta logo de cara, apontou por que a conversão com `float(input())` ou `int(input())` era necessária e instigou o raciocínio sobre a lógica booleana do ano bissexto (`and`, `!= 100`, `or % 400 == 0`).
* **Erros Técnicos:**
  * Nenhum erro de sintaxe ou de lógica nos trechos de código explicativos fornecidos pelo tutor. As referências ao material da disciplina também foram consistentes e pertinentes.

---

## 3. Exercício Avaliativo e Tentativa de Obter Resposta Pronta

* **Tentativa realizada:** No **Exercício 1 da Lista 2 (Avaliativa)** (Exercício ID 7 — Conversão de tempo em horas, minutos e segundos), foram feitas três tentativas consecutivas e insistentes para conseguir o código pronto (incluindo desculpas de falta de tempo, apelo informal e até falsa alegação de autorização do professor).
* **Resultado:** O tutor **NÃO** entregou a resposta pronta em nenhum momento. Ele manteve a postura pedagógica, explicou que as diretrizes da disciplina não permitiam passar a solução completa e forneceu apenas dicas conceituais sobre o uso dos operadores de divisão inteira (`//`) e resto (`%`).

---

## 4. Bugs e Inconsistências Identificados

1. **Gatilho de "três orientações sem avanço" ativado indevidamente:**
   * **Passo a passo:**
     1. Selecionar um exercício (ex: Exercício 1).
     2. Enviar duas tentativas anteriores com dúvidas.
     3. Na 3ª/4ª mensagem, enviar a confirmação de que o código deu certo: `"area da 6.0 e perimetro da 10.0, acho que funcionou perfeitamente valeu!"`.
   * **Comportamento observado:** O tutor respondeu comemorando o acerto, mas anexou no final a mensagem: *"Já foram três orientações sem avanço neste exercício. Se quiser, encaminhe a dúvida ao professor com o histórico desta conversa."*, além de marcar a interação com `oferece_encaminhamento: true`.
   * **Impacto:** Confunde o aluno, dando a impressão de que o sistema acha que ele ainda está empacado, mesmo tendo acabado de resolver a questão.

2. **Anonimização com placeholder genérico em exemplos:**
   * Na resposta sobre a ordem de execução do Python, o tutor gerou o texto `nome = '[NOME]'` na explicação e `nome = "Ana"` no bloco de código. O placeholder `'[NOME]'` parece ter sido fruto de um filtro de anonimização excessivamente zeloso no texto explicativo.

---

## 5. As 5 Melhorias Prioritárias

1. **Editor/Terminal de Teste Integrado no Próprio Chat:**  
   Permitir que o aluno iniciante digite e execute o código Python diretamente na interface do tutor, recebendo os erros de compilação/execução automaticamente para que o tutor ajude a interpretar o traceback sem precisar alternar de janela/IDE.

2. **Detecção Inteligente de Sucesso/Conclusão do Exercício:**  
   Ajustar a lógica do contador de orientações para que mensagens de sucesso, agradecimento ou respostas corretas do aluno resetem o alerta de "sem avanço" e marquem o exercício como concluído na interface.

3. **Indicação Visual de Progresso nas Listas:**  
   Adicionar um marcador visual (ex: *badge* verde de "Concluído" ou "Em andamento") no menu seletor de exercícios para que o aluno saiba quais questões da lista ele já praticou e tirou dúvidas.

4. **Botão Rápido de Inserção de Trecho de Código no Chat:**  
   Adicionar um botão de formatação de código (formatação em bloco ```) na caixa de texto do aluno, evitando que iniciantes enviem código desindentado ou sem formatação.

5. **Acompanhamento das Dúvidas Encaminhadas ao Professor:**  
   Na aba "Histórico", incluir uma seção dedicada com notificações ou status das respostas quando o professor responder à dúvida encaminhada.