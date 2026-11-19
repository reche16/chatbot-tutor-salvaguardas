# Conceito Visual e Sistema de Design — Chatbot Tutor (USJT)

## 1. Direção Visual
Interface utilitária, enxuta e acadêmica, inspirada em **Linear**, **GitHub Primer** e **Canvas LMS**. Prioriza legibilidade de texto denso e blocos de código, densidade equilibrada de informação e resposta imediata sem adornos visuais. A superfície usa tons neutros frios (ardósia/zinco) com bordas estruturais de `1px` no lugar de sombras pesadas, e azul cobalto sóbrio com contraste AA rigoroso para ações primárias. Todo elemento na tela cumpre função pedagógica ou de navegação; zero estética promocional, zero gradientes decorativos, zero emojis como ícones operacionais.

---

## 2. Tokens (CSS Custom Properties)

```css
:root {
  /* Cores - Modo Claro (Padrão) */
  --bg-page: #f8fafc;
  --bg-surface: #ffffff;
  --bg-subtle: #f1f5f9;
  --bg-code: #f1f5f9;
  
  --border-default: #e2e8f0;
  --border-strong: #cbd5e1;
  
  --text-primary: #0f172a;
  --text-muted: #475569;
  --text-subtle: #64748b;
  
  --primary: #1d4ed8;
  --primary-hover: #1e40af;
  --primary-subtle: #eff6ff;
  --focus-ring: rgba(29, 78, 216, 0.25);
  
  --success: #15803d;
  --success-bg: #f0fdf4;
  --success-border: #bbf7d0;
  
  --warning: #b45309;
  --warning-bg: #fffbeb;
  --warning-border: #fde68a;
  
  --danger: #b91c1c;
  --danger-bg: #fef2f2;
  --danger-border: #fecaca;
  
  /* Bolhas do Chat */
  --bubble-student-bg: #eff6ff;
  --bubble-student-border: #bfdbfe;
  --bubble-student-text: #0f172a;
  --bubble-tutor-bg: #ffffff;
  --bubble-tutor-border: #e2e8f0;
  --bubble-unanswered-bg: #fffbeb;
  --bubble-unanswered-border: #fde68a;

  /* Tipografia (Sistema, zero latência) */
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
  
  --text-xs: 0.75rem;    /* 12px - metadados, selos */
  --text-sm: 0.875rem;   /* 14px - rótulos, tabelas, botões secundários */
  --text-base: 0.9375rem;/* 15px - corpo padrão e chat */
  --text-lg: 1.125rem;   /* 18px - subtítulos (h2) */
  --text-xl: 1.375rem;   /* 22px - títulos de página (h1) */
  --text-2xl: 1.75rem;   /* 28px - valores de KPIs */

  /* Espaçamento */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;

  /* Raios e Sombras */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  --radius-full: 9999px;
  --shadow-xs: 0 1px 2px 0 rgba(15, 23, 42, 0.04);
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg-page: #0b0f19;
    --bg-surface: #111827;
    --bg-subtle: #1e293b;
    --bg-code: #0f172a;
    --border-default: #1e293b;
    --border-strong: #334155;
    --text-primary: #f8fafc;
    --text-muted: #94a3b8;
    --text-subtle: #64748b;
    --primary: #3b82f6;
    --primary-hover: #60a5fa;
    --primary-subtle: #172554;
    --focus-ring: rgba(59, 130, 246, 0.35);
    --success: #4ade80; --success-bg: #052e16; --success-border: #14532d;
    --warning: #fbbf24; --warning-bg: #451a03; --warning-border: #78350f;
    --danger: #f87171;  --danger-bg: #450a0a;  --danger-border: #7f1d1d;
    --bubble-student-bg: #172554;
    --bubble-student-border: #1e3a8a;
    --bubble-student-text: #f8fafc;
    --bubble-tutor-bg: #111827;
    --bubble-tutor-border: #1e293b;
    --bubble-unanswered-bg: #451a03;
    --bubble-unanswered-border: #78350f;
  }
}
```

---

## 3. Especificação de Componentes

