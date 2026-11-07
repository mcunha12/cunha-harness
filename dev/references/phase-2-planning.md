# Fase 2 — Plano da feature

Roda quando a feature começa: `devstate.py phase <dir> planning`. A camada de código envelhece, então nunca roda antes.

## 1. Revalidação

Cruze os arquivos que as features anteriores alteraram (`git diff --name-only` das branches delas) com o recon desta feature. Interseção: as decisões da spec que dependem desses arquivos voltam ao Marcelo. Sem interseção, siga.

## 2. Quebra em tasks

Campos de cada task: `references/state-layout.md` (plan.json). Uma task toca um repo só.

Complexidade:

| Nota | Critério |
|---|---|
| 1 | 1 arquivo, mudança local |
| 2 | 2 a 3 arquivos no mesmo módulo |
| 3 | 4 a 8 arquivos ou 2 módulos |
| 4 | 9 a 15 arquivos, 3+ módulos ou lógica nova não trivial |
| 5 | mais de 15 arquivos ou mudança transversal |

Risco:

| Nota | Critério |
|---|---|
| 1 | copy, estilo, sem lógica |
| 2 | UI com lógica local |
| 3 | regra de negócio coberta por teste existente |
| 4 | contrato entre serviços, autenticação, dinheiro, dado de usuário |
| 5 | migration de schema, dado irreversível, segurança |

O risco entra no custo da task (complexidade × risco) e na prioridade do agendador. Nenhuma task tem review própria: o gate final revisa o diff inteiro.

Os passos 1 e 3 rodam em Opus `xhigh` em toda task. O modelo do passo 5 (Haiku `medium` ou Sonnet `medium`) é decisão do passo 3.

`changes_behavior` marca a task cujo comportamento os testes finais cobrem.

## 3. Gate final

O plano tem um gate só, o final, que espera todas as tasks. Nenhuma task depende dele. `devgraph.py validate` recusa qualquer outro gate com `intermediate_gate` (07/11/2026).

Antes do gate rodam os testes finais. O gate é a /master-review full com QA, uma por repo, com os outros repos em `related_repos`. Ele passa quando a review termina sem BLOCKER e sem MAJOR depois da correção.

## 4. Validar e analisar

```bash
python3 ~/.claude/skills/dev/scripts/devgraph.py validate <dir>/plan.json
python3 ~/.claude/skills/dev/scripts/devgraph.py analyze <dir>/plan.json
```

Erro de validação: refaça a quebra. Ciclo que persiste depois de uma refeita: leve ao Marcelo.

O `analyze` grava custos, caminho à frente, caminho crítico e clusters (MST sobre a distância de Jaccard dos `files_hint`, corte em 0,8, até 4 tasks por cluster).

## 5. Publicar

Crie as branches da feature (`feat/<slug>`) em cada repo a partir da base, registre em `state.json` e gere o tracker. Suba o servidor do tracker, se ele ainda não estiver no ar, e imprima o link:

```bash
curl -sf http://localhost:4777/health >/dev/null || (nohup python3 ~/.claude/skills/dev/scripts/tracker_server.py >/dev/null 2>&1 &)
echo "http://localhost:4777/f/<slug>"
```

Baseline de falhas: rode uma vez, na base, os testes da área que o plano toca (via `heavy_lock.sh`, workers limitados) e grave os que já falham com `devstate.py baseline <dir> '<json-list>'`. Implementador, testes finais e gate leem `state.baseline_failures` e não reinvestigam essas falhas. Em ranking-fellowship (21/10/2026), a falha do card 17205 foi investigada em 4 lugares.

A página aberta pelo localhost se atualiza sozinha a cada checkpoint, sem recarregar e sem perder a rolagem. Aberta como arquivo, ela recarrega a cada 10 s. `devstate.py phase <dir> execution`. A execução começa sem esperar aprovação.
