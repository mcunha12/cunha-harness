# Comentários: regras agnósticas de linguagem

## Princípio

Um comentário carrega informação que o código não carrega. O código diz o quê e como. O comentário diz por quê. A regra do time reduz o comentário a uma linha, porque explicação longa envelhece, diverge do código e esconde um nome ruim.

Teste por comentário, nesta ordem:
1. Apague o comentário. O leitor perde informação? Não perde: remova.
2. O comentário descreve o que o código faz? Renomeie ou extraia, e remova o comentário (handoff para review-legibilidade).
3. Cabe em uma linha? Não cabe: condense, ou mova para README/ADR/ticket e deixe um one-liner com o link.
4. Está vigente no código do diff? Não está: corrija ou remova.

## Como contar linhas

- Uma sequência de linhas `//` ou `#` sem linha de código no meio é um comentário.
- Bloco `/* ... */` e `/** ... */`: conte as linhas de texto. `/** Texto. */` em uma linha é one-liner. `/**\n * Texto.\n */` tem uma linha de texto e três de moldura. Condense para `/** Texto. */` ou `// Texto.`, o que o repo usa.
- Docstring Python de linha única (`"""Texto."""`) é one-liner. Docstring com linha em branco e seções (Args, Returns) é multi-linha.
- Comentário de fim de linha mais comentário acima, no mesmo trecho: conte juntos se falam do mesmo código.
- Linhas em branco dentro do bloco contam como separação de parágrafo: bloco multi-linha.

## Quando condensar e quando remover

Condense quando o bloco tem uma informação que o código não mostra. Escreva a informação em ≤ 100 caracteres. Mantenha o verbo no presente e a unidade. Ordem de corte dentro do bloco: descrição do que faz, parâmetros que repetem a assinatura, tipo de retorno que a assinatura já declara, exemplos de uso, motivo. O motivo é o que sobra.

Remova quando todo o conteúdo repete o código, a assinatura ou o nome da função.

Mova para fora quando a explicação é de design, algoritmo ou domínio com mais de uma linha (regra de cálculo, fluxo entre serviços, decisão de arquitetura). Deixe um one-liner com o ponteiro (`// Regra de elegibilidade: docs/specs/elegibilidade.md`). Sugira o destino no `problem`: README do módulo, ADR (`docs/adr/`), ticket, wiki. Nunca crie o documento. Escrever esse texto é decisão do autor.

## O que vale um comentário (porquê)

Alto valor, adicione quando ausente:
- Bug de dependência externa contornado. Inclua versão ou link: `// Workaround: axios 1.6 ignora timeout em stream (axios#6003)`.
- Regra de negócio com origem fora do código: `// Prazo de 30 dias corridos, regulamento 2024 art. 5`.
- Invariante que o tipo não expressa: `// Sempre ordenado por data asc`, `// Nunca vazio: validado no DTO`.
- Unidade e escala: ms, s, centavos, bytes, 0-1 versus 0-100.
- Valor mágico justificado: `// 600 min = 10h exigidas pelo regulamento`.
- Ordem ou sincronização crítica: `// Fechar a conexão antes de limpar o pool`.
- Decisão contraintuitiva: promise sem await, `==` deliberado, catch vazio deliberado, loop sequencial deliberado, cópia deliberada em vez de reuso.
- Risco: `// Não logar: contém token`, `// Idempotente: pode rodar duas vezes`, `// Não é thread-safe`.
- Intenção de regex, bitmask, fórmula, query com hint.

Baixo valor, não adicione:
- Descrição da função que o nome já dá.
- Descrição de parâmetro cujo nome e tipo bastam.
- Cabeçalho de arquivo com nome do autor e data.
- Comentário sobre o que a próxima linha faz.

## TODO, FIXME, HACK, XXX

- Formato aceito: `TODO(JIRA-123): descrição curta`. O ticket é o dono.
- Sem ticket e sem dono identificável: remova, e cite o texto no `problem` para o autor abrir o ticket. Não invente número de ticket.
- Ticket conhecido pela branch (`feat/ABC-123-...`) ou mensagem de commit do diff: use esse número e marque `confidence: media`.
- `FIXME`/`HACK` que descreve bug conhecido em código novo do diff: severidade MAJOR no `problem`, handoff para o dono do tema (review-resiliencia, review-seguranca etc.). O comentário esconde o defeito.
- TODO antigo (fora do diff) vai para `preexisting_debt` (máx 3), só quando referencia ticket fechado ou funcionalidade que já existe.