- **Barra Superior (`header.topo`):** Altura fixa `52px`, `background: var(--bg-surface)`, `border-bottom: 1px solid var(--border-default)`. Container `.faixa` com `max-width: 1040px`. Esquerda: marca com ícone SVG + nome em `font-weight: 600` + divisor `/` + tag de perfil (`Aluno` ou `Docente`). Centro: links `<nav>` com `padding: 6px 10px`, `border-radius: var(--radius-md)`, link ativo com `background: var(--bg-subtle)` e `color: var(--text-primary)`. Direita: identificação do usuário (`user.first_name|default:user.email` em `--text-sm --text-muted`) + botão fantasma compacto "Sair" (corrige `mvp/templates/base.html:12-29`, que não exibia quem estava logado nem destacava a página ativa).
- **Botões (`.botao`, `button`):** Altura `36px` (`--text-sm`, `font-weight: 500`, `padding: 0 14px`, `border-radius: var(--radius-md)`), `display: inline-flex; align-items: center; gap: 6px`.
  - *Primário:* fundo `--primary`, texto `#fff`, hover `--primary-hover`.
  - *Secundário (`.secundario`):* fundo `--bg-surface`, texto `--text-primary` (corrige `mvp/static/tutor.css:23` onde texto azul sobre borda cinza parecia link solto), borda `1px solid var(--border-strong)`, hover `--bg-subtle`.
  - *Fantasma (`.fantasma`):* fundo transparente, texto `--text-muted`, sem borda, hover `--bg-subtle` e `--text-primary`.
  - *Perigo (`.perigo`):* fundo `--danger-bg`, texto `--danger`, borda `--danger-border`.
  - *Tamanho pequeno (`.sm`):* altura `28px`, `padding: 0 10px`, `--text-xs` (usado nas ações da resposta do chat).
- **Campos de Formulário (`.campo`):** Wrapper vertical (`display: flex; flex-direction: column; gap: 4px; margin-bottom: 14px`). `<label>` em `--text-sm`, `font-weight: 500`, `color: var(--text-primary)`. Inputs/selects/textareas com altura `36px`, `padding: 6px 10px`, `border: 1px solid var(--border-strong)`, `border-radius: var(--radius-md)`, foco com `outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px var(--focus-ring)` (corrige `mvp/static/tutor.css:25`, que não tinha `:focus-visible`). Erro de campo: borda `--danger` no input e `<small class="erro">` com ícone de alerta em `--text-xs --danger`.
- **Cartões (`.cartao`):** `background: var(--bg-surface)`, `border: 1px solid var(--border-default)`, `border-radius: var(--radius-lg)` (`8px` em vez de `10px` em `mvp/static/tutor.css:16`), `padding: 16px`, `box-shadow: var(--shadow-xs)`.
- **Tabelas (`table`):** Envolvidas em `.cartao.tabela-container` com `padding: 0; overflow-x: auto; border-radius: var(--radius-lg)`. Cabeçalho `<th>` com `background: var(--bg-subtle)`, `--text-xs`, `text-transform: uppercase`, `letter-spacing: 0.04em`, `color: var(--text-muted)`, `padding: 10px 14px`. Células `<td>` com `padding: 12px 14px`, `--text-sm`, `font-variant-numeric: tabular-nums` para datas e números. Hover sutil na linha (`tbody tr:hover { background: var(--bg-subtle); }`).
- **Selos de Status (`.selo`):** `display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; border-radius: var(--radius-full); font-size: var(--text-xs); font-weight: 500; border: 1px solid transparent`. Variantes `.ok` (fundo `--success-bg`, texto `--success`, borda `--success-border`), `.alerta` (`--warning-*`) e `.erro` (`--danger-*`).
- **Mensagens Flash (`ul.mensagens`):** Em `mvp/templates/base.html:32`, cada `<li>` recebe borda de `1px` semântica (`--success-border`, `--danger-border`), ícone SVG à esquerda e alinhamento flex.
- **Estado Vazio (`.estado-vazio`):** Substitui os `<p class="suave">` soltos (`mvp/templates/atendimento/inicio.html:10`, `mvp/templates/pedagogico/duvidas.html:22`, `mvp/templates/pedagogico/revisao.html:21`). Caixa com `border: 1px dashed var(--border-strong)`, `border-radius: var(--radius-lg)`, `padding: 32px 16px`, texto centralizado, título curto em `--text-primary` e instrução prática em `--text-muted`.
- **Indicador "Digitando" (`.msg.tutor.digitando`):** Substitui o texto cru em itálico `"Pensando…"` (`mvp/templates/atendimento/chat.html:132`, `mvp/static/tutor.css:57`) por três pontos `.dot` de `5px` com animação discreta de `opacity` (`1.2s infinite`) + rótulo `"Consultando material da disciplina…"`.

