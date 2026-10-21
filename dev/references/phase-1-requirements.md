# Fase 1 — Requisitos

Roda no começo para todas as features do pedido. Depois dela, a execução não para para perguntar, salvo bloqueio.

1. Entrada. Leia todas as fontes: Jira e Notion pelos conectores, arquivo e imagem pelo Read. Link citado dentro de uma fonte é seguido até 1 nível.
2. Recon em paralelo. Enquanto você lê, dispare um swarm Haiku (`effort: "medium"`, até 3 agentes) para mapear onde o pedido toca o código: módulos, rotas, telas, testes existentes. Saída em `~/.claude/dev/features/_recon/<data>.md`.
3. Divisão em features. 1 feature = 1 branch com o mesmo nome em cada repo que ela toca = 1 MR por repo. Mostre a divisão e as dependências entre features (B usa o endpoint que A cria). O Marcelo confirma e escolhe a ordem.
4. Perguntas. Só o que fontes e código não respondem. Rodadas de até 4 perguntas pelo AskUserQuestion, opção recomendada primeiro. Entram também:
   - acesso a dado real para os testes (a /test-audit exige registro real anonimizado, só leitura);
   - `run.json` de cada repo com UI que ainda não tem um: comando para subir o app, URL, login de teste (senha por variável de ambiente) e backend usado.
5. Saída por feature:
   - `devstate.py init ~/.claude/dev/features/<slug> <slug> <repos.json>`;
   - `spec.md`: histórias, critérios de aceite, fora do escopo, job to be done de cada tela;
   - `decisions.jsonl`: cada decisão com a origem (fonte, código, resposta).

A spec serve também de spec do Mode A da /test-audit.
