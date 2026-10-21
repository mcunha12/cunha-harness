Você escreve o bloco "Situação agora" do tracker da feature. Não edite código nem o estado.

Leia {{feature_dir}}/state.json, {{feature_dir}}/plan.json e as últimas 5 linhas de {{feature_dir}}/decisions.jsonl.
Marco que disparou esta atualização: {{milestone}}

Escreva de 3 a 5 linhas, nesta ordem:
1. o que avançou desde o último marco;
2. o que está travado e por quê (task bloqueada, gate bloqueado, review com MAJOR), ou "nada travado";
3. o que vem a seguir no caminho crítico.

Regras: PT-BR, STE Operacional. Uma ideia por linha. Ids das tasks e dos gates como estão no plano. Número no lugar de qualificador. Sem preâmbulo, sem opinião.

Grave {{feature_dir}}/situation.json no formato {"at": "<ISO agora>", "lines": ["…", "…"]} e depois rode:
python3 ~/.claude/skills/dev/scripts/render_tracker.py {{feature_dir}}
Devolva só "ok".
