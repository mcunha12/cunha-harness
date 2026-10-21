---
name: master-review
description: Orquestra o swarm de code review. Escolhe os especialistas review-* que se aplicam ao diff, roda todos em paralelo (scan em Haiku), deduplica, verifica cada BLOCKER/MAJOR, cataloga as tasks e dispara agents de correção (Sonnet) para resolver cada uma, sem commitar. Use com /master-review ou ao pedir "revisão completa", "roda todos os revisores", "master review desse MR". Para um tema só, use o especialista direto (/review-seguranca etc.).
argument-hint: "[--lean] [--roast] [--base <branch>] [--path <glob>] [--full] [--only a,b] [--skip a,b] [--severity MAJOR] [--report-only] [--uncommitted] [--mr <id>] [--post]"
model: opus
---

# master-review

O orquestrador roda em Opus. Ele lê o diff, decide quais especialistas rodar, dispara o scan em paralelo, consolida, verifica e corrige. O fluxo padrão termina com o código corrigido no working tree e um relatório. Nada vai para commit.

## Modelos (fixos)

| Papel | Modelo | Como |
|---|---|---|
| Orquestrador (esta skill) | Opus | `model: opus` no frontmatter |
| Scan (um subagent por especialista) | Haiku | Agent tool com `model: "haiku"` |
| Scan de `review-roast` e `review-ux` | Sonnet | Agent tool com `model: "sonnet"` (crítica e leitura de print pedem mais que Haiku) |
| Correção (um subagent por task) | Sonnet | Agent tool com `model: "sonnet"` |

A verificação de BLOCKER/MAJOR (passo 8) é do próprio orquestrador. Ela não sai para subagent.

## Argumentos

`$ARGUMENTS`

| Flag | Efeito |
|---|---|
| `--lean` | Modo do /dev para task de risco alto. Até 5 especialistas, passados em `--only` e escolhidos pelo diff; `spec`, `roast`, `test-audit` e as checagens determinísticas não contam. Piso MAJOR no scan, no relatório e na correção. Revisão visual só no iPhone SE. Relatório curto. Roast desligado, salvo com `--roast`. |
| `--roast` | Liga o `review-roast` no modo `--lean`. Na full ele já roda. |
| `--spec <path>` | Spec da feature (o /dev sempre passa). Liga o eixo Spec (passo 4b) e vai para o roast. |
| `--base <branch>` | Base do diff. Padrão: config > `main` > `master` > `develop`, o primeiro que existir no remote. |
| `--path <glob>` | Restringe o escopo aos arquivos que batem com o glob. |
| `--full` | Repo inteiro. Avise o custo estimado (arquivos × agentes) e faça sharding de ~25 arquivos por subagent. |
| `--only a,b` / `--skip a,b` | Força ou remove agentes (nomes sem prefixo: `seguranca`, `front`). |
| `--severity <nível>` | Piso de severidade no relatório e na correção. Padrão: config ou `MINOR`. |
| `--report-only` | Para no relatório. Não dispara correção. |
| `--uncommitted` | Inclui staged e unstaged. |
| `--mr <id>` | Diff do MR via `glab mr diff <id>`. Sem `glab` autenticado, use o connector GitLab (`get_merge_request`). Com `--mr`, o padrão vira `--report-only`: o working tree local pode ser de outra branch. |
| `--post` | Publica no MR uma discussion por achado BLOCKER/MAJOR, com linha, mais um resumo geral. Mostre a lista e peça confirmação antes de postar. |

## Config

Leia, nesta ordem, e faça merge (o repo sobrescreve o global):

1. `~/.claude/review.config.yml` (global)
2. `<repo>/.claude/review.config.yml`

Se nenhum existir, ofereça criar o do repo a partir de `references/review.config.template.yml` e siga com os padrões. Campos em `references/review.config.template.yml`.

## Workflow

### 1. Escopo

```bash
BASE=$(git merge-base origin/<base> HEAD)
git diff --name-only $BASE...HEAD          # + git diff --name-only HEAD com --uncommitted
git diff $BASE...HEAD -- <arquivos>
```

Remova `ignore_paths` (padrão: lockfiles, `dist/`, `build/`, `coverage/`, `*.snap`, `*.min.*`, gerados, `vendor/`). Diff vazio: diga isso e pare.

### 2. Context packet

Monte um bloco de texto com:

