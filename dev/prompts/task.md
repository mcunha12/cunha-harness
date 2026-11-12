Você implementa uma task do /dev.

Task: {{task_json}}
Plano: seção `## {{task_id}}` de {{feature_dir}}/plan.md
Spec: {{feature_dir}}/spec.md
Onde trabalhar: {{workdir}} (branch {{branch}}). Trabalhe só nele.
{{retry_context}}

Faça:
1. Leia a seção da task no plano e os arquivos que ela cita.
2. Leia `{{feature_dir}}/guard.md` e aplique as regras. Não carregue a skill `code-guard`.
3. Task com UI em repo com Impeccable: siga `~/.claude/skills/dev/references/impeccable.md`, linha "Task com UI". Task com UI em qualquer repo: siga `~/.claude/skills/dev/references/unslop.md` e a prioridade de tela da spec.
4. Siga o `CLAUDE.md` do repo e o `~/.claude/CLAUDE.md`: comentário one-liner, nada de refatoração fora do escopo.
5. Implemente o plano. Não escreva teste novo: os testes entram no fim da feature.
6. Teste existente que quebra porque a spec muda aquele comportamento: ajuste só a asserção e liste o teste em `tests_adjusted`. Teste que quebra por outro motivo é defeito do código: corrija o código.
7. Rode `python3 ~/.claude/skills/code-guard/scripts/diff_checks.py run --repo {{workdir}} --base {{base_branch}} --uncommitted` e zere os achados.
8. Rode os comandos de verificação do plano, cada um via `~/.claude/skills/dev/scripts/heavy_lock.sh`, com `--maxWorkers=2`. Nunca a suíte inteira. Falha listada em `baseline_failures` do state.json já existia: não investigue.
9. Commits `feat({{task_id}}): …` ou `fix({{task_id}}): …`. Nunca em main. Não faça push.
10. Mesmo erro 2 vezes: pare e registre o erro.

Não suba navegador: a tela passa pelo QA do gate final.

Grave {{feature_dir}}/tasks/{{task_id}}/result.json:
{"status": "implemented" | "failed", "verification": "<comandos e resultado>", "files_changed": [...], "tests_adjusted": [...], "error": null | "<erro>"}
Devolva só o caminho do arquivo e até 5 linhas de resumo.
