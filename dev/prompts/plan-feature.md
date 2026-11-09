Você faz o plano da feature do /dev. Leia o código uma vez e planeje todas as tasks. Não edite código.

Feature: {{feature_dir}} (spec.md, decisions.jsonl, state.json)
Mapeamento da Fase 1: {{recon_path}}
Repos: {{repos_json}} (caminho, branch da feature, base, impeccable)

Faça:
1. Leia a spec, o mapeamento e os arquivos que a feature toca. Siga o que eles importam de mais próximo. Anote os padrões que o repo já usa para o mesmo problema.
2. Leia `baseline_failures` no state.json: falhas que já existem na base. Não planeje investigá-las.
3. Repo com `"impeccable": true`: siga `~/.claude/skills/dev/references/impeccable.md`, linha "Plano".
4. Quebre a feature em tasks. Uma task toca um repo só. Ordene a lista para que `depends_on` cite só tasks anteriores. Use a tabela de complexidade e risco de `~/.claude/skills/dev/references/phase-2-planning.md`.
5. Escolha o modelo e o esforço de cada task e os overrides da review pelas "Notas do plano" de `~/.claude/skills/dev/references/phase-2-planning.md`. Todo modelo acima do padrão leva o motivo em 1 linha no plan.md.
6. Grave {{feature_dir}}/plan.json no formato de `~/.claude/skills/dev/references/state-layout.md`.
7. Grave {{feature_dir}}/plan.md com uma seção `## <id> — <título>` por task, nesta ordem:
   - arquivos a criar e a mudar, com a mudança de cada um em 1 linha e as assinaturas novas exatas, com `arquivo:linha` do ponto de mudança;
   - padrão do repo a seguir, com `arquivo:linha` do exemplo;
   - "Comportamentos": cada comportamento observável que muda (entrada → saída que o usuário ou o consumidor vê), com o dado real que prova cada um. Os testes finais partem daqui;
   - comandos de verificação: type-check, lint e testes que já existem para os arquivos tocados, cada um prefixado por `~/.claude/skills/dev/scripts/heavy_lock.sh` e com `--maxWorkers=2`;
   - domínios da code-guard que a task carrega;
   - com UI e Impeccable: modo da tela, `--target`, tokens e componentes do DESIGN.md, comando do Impeccable.
8. Task com UI: grave {{feature_dir}}/tasks/<id>/steps.json com o fluxo de cliques de cada tela alterada, no formato do `mobile_flow.py` da master-review.

Dúvida que só o Marcelo responde: escreva "BLOQUEIO:" e a pergunta no topo do plan.md.
PT-BR, STE Operacional. Devolva só os caminhos e até 5 linhas de resumo: número de tasks, modelos acima do padrão, gate lean ou full, overrides, bloqueios.
