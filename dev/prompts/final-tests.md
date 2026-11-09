Você escreve os testes finais do /dev para um repo. Todas as tasks da feature já estão na branch da feature. Os testes entram agora, depois do código.

Feature: {{feature_dir}} (spec.md, plan.json, plan.md, state.json)
Repo: {{repo_path}}, na branch da feature {{feature_branch}} (base {{base_branch}}). Trabalhe só nela.

Faça:
1. Carregue a skill `test-audit`. A tabela "Classify every test case" é o critério de entrada: escreva só teste com veredito "Behavior". Nada tautológico, change-detector, regressão sem lacuna, morto ou unit fora da exceção (função pura de cálculo ou parsing, com a lista de modos de falha escrita antes). Siga o `AGENTS.md` do repo quando ele for mais restrito.
2. Liste os comportamentos que mudaram neste repo: a seção "Comportamentos" das tasks do repo no `plan.md`, cruzada com os critérios de aceite da `spec.md` e com `git diff {{base_branch}}...{{feature_branch}}`. Corte o comportamento que um teste existente já cobre.
3. Escreva um teste de integração ou E2E por comportamento que sobrou, com dado real anonimizado (só leitura; nunca escreva em produção). Cada teste afirma um resultado observável.
4. Rode só os testes novos, via `~/.claude/skills/dev/scripts/heavy_lock.sh`, com `--maxWorkers=2`. Todos passam. Falha listada em `baseline_failures` do state.json já existia: não investigue.
5. Prove que cada teste pega a regressão: crie uma worktree temporária em {{base_branch}}, copie para ela só o teste e as fixtures, rode via `heavy_lock.sh` e remova a worktree. Teste que passa na base não prova o comportamento novo: reescreva ou apague.
6. Rode `python3 ~/.claude/skills/dev/scripts/fixture_pii.py {{repo_path}} {{base_branch}}`. Exit 1: troque o dado apontado por pseudônimo (`Aluno Exemplo NN`, `@exemplo.com`, `Cidade Exemplo N`/`ZZ`, `11900xxxxxx`) e rode de novo.
7. Commit só dos testes e das fixtures: `test(<feature>): …`. Nunca em main. Não faça push.

Repo sem comportamento testável (só copy, estilo ou config): não escreva teste e registre o motivo.

Grave {{feature_dir}}/final-tests/{{repo}}.md: cada teste com o comportamento que cobre, o veredito da /test-audit, o comando, a saída verde e a saída na base. Depois, cada comportamento sem teste e o motivo.
Devolva só o caminho do arquivo e até 5 linhas de resumo.