---

## 4. Layout por Tela e O Que Muda

1. **Login (`mvp/templates/contas/login.html`):**
   - *O que muda:* Sai o erro inline `style="color:var(--erro)"` (`login.html:6`) para um alerta `.flash-erro` estruturado. Os campos (`login.html:8-11`) ganham wrappers `.campo` em vez de depender de `margin-bottom: 10px` global (`tutor.css:59`). Botão "Entrar" ocupa `width: 100%`. Links de rodapé (`login.html:15`) ficam separados por `border-top: 1px solid var(--border-default)` e `padding-top: 12px`.
2. **Cadastro de Aluno (`mvp/templates/contas/cadastro.html`):**
   - *O que muda:* Largura do cartão sobe para `460px` (`max-width`). Campos organizados em grade de 2 colunas no desktop (`grid-template-columns: 1fr 1fr`) para `Nome` + `Sobrenome` e `Senha` + `Confirmação`, mantendo `E-mail institucional`, `Matrícula (RA)` e `Código da turma` (com fonte monoespaçada e destaque visual) em linha inteira, em vez de empilhar tudo num loop genérico sem hierarquia (`cadastro.html:9-16`).
3. **Início do Aluno (`mvp/templates/atendimento/inicio.html`):**
   - *O que muda:* O alerta de respostas novas (`inicio.html:4`) vira um banner de destaque com borda esquerda `--primary` e link direto. A lista de disciplinas (`inicio.html:6-9`), que hoje empilha `.cartao` com `<br>` e `style="margin-top:8px"`, passa a usar `.grade-disciplinas` (`grid-template-columns: repeat(auto-fill, minmax(280px, 1fr))`), onde cada cartão tem código da disciplina em `.selo` monoespaçado no topo, título forte e rodapé alinhado à direita com botão "Abrir tutor →".
4. **Chat do Aluno (`mvp/templates/atendimento/chat.html`):**
   - *O que muda:*
     - **Cabeçalho da conversa (`.barra`, `chat.html:5-19`):** Fica integrado ao topo do container do chat (fundo `--bg-surface`, borda inferior), agrupando nome da disciplina, `<select id="modo">` estilizado e botão `.secundario.sm` "Nova conversa" com ícone.
     - **Enunciado (`#enunciado`, `chat.html:20`):** Quando visível, fica fixo logo abaixo da `.barra` com fundo `--bg-subtle`, borda esquerda `3px solid var(--primary)` e rótulo em caixa alta `"ENUNCIADO DO EXERCÍCIO"`, sem rolar junto com as mensagens antigas.
     - **Bolhas (`#historico-chat`, `chat.html:21-30`):** Cada mensagem passa a ter cabeçalho sutil (`Você` ou `Tutor IA · Algoritmos` + metadado do exercício em `.selo`) acima do corpo. Blocos `<pre><code>` ganham barra superior fina indicando linguagem/código e contraste nítido.
     - **Ações sob a resposta (`.acoes`, `chat.html:67-99`):** Saem os emojis `👍` e `👎` (`chat.html:75-76`); entram botões `.fantasma.sm` com ícones SVG de polegar e divisor vertical antes de "Encaminhar ao professor" (com ícone de envio).
     - **Rodapé de envio (`#form-chat`, `chat.html:31-34`):** Ancorado na base do container do chat, dentro de uma caixa com foco unificado (`textarea` sem borda própria + botão primário à direita + dica de atalho `Enter para enviar · Shift+Enter para quebrar linha` no canto inferior).
