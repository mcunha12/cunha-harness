# Fase 1 — Requisitos

Roda no começo para todas as features do pedido. Depois dela, a execução não para para perguntar, salvo bloqueio.

1. Entrada. Leia todas as fontes: Jira e Notion pelos conectores, arquivo e imagem pelo Read. Siga link citado dentro de uma fonte até 1 nível.
2. Mapeamento. Enquanto você lê, dispare 1 agente `model: "haiku"`, `effort: "medium"` (`low` em pedido de 1 módulo) para mapear onde o pedido toca o código: módulos, rotas, telas, testes existentes. Saída em `~/.claude/dev/features/_recon/<data>.md`.
3. Impeccable. Em cada repo com UI, confira `PRODUCT.md` e `DESIGN.md` na raiz. Com setup, leia o `PRODUCT.md` antes de escrever a spec: público, modo de cada tela e restrições entram na spec. Sem setup, avise o Marcelo em 1 linha (SKILL.md, regra 13).
4. Divisão em features. 1 feature = 1 branch com o mesmo nome em cada repo que ela toca = 1 MR por repo. Mostre a divisão e as dependências entre features. O Marcelo confirma e escolhe a ordem.
5. Perguntas. Só o que fontes e código não respondem. Rodadas de até 4 perguntas pelo AskUserQuestion, opção recomendada primeiro. Entram também:
   - acesso a dado real para os testes finais (a /test-audit exige registro real anonimizado, só leitura);
   - `run.json` de cada repo com UI que ainda não tem um: comando para subir o app, URL, login de teste (senha por variável de ambiente) e backend usado.
6. Saída por feature:
   - `devstate.py init ~/.claude/dev/features/<slug> <slug> <repos.json>`, com `"impeccable": true | false` em cada repo;
   - `spec.md`: histórias, critérios de aceite, fora do escopo, job to be done de cada tela;
   - `decisions.jsonl`: cada decisão com a origem (fonte, código, resposta).
7. Feature que depende de outra ainda aberta: grave a espera e dispare o loop de `ready` (SKILL.md, seção 3). A Fase 2 roda quando a outra fechar, a partir da branch dela. Ao Marcelo, diga só que a feature está na fila e começa sozinha.
