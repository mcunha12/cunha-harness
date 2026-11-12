# Fase 1 — Requisitos

Roda no começo para todas as features do pedido. Depois dela, a execução não para para perguntar, salvo bloqueio.

1. Entrada. Leia todas as fontes: Jira e Notion pelos conectores, arquivo e imagem pelo Read. Siga link citado dentro de uma fonte até 1 nível.
2. Mapeamento. Enquanto você lê, dispare 1 agente `model: "haiku"`, `effort: "medium"` (`low` em pedido de 1 módulo) para mapear onde o pedido toca o código: módulos, rotas, telas, testes existentes. Saída em `~/.claude/dev/features/_recon/<data>.md`.
3. Impeccable. Em cada repo com UI, confira `PRODUCT.md` e `DESIGN.md` na raiz. Com setup, leia o `PRODUCT.md` antes do brainstorm: público, modo de cada tela e restrições entram na conversa e na spec. Sem setup, avise o Marcelo em 1 linha (SKILL.md, regra 13).
4. Brainstorm. Obrigatório em todo `/dev <pedido>`, com o mapeamento já na mão. Ver `references/brainstorm.md`.
5. Divisão em features. 1 feature = 1 branch com o mesmo nome em cada repo que ela toca = 1 MR por repo. Mostre a divisão e as dependências entre features. O Marcelo confirma e escolhe a ordem.
6. Perguntas operacionais. No fim do brainstorm, 1 rodada pelo AskUserQuestion, opção recomendada primeiro, só com o que ainda falta:
   - acesso a dado real para os testes finais (a /test-audit exige registro real anonimizado, só leitura);
   - `run.json` de cada repo com UI que ainda não tem um: comando para subir o app, URL, login de teste (senha por variável de ambiente) e backend usado.
7. Saída por feature:
   - `devstate.py init ~/.claude/dev/features/<slug> <slug> <repos.json>`, com `"impeccable": true | false` em cada repo;
   - `spec.md`: o documento do brainstorm, no formato da seção "Spec" abaixo;
   - `decisions.jsonl`: cada decisão com a origem (fonte, código, resposta, brainstorm).
8. Feature que depende de outra ainda aberta: grave a espera e dispare o loop de `ready` (SKILL.md, seção 3). A Fase 2 roda quando a outra fechar, a partir da branch dela. Ao Marcelo, diga só que a feature está na fila e começa sozinha.

## Brainstorm

Procedimento completo em `references/brainstorm.md`: conversa, investigação, companion visual com opções no localhost, Impeccable, spike, builder check e gate.

## Spec

`spec.md` de cada feature, nesta ordem:

1. Objetivo e o porquê.
2. Histórias e critérios de aceite.
3. Regras de negócio, numeradas.
4. Pontas soltas e a decisão de cada uma.
5. Telas: job to be done, modo e o brief do Impeccable aprovado.
6. Dado e medição.
7. Fora do escopo.
8. Decisões do orquestrador, para o Marcelo conferir.
