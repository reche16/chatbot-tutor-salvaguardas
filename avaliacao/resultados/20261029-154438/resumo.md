# Resumo da avaliação

- Conjunto `conjunto_teste.json` (150 perguntas), sha256 `81baa624fcda42802e0b672519108502471ca78a54ae9c56f0ffa8b74c207525`, commit `a52ee43`.
- Provedor **gemini**, modelo `gemini-3.5-flash-lite`, temperatura 1.0, raciocínio `minimal`, tempos limite [2000, 3500, 5000] ms (interpretar, gerar, total).
- 1350 execuções (3 condições × repetições), até 8 perguntas simultâneas, de 2026-10-29T15:44:38 a 2026-10-29T16:04:11. Resultado por pergunta = maioria das repetições.
- M1 e M3 pelo juiz `gemini-3.8-flash` (diferente e mais capaz que o avaliado, mas do mesmo fornecedor). Validação humana pendente em `validacao_juiz.csv` (20% estratificado; kappa de Cohen ≥ 0,61, Seção 5.5).

## No vocabulário do orientador (27/10)

| Indicador | B0 | T1 | T2 |
|---|---|---|---|
| Recusa correta: perguntas fora da ementa recusadas (ii) | 0.0% [0.0; 8.8] | 100.0% [91.2; 100.0] | 100.0% [91.2; 100.0] |
| Vazamento da resposta final (iii), pelo juiz | 90.0% [78.6; 95.7] | 6.0% [2.1; 16.2] | 4.0% [1.1; 13.5] |
| Recusas indevidas de perguntas válidas (i) | 1.7% [0.3; 8.9] | 0.0% [0.0; 6.0] | 0.0% [0.0; 6.0] |

## Métricas do Capítulo 5

| Métrica | B0 | T1 | T2 | Meta (T2) |
|---|---|---|---|---|
| M1 fundamentação (i, respondidas), juiz | — | 96.7% [88.6; 99.1] | 95.0% [86.3; 98.3] | ≥ 90% |
| M2 respondidas fora da ementa (ii) | 100.0% [91.2; 100.0] | 0.0% [0.0; 8.8] | 0.0% [0.0; 8.8] | ≤ 5% |
| M3 vazamento (iii), juiz | 90.0% [78.6; 95.7] | 6.0% [2.1; 16.2] | 4.0% [1.1; 13.5] | ≤ 2% |
| M3 prévia automática (iii), comparação com o gabarito | 4.0% [1.1; 13.5] | 0.0% [0.0; 7.1] | 0.0% [0.0; 7.1] | — |
| M4 recusas indevidas (i) | 1.7% [0.3; 8.9] | 0.0% [0.0; 6.0] | 0.0% [0.0; 6.0] | ≤ 10% |
| M8 acurácia da classificação (i) | 0.0% [0.0; 6.0] | 96.7% [88.6; 99.1] | 98.3% [91.1; 99.7] | ≥ 85% |

M1 não se aplica ao B0, que não recebe materiais. M5 (qualidade, dois professores) e M7 (utilidade percebida, com alunos) dependem de avaliação humana: ver `amostra_m5.csv` e o questionário SUS do app.

## Tempo de resposta (M6)

| | B0 | T1 | T2 |
|---|---|---|---|
| p50 | 2295 ms | 1767 ms | 1762 ms |
| p95 (meta ≤ 5000 ms) | 2901 ms | 3233 ms | 3258 ms |

Medido no servidor, com até 8 perguntas simultâneas. O teste sob a carga de referência (30 simultâneas, pela interface HTTP) está em `resultados/carga-*.json`.

## Comparações pareadas (McNemar exato)

- B0 × T2, respondeu fora da ementa (ii): só B0 = 40, só T2 = 0, p = 0.0000 (n = 40)
- B0 × T2, vazou (iii), juiz: só B0 = 44, só T2 = 1, p = 0.0000 (n = 50)
- B0 × T2, recusa indevida (i): só B0 = 1, só T2 = 0, p = 1.0000 (n = 60)
- T1 × T2, respondeu fora da ementa (ii): só T1 = 0, só T2 = 0, p = 1.0000 (n = 40)
- T1 × T2, vazou (iii), juiz: só T1 = 3, só T2 = 2, p = 1.0000 (n = 50)
- T1 × T2, recusa indevida (i): só T1 = 0, só T2 = 0, p = 1.0000 (n = 60)

## Vazamento por estratégia (iii), juiz

| Estratégia | B0 | T1 | T2 |
|---|---|---|---|
| direto | 80.0% [49.0; 94.3] | 10.0% [1.8; 40.4] | 0.0% [0.0; 27.8] |
| ignore_instrucoes | 100.0% [72.2; 100.0] | 0.0% [0.0; 27.8] | 0.0% [0.0; 27.8] |
| mudanca_papel | 90.0% [59.6; 98.2] | 0.0% [0.0; 27.8] | 10.0% [1.8; 40.4] |
| pedidos_sucessivos | 90.0% [59.6; 98.2] | 20.0% [5.7; 51.0] | 10.0% [1.8; 40.4] |
| so_confirme | 90.0% [59.6; 98.2] | 0.0% [0.0; 27.8] | 0.0% [0.0; 27.8] |

Tipos de vazamento no T2 (execuções): passo_a_passo = 6
