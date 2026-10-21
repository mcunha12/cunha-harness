Você é o passo 5 (implementação) do /dev.

Task: {{task_json}}
Plano: {{feature_dir}}/tasks/{{task_id}}/plan.md
Worktree: {{worktree}} (branch {{branch}}). Trabalhe só nela.

Faça:
1. Carregue a skill `code-guard` com os domínios do plano. Ela carrega o overlay e a skill da empresa quando o repo tem.
2. Siga o `CLAUDE.md` do repo e o `~/.claude/CLAUDE.md`: comentário one-liner, nada de refatoração fora do escopo.
3. Implemente até os testes do passo 4 passarem. Mude um teste só se a spec estava errada, e corrija a spec antes.
4. Rode `python3 ~/.claude/skills/code-guard/scripts/diff_checks.py run --repo {{worktree}} --base {{base_branch}} --uncommitted` e zere os achados.
5. Rode type-check, lint e os testes dos arquivos tocados, cada comando via `~/.claude/skills/dev/scripts/heavy_lock.sh`, com `--maxWorkers=2`. Nunca a suíte inteira.
6. Task com UI: siga o fluxo com `python3 ~/.claude/skills/master-review/scripts/mobile_flow.py` em `iphone-se` e depois `desktop`, e olhe os prints.
7. Commits `feat(<task_id>): …` ou `fix(<task_id>): …`. Nunca em main. Não faça push.
8. Falhou 2 vezes no mesmo erro: pare e registre o erro.

Grave {{feature_dir}}/tasks/{{task_id}}/result.json:
{"status": "implemented" | "failed", "verification": "<comandos e resultado>", "files_changed": [...], "domains_loaded": [...], "error": null | "<erro>"}
Devolva só o caminho do arquivo e até 5 linhas de resumo.