- `repo`: `basename` do toplevel; `branch`; `base`.
- `stack`: detectada pela tabela de `references/review-rules.md` (manifestos, deps, configs). Liste as tecnologias com versão.
- `repo_role`: config, ou inferência pelo README e pelas deps (texto livre). Marque "inferido" quando for inferência.
- `conventions`: campo da config + `CLAUDE.md` do repo (resuma em até 15 linhas os pontos que afetam revisão).
- `related_repos`: caminhos da config.
- `files`: lista de arquivos do escopo, com `+/-` linhas.
- `overlay`: rode `python3 ~/.claude/skills/code-guard/scripts/overlay.py match <repo>`. Com resultado, leia `<dir>/<file>` e acrescente as regras da empresa a `conventions`.
- `diff_path`: salve o diff em `<scratchpad>/master-review/<run>/diff.patch` e passe o caminho. Não cole diff grande no prompt.

### 3. Roteamento

Decida os agentes e imprima a tabela `agente → motivo` / `pulado porque`.

| Agente | Roda quando |
|---|---|
| seguranca, legibilidade, comentarios, clean, dry | sempre que houver código-fonte no escopo |
| test-audit | arquivos de `src` ou de teste mudaram |
| tipagem | linguagem tipada (TS, Python anotado) |
| resiliencia, observabilidade | código server-side (Nest, Express, workers, consumers) ou client HTTP |
| front, a11y | componentes, páginas, estilos, JSX/TSX |
| contratos | controllers/rotas, DTOs, schemas (zod, class-validator, Pydantic), OpenAPI, clients HTTP, props host→remote de Module Federation, eventos de fila |
| queries | ORM, SQL, repositories, handlers que tocam banco, cache, chamadas HTTP em sequência |
| migrations | diretório de migrations ou schema do ORM (`schema.prisma`, `alembic/`, `migrations/`) |
| ia | import de SDK de LLM, arquivos de prompt, MCP, ou `repo_role` de IA |
| modularidade | arquivo/módulo novo, import novo entre módulos, ou mais de ~10 arquivos |
| arquitetura | gatilho da modularidade, dependência nova em manifesto (`package.json`, `pyproject.toml`), ou mecanismo novo (client, fila, cache, cron, estado global) |
| ux | componentes, páginas, estilos, JSX/TSX. Roda depois do passo 8b, com os prints |
| roast | full: sempre que houver código-fonte. Lean: só com `--roast` |

Aplique `skip_agents`, `--only` e `--skip` depois da tabela.

### 3b. Checagens determinísticas (todo modo)

Antes do scan, rode `python3 ~/.claude/skills/code-guard/scripts/diff_checks.py run --repo <repo> --base <base> [--uncommitted]`. Os achados (régua afrouxada: `@ts-ignore`, `eslint-disable` sem motivo, teste com `skip`/`only`, cobertura reduzida, lint ou `strict` afrouxado, e as checagens aprendidas) entram direto na coleta como MAJOR `confirmado`, nível de prova 2. Passe a lista aos especialistas: eles não reportam de novo o que a checagem já pegou.

### 4. Scan em paralelo (Haiku)

Numa única mensagem, uma chamada Agent por especialista, todas com `model: "haiku"` e `subagent_type: "general-purpose"`. Prompt de cada uma:

