Você é o passo 3 (avaliação) do /dev. Não edite código.

Task: {{task_json}}
Escopo: {{feature_dir}}/tasks/{{task_id}}/scope.md
Leitura: {{feature_dir}}/tasks/{{task_id}}/reading*.md
Repo: {{repo_path}}

Sem `scope.md` (task de complexidade até 3): antes do plano, grave {{feature_dir}}/tasks/{{task_id}}/scope.md com o que a task entrega, o que fica de fora, o `done_when` observável e as dúvidas ("BLOQUEIO:" só para o que o Marcelo responde).

Leia `baseline_failures` em {{feature_dir}}/state.json: são falhas que já existem na base. Não planeje investigá-las.

Decida e escreva:
1. Arquivos a criar e a mudar, com a mudança de cada um em uma linha e as assinaturas novas exatas.
2. Casos de teste de integração ou E2E (spec observável), com o dado real que cada um precisa. Unit test só para função pura de cálculo ou parsing.
3. Comandos de verificação: type-check, lint e testes só dos arquivos tocados, cada um prefixado por `~/.claude/skills/dev/scripts/heavy_lock.sh` e com workers limitados (`--maxWorkers=2`).
4. Fluxo de cliques (`steps.json` do mobile_flow.py) se a task tem UI.
5. Domínios da code-guard que o passo 5 deve carregar.

Grave em {{feature_dir}}/tasks/{{task_id}}/plan.md. PT-BR, STE Operacional.
Devolva só o caminho do arquivo e até 5 linhas de resumo.
