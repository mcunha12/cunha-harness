---
name: retro
description: Retro de uma feature do /dev - checagens automáticas que faltaram, regras da code-guard sem efeito, custo e navegação. Só roda quando o Marcelo chama /retro <feature>; o /dev não a dispara.
argument-hint: "<feature>"
user-invocable: true
---

# /retro

1. Sem argumento: liste as features em `~/.claude/dev/features/` com `phase: done` e pergunte qual.
2. Dispare 1 agente `model: "haiku"`, `effort: "medium"`, `subagent_type: "general-purpose"` com `prompt.md` desta pasta. Troque `{{feature_dir}}` por `~/.claude/dev/features/<feature>` e `{{feature}}` pelo slug.
3. O agente grava `<feature_dir>/retro.md`.
4. Cada checagem da seção 1 passa pelo nível 1 do ciclo de aprendizado da `code-guard`: `python3 ~/.claude/skills/code-guard/scripts/diff_checks.py add-check`, que recusa o que não dispara num erro real.
5. Regras sem efeito e custos viram decisões em `decisions.jsonl` (`origin: "code-guard"`). Nada é removido sozinho.
6. Mostre ao Marcelo o caminho do `retro.md` e as checagens aceitas e recusadas.
