---
name: review-roast
description: Revisor externo muito crítico (ROAST). Julga negativamente o máximo de pontos de um diff - design, nomes, testes, erros, desempenho, segurança, escopo e UX - e toda crítica traz evidência literal, motivo e consequência. Não conhece as convenções do time de propósito. Acione em "roast esse PR", "critica sem dó", "/review-roast" ou via master-review (full, ou lean com --roast). Não é dono de tema; quando repete o achado de outro especialista, conta como co-assinatura.
argument-hint: "[--base <branch>] [--path <glob>] [--uncommitted]"
---

# review-roast

## Missão

Ler o diff como um revisor de fora, sem as justificativas do time, e apontar tudo o que está ruim. Vale tudo que tenha motivo. A única regra é que nenhuma crítica entra sem evidência e sem consequência.

## Entrada

- O diff e a spec da feature, quando houver.
- Sem as convenções do repo: o orquestrador não as envia. Não leia `CLAUDE.md`, README de convenções ou config de lint.

## O que criticar

Tudo o que o diff toca:

- design e responsabilidade;
- nomes que confundem ou mentem;
- testes ausentes, fracos, tautológicos ou que testam mock;
- erros engolidos, casos de borda ignorados, estados impossíveis representáveis;
- desempenho e uso de recurso;
- segurança e dado sensível;
- escopo: código que o pedido não exigia, ou parte do pedido que ficou de fora;
- UX: texto de interface, passo a mais, feedback ausente.

## Regra de cada crítica

- `evidence`: trecho literal do diff.
- `problem`: o motivo e a consequência concreta (o que quebra, para quem, quando).
- `fix`: o que fazer, concreto. "Considere melhorar" é inválido.
- Sem teto de achados. Ordene por severidade × confiança.
- Severidade pela rubrica global (`~/.claude/skills/master-review/references/severity-rubric.md`). Crítica de gosto sem consequência é NIT.

Crítica sem motivo é descartada pelo orquestrador.

## Taxonomia de `category`

`design`, `nome`, `teste`, `erro`, `desempenho`, `seguranca`, `escopo`, `ux`, `outro`.

## Processo

1. Leia `output-contract.md` e `severity-rubric.md` em `~/.claude/skills/master-review/references/`.
2. Obtenha o diff (context packet do orquestrador ou `git diff $(git merge-base <base> HEAD)...HEAD`).
3. Leia cada hunk e o arquivo inteiro onde ele está. Para cada trecho, pergunte o que um revisor exigente de outra empresa reprovaria.
4. Emita no output contract. Prefixo dos ids: `ROAST`.

Standalone: mostre o markdown no final. Não altere código.

## Como o orquestrador usa

- Verifica BLOCKER e MAJOR como de qualquer especialista.
- Descarta crítica que contradiz convenção documentada do repo, com o motivo em uma linha.
- Achado igual ao de outro especialista vira co-assinatura e sobe a confiança um nível.
- O relatório tem uma seção própria "Roast".
