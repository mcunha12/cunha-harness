Você é o passo 4 (testes antes do código) do /dev.

Task: {{task_json}}
Plano: {{feature_dir}}/tasks/{{task_id}}/plan.md
Worktree: {{worktree}} (branch {{branch}}, base {{base_branch}}). Trabalhe só nela.

Faça:
1. Carregue a skill `test-audit` e siga o Mode A.
2. Escreva a spec e os testes de integração/E2E do plano, com dado real anonimizado (só leitura; nunca escreva em produção).
3. Rode só os testes novos, via `~/.claude/skills/dev/scripts/heavy_lock.sh`, com workers limitados. Cada um falha porque o comportamento não existe, nunca por erro de setup.
4. Rode `python3 ~/.claude/skills/dev/scripts/fixture_pii.py {{worktree}} {{base_branch}}`. Exit 1: troque o dado apontado por pseudônimo e rode de novo.
5. Commit só da spec e dos testes: `test(<task_id>): …`. Nunca em main.

Grave um resumo em {{feature_dir}}/tasks/{{task_id}}/tests.md (testes, comando, saída do vermelho).
Devolva só o caminho do arquivo e até 5 linhas de resumo.
