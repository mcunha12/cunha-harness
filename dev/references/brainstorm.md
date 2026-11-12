# Brainstorm (Fase 1)

Cópia adaptada da `superpowers:brainstorming` 7.0.0 (MIT, `scripts/companion/LICENSE`). O /dev usa esta página. Não carregue a skill da superpowers.

O orquestrador conduz, na conversa, em português e em STE Operacional. O objetivo é descobrir o que o Marcelo quer e por quê antes de construir.

## 1. Regras da conversa

1. Roda em todo `/dev <pedido>`, mesmo com pedido completo. Pedido completo vira playback para o Marcelo confirmar. Pula só se o Marcelo pedir; grave isso em `decisions.jsonl`.
2. Sem a mensagem que oferece pular as perguntas.
3. Cada mensagem termina com 1 pergunta, numa frase, sem lista de exemplos de resposta.
4. Pergunta aberta primeiro, ancorada num caso real: "Me conta a última vez que...", "Se só desse para fazer uma dessas bem, qual?". Menu de opções só quando o Marcelo travar ou pedir palpite.
5. Palpite que ele corrige vale mais que pergunta: "Meu palpite: X te incomoda por causa de Y?". Todo palpite vai marcado como palpite.
6. Pense largo em privado: gere várias ideias e descarte as fracas antes de propor. Mostre a comparação só quando ajuda a decidir.
7. Decisão de como fazer (biblioteca, padrão, arquitetura): siga o que o repo já usa e diga em 1 linha. Na spec, entra como decisão do orquestrador.

## 2. Investigação

O mapeamento da Fase 1 (agente Haiku) substitui a oferta de recon. Não pergunte se pode olhar o código.

Pedido que é bug ou comportamento errado: antes de propor solução, feche a causa raiz pela fase 1 da `superpowers:systematic-debugging`:

1. Reproduza o problema, com o passo a passo.
2. Colete evidência: log, dado, `file:line` (agente Haiku; o orquestrador lê só o resumo).
3. Compare com o caminho que funciona.
4. Escreva a causa raiz como hipótese ou como fato medido, dizendo qual é.

A causa raiz entra no playback e na spec, seção "Pontas soltas".

## 3. Território

Território, não roteiro. Nunca leia os itens como perguntas.

| Tema | O que sai fechado |
|---|---|
| Objetivo | o que é, por que agora, como o Marcelo sabe que deu certo |
| Regras de negócio | cada regra com quem, quando, limite e exceção; conflito entre fontes resolvido |
| Pontas soltas | estado vazio, erro, permissão, dado faltando ou sujo, legado, migração, concorrência, o que acontece com o que já existe |
| Propostas de UI | 2 a 4 opções por tela tocada, passadas pelo Impeccable, uma escolhida pelo Marcelo no navegador |
| Referências | o que ele viu em outro lugar e gostou ou odiou |
| Dado e medição | de onde vem cada número, como o Marcelo confere |
| Fora do escopo | o que fica de fora e o que seria falha mesmo funcionando |

## 4. Playback

Assim que uma parte estiver clara, descreva de volta em 200 a 300 palavras e volte às perguntas da parte seguinte. Playback e perguntas alternam a conversa inteira. Só o que o Marcelo disse entra como dele. Termine cada playback perguntando o que está errado ou faltando. Playback de tela vai com o mockup ao lado.

## 5. Companion visual (protótipos no localhost)

Abra direto, sem perguntar, na primeira vez que ver ajuda mais que ler: tela, layout, fluxo, opções que ficam diferentes entre si, diagrama. Requisito, escopo e trade-off ficam no texto.

Iniciar, uma vez por feature, com `run_in_background: true`:

```bash
bash ~/.claude/skills/dev/scripts/companion/start-server.sh --project-dir ~/.claude/dev/features/<slug> --open
```

1. A saída traz `url`, `screen_dir` e `state_dir`. Grave os três em `decisions.jsonl`. Passe ao Marcelo a `url` completa, com o `?key=`.
2. Os arquivos ficam em `~/.claude/dev/features/<slug>/.superpowers/brainstorm/`, fora do repo.
3. Antes de cada tela, confira que `<state_dir>/server-info` existe e `<state_dir>/server-stopped` não. Se caiu, rode o mesmo comando: a porta e a aba aberta se mantêm.

Loop por tela:

1. Escreva um arquivo novo em `screen_dir` com a ferramenta Write, nome semântico (`checkout.html`, `checkout-v2.html`). Nunca reuse nome.
2. Escreva fragmento, sem `<html>`: o servidor aplica o template. Opções com `<div class="options">` e `<div class="option" data-choice="a" onclick="toggleSelect(this)">`. Mockup grande com `<div class="cards">` e `class="card"`. Lado a lado com `class="split"`. Classes completas em `scripts/companion/frame-template.html`.
3. Cada tela traz a pergunta no topo e 2 a 4 opções.
4. No chat: a `url`, 1 linha do que está na tela e o pedido para clicar na opção e responder no terminal. Termine o turno.
5. No turno seguinte, leia `<state_dir>/events` (JSONL de cliques; o último `choice` é a escolha) e junte com o texto do Marcelo. Nunca faça poll desse arquivo.
6. Feedback que muda a tela gera nova versão. Avance só com a tela validada.
7. Ao voltar para o texto, grave `waiting.html` com `<p class="subtitle">Continuando no terminal...</p>`.
8. No fim da Fase 1: `bash ~/.claude/skills/dev/scripts/companion/stop-server.sh <session_dir>`.

### Propostas de UI com Impeccable

Toda opção de UI passa pelo Impeccable antes de ir ao navegador, com ou sem setup no repo:

1. Carregue a skill `impeccable`. Rode `impeccable context --target <rota ou arquivo>` uma vez por tela, com o cwd no repo.
2. Monte o brief pelo `reference/shape.md`: 3 a 5 itens (job, modo da tela, estados, hierarquia, o que não muda). As perguntas do `shape` entram no brainstorm, sem rodada própria.
3. Leia `reference/craft-floor.md` antes do mockup. Use só tokens e componentes do `DESIGN.md` (sem setup: os do código atual). Conteúdo real do domínio, sem lorem ipsum.
4. Rode `impeccable detect <arquivo do mockup>` até zerar os achados.
5. A opção escolhida e o brief dela entram na `spec.md`, na seção da tela.

## 6. Spike

Protótipo descartável que roda é o jeito mais barato de saber se algo funciona. Ofereça quando ajudar. Spike sai sem teste, sem plano e sem review, em worktree própria, e fica rotulado como descartável. Aproveitar o código do spike é pedido novo e volta para a spec. O que o spike ensinou volta para a conversa.

## 7. Tamanho

Com o pedido entendido, diga o tamanho em 1 linha. O Marcelo pode mudar.

| Tamanho | Descrição | Depois |
|---|---|---|
| Tarefa rápida e clara | o próprio pedido | spec curta, Fase 2 |
| Mudança pequena | spec com as seções que se aplicam | Fase 2 |
| Projeto | spec completa | Fase 2 |

Pedido que são vários projetos independentes vira várias features (item 5 da Fase 1), com brainstorm de uma por vez.

## 8. Spec e builder check

1. Escreva `~/.claude/dev/features/<slug>/spec.md` no formato da seção "Spec" de `references/phase-1-requirements.md`. Não grave no repo e não commite.
2. Avise o Marcelo em 1 linha que um revisor lê a spec antes e que pode voltar 1 vez com perguntas.
3. Dispare `prompts/builder-check.md` com `model: "opus"`, `effort: "medium"`, domínio "engenheiro de software" e o caminho da spec.
4. Separe o retorno em 3 pilhas:
   - Já respondido pela conversa ou pelo código: a resposta entra na spec.
   - Menor: um builder sensato decide sem mudar o que é construído. Decida e marque como decisão do orquestrador.
   - Do Marcelo: só ele responde e a resposta muda o que é construído.
5. A pilha do Marcelo vai numa mensagem só, a mais importante primeiro. É a única rodada do builder check.
6. Entregue a spec com a lista curta das decisões do orquestrador.

## 9. Gate

Nada é construído antes de o Marcelo aprovar a `spec.md`: código de produto, scaffold, dependência, branch de feature, plano. Ler e investigar pode. Exceção: spike que ele aprovou.

Depois da aprovação, o próximo passo é o item 5 da Fase 1 e depois a Fase 2 do /dev. Não invoque `superpowers:writing-plans`.

## 10. Sinais de erro

| Pensamento | Realidade |
|---|---|
| "Vou dar opções para poupar esforço" | Opção direciona. Peça a descrição primeiro. |
| "Vou preencher com padrões sensatos" | Diga cada padrão em voz alta. Padrão que ele não ouviu ele não pôde recusar. |
| "Ele disse 'boa' para a ideia" | A aprovação cobre o que foi mostrado. Spec não escrita não está aprovada. |
| "O spike funciona, sigo em cima dele" | Aproveitar o spike é pedido novo. Volta para a spec. |
| "Já sei a causa do bug" | Sem reprodução e evidência é hipótese. Marque como hipótese. |