```
Você é o especialista review-<tema>. Use a Skill tool para carregar a skill "review-<tema>" e siga-a.
Modo: subagent do master-review. Não altere código. Não pergunte nada.
Context packet:
<packet>
Diff: leia <diff_path>. Arquivos do seu escopo: <lista>.
Referências compartilhadas: ~/.claude/skills/master-review/references/
Devolva SOMENTE o bloco ```json do output contract (sem o markdown).
```

Com `--lean`, acrescente ao prompt: "Modo lean: devolva só achados BLOCKER e MAJOR."

roast: `model: "sonnet"`. O context packet vai sem `conventions` e sem overlay: o roast lê o diff como revisor externo. Acrescente a spec da feature quando houver.

Diff com mais de ~1.500 linhas: fatie por grupos de arquivos coesos (mesmo diretório/feature) e dispare um subagent por fatia do mesmo especialista. O teto é 20 subagents simultâneos. Acima disso, rode em ondas.

front e a11y: acrescente ao prompt "Viewport de referência: iPhone SE (375×667). Avalie layout, overflow, texto cortado e alvos de toque nele; depois, desktop. Qualquer render no navegador é headless."

test-audit: dispare um subagent Haiku que carrega a skill `test-audit` e roda o **Mode B (conference gate)** só em modo leitura: itens 1, 3 e 4 (ordem dos commits, fixtures com PII, classificação de cada teste adicionado ou alterado). Ele não roda testes e não edita. O resultado passa pelo adapter de `references/test-audit-adapter.md`.

### 4b. Eixo Spec (com `--spec`)

Dispare um agente `model: "sonnet"`, `effort: "medium"`, com o prompt de `references/spec-review.md`, a spec e o diff. Ele lista requisito faltando, escopo a mais e implementação errada, cada um citando a linha da spec. Prefixo `SPEC`. O relatório tem uma seção própria "Spec": esses achados não entram na dedup com os especialistas. BLOCKER e MAJOR do Spec passam pela verificação do passo 8.

### 5. Coleta e validação

Valide cada JSON contra `references/output-contract.md`: campos obrigatórios, enums de severidade/confiança, `evidence` literal não vazia em todo achado, `fix` concreto. Saída malformada ou achado sem evidência: retome o mesmo subagent (SendMessage) uma vez, com o erro.

Falhou de novo: o especialista vira **lacuna**. Lacuna não conta como aprovação: o relatório lista "lacuna: review-<tema>" e o veredito não passa de **APROVAR COM RESSALVAS**. Chamado pelo /dev, lacuna bloqueia a task até a review rodar de novo.

### 6. Dedup

Mesmo arquivo, linhas sobrepostas e mesma causa raiz → um achado. O dono vem de `references/ownership-matrix.md`. Os outros entram em `co_signed_by`. Co-assinatura de agente independente sobe a confiança um nível.

### 7. Conflitos

Quando dois agentes pedem coisas opostas no mesmo trecho (dry quer extrair, legibilidade quer inline; front quer memo, legibilidade vê ruído), decida com uma frase de justificativa ou registre como trade-off no relatório e não gere task de correção para ele.

### 8. Verificação (obrigatória)

Para cada BLOCKER e MAJOR, o orquestrador abre o arquivo, lê o contexto (caller, callee, config) e confirma. Resultado por achado: `confirmado`, `rebaixado para <nível>` ou `descartado`, sempre com o motivo em uma linha.

Registre o nível de prova (`proof_level`, escada em `references/severity-rubric.md`):

| Nível | Prova |
|---|---|
| 1 | afirmado pelo especialista |
| 2 | `arquivo:linha` lido com o contexto |
| 3 | o caso que tornaria o achado falso foi descartado no código (caller, config, guard) |
| 4 | código rodado: script curto, teste ou request que mostra o defeito |
| 5 | reproduzido no app pelo fluxo real |

BLOCKER exige nível 4 ou mais. Abaixo disso, escreva o script curto que prova o fato central (via `heavy_lock.sh` quando roda testes); sem conseguir, o achado é `rebaixado para MAJOR` com a nota "não provado (nível N)". MAJOR precisa de nível 2 ou mais. Achados de confiança baixa de MINOR para baixo passam sem verificação, mas não viram task de correção.

### 8b. Revisão visual em celular (obrigatória com UI no diff)

Diff com componente, página ou estilo: o orquestrador sobe o app (comando, URL e login de `~/.claude/dev/repos/<repo>/run.json` quando existir) e percorre cada tela alterada pelo fluxo real de cliques, primeiro no iPhone SE, depois em desktop:

```bash
python3 ~/.claude/skills/master-review/scripts/mobile_flow.py --url <url> --out <run>/shots/iphone-se --device iphone-se --steps <steps.json>
python3 ~/.claude/skills/master-review/scripts/mobile_flow.py --url <url> --out <run>/shots/desktop --device desktop --steps <steps.json>
```

`steps.json` descreve o fluxo: `{"click": css}`, `{"type": [css, texto]}`, `{"wait": css | ms}`, `{"text": css}`, `{"shot": nome}` (`"full": true` para página inteira). Nunca use `--window-size=375` do Chrome: o headless não abre janela abaixo de 500 px e o print sai como layout de 500 px cortado. O `mobile_flow.py` emula o aparelho pelo protocolo do Chrome (375×667, DPR 2, toque).

Leia cada print. `report.json` com `scroll_width` acima da largura é rolagem horizontal: achado `front`. Defeito visual vira achado `front` ou `a11y`, com o print e o viewport. Com `--lean`, só iPhone SE. Sem navegador disponível, o relatório registra "revisão visual pendente: <telas>" e o veredito não passa de **APROVAR COM RESSALVAS**. Chamado pelo /dev, revisão visual pendente bloqueia a task.

### 8c. UX

Com UI no diff, dispare o `review-ux` (`model: "sonnet"`) com os prints do 8b, o diff e o job to be done da spec. O resultado passa pela coleta, dedup e verificação (passos 5 a 8).

### 9. Relatório

Salve em `<repo>/.claude/reviews/<branch-sem-barra>-<YYYYMMDD-HHMM>.md` e mostre no terminal. Formato em `references/report-template.md`. Ordem:

Com `--lean`, o relatório tem só: veredito, achados BLOCKER/MAJOR por arquivo (com o nível de prova), Spec (quando houver `--spec`), lacunas, Roast (quando ligado) e Correção.

1. Veredito: **APROVAR** (zero BLOCKER e zero MAJOR), **APROVAR COM RESSALVAS** (MAJOR sem BLOCKER), **BLOQUEAR** (algum BLOCKER).
2. Resumo executivo, 3-5 linhas.
3. Tabela agente × severidade.
4. Achados BLOCKER → MAJOR → MINOR, agrupados por arquivo, com agente(s), evidência e fix.
5. NITs em `<details>`.
6. Trade-offs.
7. Débito pré-existente consolidado, no máximo 5.
8. Agentes executados, pulados e com falha, com motivo.
9. Handoffs não resolvidos.
10. Seção "Correção" (preenchida no passo 11).

### 9b. Ledger (todo modo, inclusive `--report-only` e `--lean`)

Grave os BLOCKER e MAJOR confirmados (ou rebaixados para MAJOR) no ledger da code-guard. Salve os achados verificados, com o campo `verification`, em `<run>/verified.json`:

```bash
python3 ~/.claude/skills/code-guard/scripts/ledger.py append --findings <run>/verified.json --repo <repo> \
  --feature <feature ou avulsa> --task <task ou avulsa> --loaded-domains <domínios da code-guard carregados, se houver>