5. **Histórico do Aluno (`mvp/templates/atendimento/historico.html`):**
   - *O que muda:* Filtro (`historico.html:4-12`) alinhado em barra compacta. Dúvidas encaminhadas (`historico.html:16-25`) exibem pergunta do aluno e resposta do professor em blocos visualmente distintos (a resposta do docente ganha fundo `--success-bg` sutil e borda lateral `--success` em vez de um `<p>` simples em `historico.html:23`). Na tabela (`historico.html:29-41`), a coluna de ação "abrir" vira botão `.secundario.sm`.
6. **Painel de Métricas do Professor (`mvp/templates/pedagogico/painel.html`):**
   - *O que muda:* Os links soltos de pendências (`painel.html:11-14`) viram dois cartões de ação rápida no topo com contador em destaque e seta, lado a lado. Os 7 cartões `.indicador` (`painel.html:16-24`) são organizados em grade de 4 colunas com hierarquia: `rotulo` em cima (`--text-xs`, uppercase, `--text-muted`) e `valor` embaixo (`--text-2xl`, `tabular-nums`), invertendo a ordem atual (`painel.html:17`) para leitura imediata de dashboard. Tabelas (`painel.html:27-34`) ganham container com borda e alinhamento numérico à direita nas colunas de contagem.
7. **Dúvidas Encaminhadas (`mvp/templates/pedagogico/duvidas.html`):**
   - *O que muda:* O filtro `Abertas · Respondidas` em texto puro (`duvidas.html:4`) vira controle segmentado (abas tipo *pill* com estado ativo claro). O `<details>` do histórico (`duvidas.html:10-15`) ganha caixa `--bg-subtle` com `padding: 12px` e linha vertical guia. O formulário de resposta (`duvidas.html:17-20`) fica separado por divisória com botão alinhado à direita.
8. **Revisão do Professor (`mvp/templates/pedagogico/revisao.html`):**
   - *O que muda:* O filtro pendentes/todas (`revisao.html:5`) também vira controle segmentado. Metadados técnicos (`modelo_pln`, `versao_prompt` em `revisao.html:8`) vão para tags monoespaçadas discretas no cabeçalho do cartão. A justificativa do aluno (`revisao.html:12`) ganha caixa de destaque `--warning-bg` para saltar aos olhos antes do campo de revisão.

---

## 5. Ícones SVG Inline (Stroke `1.75px`, `16×16`, `currentColor`)

Nenhum pacote externo; todos com `viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"`:
1. **Marca / Capelo ou Terminal (`header.topo .marca`):** `<path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/>` (livro/caderno técnico).
2. **Nova Conversa (`chat.html:18`):** `<path d="M12 5v14M5 12h14"/>` (sinal de mais).
3. **Útil (`chat.html:75`, substitui 👍):** `<path d="M7 10v12"/><path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z"/>`.
4. **Não Útil (`chat.html:76`, substitui 👎):** `<path d="M17 14V2"/><path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22a3.13 3.13 0 0 1-3-3.88Z"/>`.
5. **Encaminhar ao Professor (`chat.html:85-87`):** `<path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>` (avião de papel / envio direto).
6. **Alerta / Sem Resposta (`chat.html:27`, `login.html:6`):** `<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>`.
7. **Exportar CSV (`painel.html:9`):** `<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>`.

---

## 6. Lista de "Não Fazer" (Anti-Padrões)

- **Não usar gradientes roxos/azuis/neon** em botões, cabeçalhos, bordas ou planos de fundo.
- **Não usar emojis como ícones de interface** (`👍`, `👎`, `✨`, `🤖`, `📚`, `🚀`).
- **Não usar glassmorphism** (`backdrop-filter: blur`), sombras difusas grandes (`box-shadow` > `8px`) ou cantos hiper-arredondados (`border-radius` > `12px` em cartões).
- **Não criar avatares caricatos de robô** nem chamar o sistema de "Assistente Mágico / IA Inteligente".
- **Não usar `prompt()` nativo do navegador** quando puder expandir um campo inline simples (como na justificativa de `chat.html:77` e no encaminhamento de `chat.html:93`).
- **Não deixar blocos `<pre><code>` sem `overflow-x: auto`** ou com fonte proporcional.
- **Não usar estilos inline (`style="..."`)** nos templates (`base.html:26`, `login.html:6`, `inicio.html:8`, `revisao.html:17`).
