Você é o passo 5 (implementação) do /dev.

Task: {{task_json}}
Plano: {{feature_dir}}/tasks/{{task_id}}/plan.md
Worktree: {{worktree}} (branch {{branch}}). Trabalhe só nela.

Faça:
1. Carregue a skill `code-guard` com os domínios do plano. Ela carrega o overlay e a skill da empresa quando o repo tem.
2. Siga o `CLAUDE.md` do repo e o `~/.claude/CLAUDE.md`: comentário one-liner, nada de refatoração fora do escopo.
3. Implemente o plano. Não escreva teste novo: no /dev os testes entram no fim da feature, depois de todas as tasks. O item da code-guard que pede a /test-audit (Mode A) antes do código não vale aqui.
4. Teste existente que quebra porque a spec muda aquele comportamento: ajuste só a asserção à spec e liste o teste em `tests_adjusted`. Teste que quebra por outro motivo é defeito do código: corrija o código.
5. Rode `python3 ~/.claude/skills/code-guard/scripts/diff_checks.py run --repo {{worktree}} --base {{base_branch}} --uncommitted` e `python3 ~/.claude/skills/dev/scripts/fixture_pii.py {{worktree}} {{base_branch}}`, e zere os achados. Falha listada em `baseline_failures` do state.json já existia: não investigue.
6. Rode os comandos de verificação do plano: type-check, lint e os testes que já existem para os arquivos tocados, cada comando via `~/.claude/skills/dev/scripts/heavy_lock.sh`, com `--maxWorkers=2`. Nunca a suíte inteira.
7. Commits `feat(<task_id>): …` ou `fix(<task_id>): …`. Nunca em main. Não faça push.
8. Falhou 2 vezes no mesmo erro: pare e registre o erro.

A tela alterada passa pelo QA do gate final. Não suba navegador nesta task.

Grave {{feature_dir}}/tasks/{{task_id}}/result.json:
{"status": "implemented" | "failed", "verification": "<comandos e resultado>", "files_changed": [...], "tests_adjusted": [...], "domains_loaded": [...], "error": null | "<erro>"}
Devolva só o caminho do arquivo e até 5 linhas de resumo.