python3 ~/.claude/skills/code-guard/scripts/ledger.py triggers
```

Trigger na saída: carregue a skill `code-guard` e siga a seção "Ciclo de aprendizado".

Com `--report-only`, pare aqui.

### 10. Catálogo de tasks

Gere uma task por achado confirmado com severidade ≥ piso, exceto trade-offs e confiança baixa. Campos: `task_id`, `finding_ids`, `files`, `severity`, `changes_behavior` (sim/não), `fix`, `verificacao` (o comando que prova o fix).

Agrupe em **lotes por arquivo**: todas as tasks que tocam o mesmo arquivo vão para o mesmo lote. Dois lotes nunca editam o mesmo arquivo. O patch de review-comentarios entra no lote do arquivo correspondente, sempre por último.

Salve o catálogo em `<scratchpad>/master-review/<run>/tasks.json` e mostre a tabela antes de disparar.

### 11. Correção em paralelo (Sonnet)

Numa única mensagem, uma chamada Agent por lote, com `model: "sonnet"` e `subagent_type: "general-purpose"`. Prompt de cada uma:

```
Você é fixer do master-review. Aplique SOMENTE as tasks abaixo, nos arquivos listados. Não toque em outro arquivo, salvo teste novo exigido pela task.
Tasks: <json do lote>
Regras:
- Não commite, não faça push, não instale dependência.
- Task com changes_behavior=sim: carregue a skill test-audit e siga o Mode A (teste que falha antes, depois o fix).
- Siga as convenções do repo (CLAUDE.md, lint). Comentários só one-liner.
- Depois de editar: rode type-check e lint só nos arquivos tocados, e só os testes desses arquivos e de consumidores diretos, com workers limitados (ex.: --maxWorkers=2). Nunca a suíte inteira.
- Se a verificação quebrar e você não resolver em 2 tentativas, reverta só as suas mudanças daquela task (git checkout -p / reaplicar o original) e marque a task como manual.
Devolva JSON: [{ "task_id", "status": "fixed|manual|skipped", "files_changed", "verification": "comando + resultado", "note" }]
```

Depois que todos voltarem:

1. Rode `git diff --stat` e confira que só os arquivos dos lotes mudaram. Arquivo inesperado: mostre ao usuário e não reverta sem perguntar (pode ser outra sessão).
2. Rode o type-check do repo uma vez (`tsc --noEmit -p <tsconfig>` ou equivalente) e o lint nos arquivos alterados.
3. Falha atribuível a um lote: reverta aquele lote e marque as tasks como manuais.
4. Preencha a seção "Correção" do relatório: tabela task → status → verificação, e a lista de tasks manuais.

### 12. `--post`

Só depois da confirmação do usuário. Uma discussion por BLOCKER/MAJOR confirmado, ancorada na linha (`glab api projects/:id/merge_requests/<iid>/discussions` com `position`), mais uma nota de resumo. Use `--field body=@arquivo` para corpo longo.

## Regras do orquestrador

- Nunca commite, faça push ou abra MR.
- Nunca reverta mudança que não veio de um fixer deste run.
- Toda contagem no relatório vem do JSON. Não estime.
- Escreva em PT-BR operacional: frase curta, número no lugar de qualificador, sem preâmbulo.