## Desatualizado e mentiroso

Procure no diff, quando o código mudou e o comentário vizinho não mudou:
- Parâmetro adicionado, removido ou renomeado e o comentário cita o antigo.
- Comportamento de erro alterado (retorna null para lança, lança para retorna Result).
- Constante com valor novo e comentário com o valor antigo (`// 24h` ao lado de `60 * 60 * 1000`).
- Condição invertida, ordem trocada, passo removido de uma lista numerada.
- Nome de campo, rota, função ou flag citado que não existe mais (`grep` para confirmar).
- `@param`/`@returns` de parâmetro inexistente.

Corrija o comentário para o comportamento atual em uma linha, ou remova. Mentiroso é MAJOR: um leitor decide com base nele.

## Código comentado

- Qualquer linha que compila ou parseia quando descomentada.
- Exceção: exemplo de uso numa linha dentro de comentário de um workaround (`// Antes: new Date(s) (quebrava no Safari)`). Mantenha só se for o porquê.
- Bloco `if (false)`, `/* istanbul ignore */` com código morto, `return; // resto não roda`: o dono é review-clean (código morto). Reporte só o comentário.

## Banners, moldura e ruído

- Linhas de `=`, `-`, `*`, `#`, `~` repetidos. Cabeçalhos `// ---- Helpers ----`. Remova. Se o arquivo precisa de seções, o arquivo é grande: handoff para review-modularidade.
- Comentários de sequência `// Step 1`, `// Step 2`: remova. Se as etapas têm nomes que importam, handoff para review-clean (extract function).
- Assinatura e autoria (`// Created by`, `// Author:`, `// Data:`). Remova. O git guarda.
- Referência de ticket sem motivo (`// JIRA-123`): remova. O blame leva ao commit. Mantenha quando o ticket explica por que o código é estranho.
- Emojis e ascii art.

## Comentário de teste

- Descrever o cenário em um one-liner é válido (`// Aluno com matrícula trancada`).
- `// arrange`, `// act`, `// assert`: NIT, remova se o repo não adota o padrão.
- Teste comentado ou `skip` com comentário: handoff para test-audit.

## Comentário em configuração e infra

- `Dockerfile`, `nginx.conf`, YAML, Helm, `.env.example`, `docker-compose`: one-liner que explica o porquê de uma diretiva (`# no-store: env-config.js define window.env`) é de alto valor. Bloco longo vira link para doc.
- Multi-linha de licença ou aviso legal: preserve.
- Comentário em SQL (`--`): permitido e desejável sobre locks, índices e backfill. Multi-linha segue a regra.

## Segurança e privacidade em comentário

- Segredo, token, senha, IP interno, e-mail real, CPF, dado de aluno em comentário ou em exemplo: remova no patch e registre handoff para review-seguranca (rotação é decisão deles).
- Nome de pessoa em comentário (`// pedir ao João`): remova, ou troque por ticket/time.

## Como montar o patch

- Gere diff unificado por arquivo com cabeçalho `--- a/<path>` e `+++ b/<path>`, hunks `@@ -a,b +c,d @@` e 3 linhas de contexto. Numere a partir do arquivo na árvore de trabalho.
- Hunks vizinhos (< 7 linhas entre eles) se fundem num só, como o `git diff` faz.
- Remover um comentário que ocupa uma linha inteira e deixa duas linhas em branco: remova também uma linha em branco.
- Não reformate código. Não mude indentação do código. Não altere espaço em branco fora do comentário.
- Valide: toda linha `+`/`-` do patch é comentário ou linha em branco removida por consequência. Se alguma linha de código aparece, descarte o hunk e refaça.
- O consolidado junta todos os arquivos, na ordem alfabética dos paths.

## Quando não mexer

- Arquivo gerado, vendor, minificado, lockfile, snapshot.
- Comentário fora do diff. Reporte no máximo 3 em `preexisting_debt` quando o arquivo foi tocado e o comentário mente.
- Comentário com diretiva de ferramenta. Em dúvida, preserve.
- Texto em markdown e documentação.
- Idioma. Não traduza comentário existente.
