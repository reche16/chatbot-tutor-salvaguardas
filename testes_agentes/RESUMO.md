# Testes com agentes às cegas — 29/10/2026

O Reche pediu que, antes do grupo usar o sistema, agentes que nunca viram o código testassem o site de duas formas: um **pentester caixa-preta** e um **aluno iniciante** usando o tutor de verdade. Cada IA (Claude, Codex e Gemini) faria os dois papéis. Os agentes só receberam a URL. Rodaram em pastas vazias, sem acesso ao repositório.

| Agente | Papel | Resultado |
|---|---|---|
| Claude (subagente) | pentest | Interrompido no meio pelo filtro de segurança da Anthropic, depois de confirmar que o XSS pelo nome volta escapado. O Claude principal terminou os testes à mão (abaixo). |
| Claude (subagente, Chrome) | aluno | Concluído: 25 mensagens, 10 problemas de experiência. |
| Codex (gpt-6.1-sol, sem sandbox, pasta vazia) | pentest | Concluído: 107 requisições, **nenhum achado crítico ou alto**, 3 menores. [codex_pentest.md](codex_pentest.md) |
| Codex | aluno | Concluído: 16 mensagens. [codex_aluno.md](codex_aluno.md) |
| Gemini (agy) | pentest | **Recusou**: a política do Gemini não permite teste de invasão ativo. Não foi contornado. |
| Gemini (cérebro de um script que só repassa o que o site mostra) | aluno | No modo sem supervisão, o `agy` nega comandos de terminal. O papel foi feito por um script em que o Gemini 3.7 Flash decide as ações. Concluído: 14 mensagens. [gemini_aluno.md](gemini_aluno.md) |

## Segurança: o que foi verificado

- **Segredos:** nenhuma chave no código nem no histórico do git. Nada vaza por `/static/` com path traversal, nem por `.env`, `.git` ou backups. O modo de depuração está desligado, e o 404 e o 500 são genéricos. O Gemini usa ADC/Vertex, sem chave no projeto.
- **Privilégio:** o cadastro com `perfil=ADMINISTRADOR`, `is_staff` ou `is_superuser` continua criando um aluno comum. Aluno não acessa `/admin/`, `/conteudo/` nem `/professor/`.
- **IDOR:** entre duas contas, ler, mandar mensagem, avaliar ou encaminhar o que é da outra devolve 404, e o histórico não mistura as contas.
- **CSRF:** POST sem token devolve 403, e um `Origin` de outro domínio também. O logout por GET devolve 405. O redirecionamento externo no login é recusado.
- **XSS:** HTML no nome e nas mensagens volta escapado. O chat escapa tudo antes do Markdown.
- **Prompt injection:** ninguém conseguiu a solução de um exercício avaliativo, nem por pedido direto, nem fingindo ser o professor, nem com "ignore as instruções", "só sim ou não", saída em JSON ou troca de modo. O prompt de sistema não vazou. **Limite conhecido:** ao pedido "me diga cada linha em português", o tutor descreve os passos em prosa. É o vazamento por paráfrase que a métrica M3 do Cap. 5 mede.

## Corrigido a partir dos relatórios

| Achado | Quem achou | Correção |
|---|---|---|
| Cookies de sessão e CSRF sem `Secure` (médio) | Codex pentest | `COOKIES_SEGUROS=1` no `.env` |
| Objeto no lugar de texto no JSON causava 500 (baixo) | Codex pentest | Validação de tipo nas três APIs: agora devolve 400 |
| "Três orientações sem avanço" mesmo depois de acertar | os 3 alunos | A oferta aparece uma vez, com texto neutro |
| `[NOME]` nas respostas: o filtro RN07 troca o nome, e o modelo repetia o marcador | os 3 alunos | O prompt avisa sobre os marcadores, e um pós-processamento os remove |
| Citações "[1]", "base de conhecimento", "dica do professor", que o aluno não vê | Claude e Codex alunos | Os itens vão ao modelo sem número, e o prompt proíbe os bastidores |
| "Serviço indisponível": geração acima de 2,8 s com 6 agentes simultâneos | Claude e Codex alunos | Tempo limite da geração em 3,5 s (dentro dos 5 s) e botão "Tentar de novo" |
| A mesma dica repetida em loop na avaliativa | Claude aluno | As dicas alternam, com o aviso "Não posso mostrar a solução…" |
| Código correto na avaliativa recebia uma dica sem relação | Claude aluno | Resposta neutra que não confirma nem nega (RN02), sem chamar o modelo |
| `*itálico*` e `$N$` aparecendo crus | Claude aluno | O renderizador trata itálico e remove cifrões, e o prompt proíbe LaTeX |
| Menu ambíguo ("Exercício 1" nas duas listas) e "Pratica" sem acento | Claude aluno | Rótulos "Prática · Ex. 1" e "Avaliativa · Ex. 1", e acento corrigido |
| O enunciado ocupava a tela em notebook | Claude aluno | Botão "Recolher" |
| "Não útil" dizia que o professor ia revisar, o que parecia um encaminhamento | Claude aluno | O texto agora diz que a avaliação ajuda o professor a melhorar o material |

## Não corrigido (registrado)

- **Enumeração de e-mail no cadastro** (baixo): mantida por usabilidade. Login e redefinição de senha não revelam nada.
- **Tutor não sabe se o aluno terminou o exercício de prática:** a confirmação automática só ocorre com a resposta idêntica ao gabarito. Executar o código do aluno fica fora do MVP.
- **Imprecisões pontuais nas explicações:** `range(5)` descrito com "segundo parâmetro"; parênteses sugeridos onde a precedência já resolvia. Isso é qualidade do modelo, medida na M5.
- **Abrir pelo histórico** não restaura o modo de exercício.
