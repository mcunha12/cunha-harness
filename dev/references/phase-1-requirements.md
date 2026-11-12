# Fase 1 — Requisitos

Roda no começo para todas as features do pedido. Depois dela, a execução não para para perguntar, salvo bloqueio.

1. Entrada. Leia todas as fontes: Jira e Notion pelos conectores, arquivo e imagem pelo Read. Siga link citado dentro de uma fonte até 1 nível.
2. Mapeamento. Enquanto você lê, dispare 1 agente `model: "haiku"`, `effort: "medium"` (`low` em pedido de 1 módulo) para mapear onde o pedido toca o código: módulos, rotas, telas, testes existentes. Saída em `~/.claude/dev/features/_recon/<data>.md`.
3. Impeccable. Em cada repo com UI, confira `PRODUCT.md` e `DESIGN.md` na raiz. Com setup, leia o `PRODUCT.md` antes do brainstorm: público, modo de cada tela e restrições entram na conversa e na spec. Sem setup, avise o Marcelo em 1 linha (SKILL.md, regra 13).
4. Brainstorm. Obrigatório em todo `/dev <pedido>`, com o mapeamento já na mão. Ver a seção "Brainstorm" abaixo.
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

**REQUIRED SUB-SKILL:** carregue `superpowers:brainstorming` e siga a conversa dela: pergunta aberta, uma pergunta por mensagem, playback por partes, palpite marcado como palpite. O orquestrador conduz. Em português, em STE Operacional.

Território que o brainstorm cobre antes da spec, em cada feature:

| Tema | O que sai fechado |
|---|---|
| Regras de negócio | cada regra com quem, quando, limite e exceção; conflito entre fontes resolvido |
| Pontas soltas | estado vazio, erro, permissão, dado faltando ou sujo, legado, migração, concorrência, o que acontece com o que já existe |
| Propostas de UI | 1 proposta por tela tocada, passada pelo Impeccable (abaixo) e aprovada pelo Marcelo |
| Dado e medição | de onde vem cada número, como o Marcelo confere que funcionou |
| Fora do escopo | o que fica de fora e o que seria falha mesmo funcionando |

O que o /dev muda na `superpowers:brainstorming`:

- Roda sempre, mesmo com pedido completo. Pedido completo vira playback das regras e pontas soltas para o Marcelo confirmar. Sem a linha de abertura que oferece pular as perguntas. O brainstorm só pula se o Marcelo pedir; grave isso em `decisions.jsonl`.
- O mapeamento substitui a oferta de recon. Não pergunte se pode olhar o código.
- O documento escrito é a `spec.md` da feature em `~/.claude/dev/features/<slug>/`. Não grave em `docs/superpowers/specs/` e não commite.
- Builder check: dispare o `builder-check-prompt.md` da skill com `model: "opus"`, `effort: "medium"`. As perguntas que só o Marcelo responde voltam numa mensagem só.
- O Marcelo aprova a `spec.md`. Depois da aprovação, o próximo passo é o item 5 desta fase e depois a Fase 2 do /dev. Não invoque `superpowers:writing-plans`.

### Propostas de UI com Impeccable

Toda proposta de UI passa pelo Impeccable antes de chegar ao Marcelo, com ou sem setup no repo:

1. Carregue a skill `impeccable`. Rode `impeccable context --target <rota ou arquivo>` uma vez por tela, com o cwd no repo.
2. Monte a proposta pelo `reference/shape.md`: o brief de 3 a 5 itens (job, modo da tela, estados, hierarquia, o que não muda). As perguntas do `shape` entram no brainstorm, sem rodada própria.
3. Proposta que se entende melhor vendo vai como mockup no visual companion da brainstorming. Leia `reference/craft-floor.md` antes de escrever o mockup, use só tokens e componentes do `DESIGN.md` (sem setup: os do código atual) e rode `impeccable detect <arquivo do mockup>` até zerar os achados.
4. O brief aprovado entra na `spec.md`, na seção da tela.

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
