---
name: review-ux
description: Revisa usabilidade de um diff de UI (UX) pela lente Caminho A→B - quanto a tela aumenta o caminho do usuário até o job to be done - com um framework que junta Nielsen, Shneiderman, Norman e as heurísticas SMART de Joyce e Lilley. Sempre a partir do fluxo real de cliques no iPhone SE (375×667) e depois desktop. Acione em "revisa a UX desse PR", "essa tela está fácil?", "/review-ux" ou via master-review. NÃO cobre WCAG, teclado, ARIA e contraste (review-a11y), performance de render (review-front) nem copy jurídica.
argument-hint: "[--base <branch>] [--path <glob>] [--uncommitted]"
---

# review-ux

## Missão

Reduzir a carga cognitiva do usuário para ir do ponto A ao ponto B e resolver o job to be done. Cada achado diz quanto o diff aumenta esse caminho: passos, decisões, campos ou itens a lembrar a mais.

## Entrada

- Prints do fluxo real de cliques, capturados pelo orquestrador no passo 8b da master-review com `~/.claude/skills/master-review/scripts/mobile_flow.py`: iPhone SE primeiro, desktop depois. Standalone, capture você mesmo com esse script. Nunca use `--window-size=375` do Chrome: o headless não abre janela abaixo de 500 px e o print sai cortado.
- O diff.
- O job to be done da spec. Sem spec, escreva o job em uma frase a partir do diff e marque como inferido.

## Framework

Leia `references/caminho-a-b.md`: 10 dimensões, fontes, heurísticas SMART e como contar o caminho.

## Processo

1. Leia `~/.claude/skills/master-review/references/output-contract.md`, `severity-rubric.md` e `ownership-matrix.md`.
2. Escreva o job to be done e o ponto A.
3. Percorra os prints de iPhone SE na ordem do fluxo. Conte passos, decisões, campos e itens a lembrar.
4. Passe cada tela pelas 10 dimensões. Repita no desktop só o que muda de layout.
5. Classifique com a rubrica abaixo e a global.
6. Emita no output contract. Prefixo dos ids: `UX`. `evidence` cita o print (`arquivo.png`) e o trecho do diff. `problem` diz o custo no caminho A→B.

Standalone: mostre o markdown no final. Não altere código.

## Rubrica de severidade do tema

**BLOCKER**
- O job to be done não pode ser concluído no iPhone SE: ação principal inalcançável, cortada ou coberta, ou fluxo sem saída.

**MAJOR**
- Passo, decisão ou item de memória a mais no caminho principal sem necessidade do job.
- Ação principal fora da primeira dobra em 375×667, sem pista de rolagem.
- Erro sem mensagem que diga como sair, ou que apaga o que o usuário digitou.
- Ação destrutiva sem confirmação nem desfazer.
- Estado sem feedback: carregamento, sucesso ou falha invisíveis.
- Termo diferente para o mesmo conceito dentro do fluxo.

**MINOR**
- Digitação que um seletor, valor padrão ou sensor eliminaria.
- Hierarquia visual que compete com a ação principal.
- Falta de atalho para quem repete a tarefa.

**NIT**
- Ajuste de espaçamento ou texto sem efeito no caminho.

## Fora de escopo e dono

| Tema | Dono |
|---|---|
| Teclado, foco, ARIA, contraste, alvo de toque (WCAG 2.2) | review-a11y |
| Re-render, bundle, Web Vitals | review-front |
| Shape de dados da API | review-contratos |

## Heurísticas anti-falso-positivo

- Passo exigido por regra de negócio, lei ou segurança (confirmação de pagamento, consentimento) não é passo a mais.
- Padrão da plataforma ou do design system do repo prevalece sobre preferência.
- Sem print, não há achado de layout: registre "revisão visual pendente" no `summary`.

## Exemplos

### [MAJOR] UX-001 — Ação principal abaixo da dobra no iPhone SE

- Evidência: `inicial.png` (375×667) mostra três cards informativos antes do botão "Ativar lembrete".
- Problema: o usuário precisa rolar e achar o botão; o job (ativar o lembrete) ganha um passo e uma busca visual.
- Fix: mover o botão para o topo do card principal ou fixar a ação no rodapé.
