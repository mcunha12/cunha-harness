---
name: code-guard
description: Diretrizes de escrita derivadas dos especialistas review-* (só o que gera BLOCKER ou MAJOR). Carregue ANTES de escrever ou alterar código em qualquer repo, núcleo sempre, domínios pelo tipo de arquivo, regras aprendidas e overlay da empresa. Use ao implementar, refatorar ou corrigir código, e no passo 5 do /dev. A master-review confere depois; a code-guard evita que o problema nasça.
---

# code-guard

A master-review acha o problema depois do código. A code-guard diz como escrever para ele não aparecer. Cada regra vem de um item BLOCKER ou MAJOR de um especialista `review-*` e aponta a origem.

## 1. Como carregar

Carregue nesta ordem e aplique tudo junto:

1. `core.md`: sempre.
2. `domains/<domínio>.md`: pela tabela abaixo, a partir dos arquivos que a tarefa vai tocar.
3. `~/.claude/code-guard/learned/global.md`, se existir.
4. Overlay da empresa: `python3 ~/.claude/skills/code-guard/scripts/overlay.py match <repo>`. Com resultado:
   - leia `<dir>/<file>` (regras da empresa);
   - leia `~/.claude/code-guard/learned/<learned>`, se existir;
   - carregue a skill `<skill>` pelo Skill tool.
5. `~/.claude/code-guard/learned/repo-<basename do repo>.md`, se existir.

| Domínio | Carregue quando a tarefa toca |
|---|---|
| `front`, `a11y`, `ux` | componentes, páginas, estilos, JSX/TSX |
| `contratos` | controllers, rotas, DTOs, schemas (zod, class-validator, Pydantic), OpenAPI, clients HTTP, eventos de fila, props host→remote |
| `queries` | ORM, SQL, repositories, handlers que tocam banco, cache, chamadas HTTP em sequência |
| `migrations` | diretório de migrations ou schema do ORM |
| `resiliencia`, `observabilidade` | código server-side (Nest, Express, workers, consumers) ou client HTTP |
| `ia` | SDK de LLM, arquivos de prompt, MCP |
| `modularidade`, `arquitetura` | arquivo ou módulo novo, import novo entre módulos, dependência nova, padrão novo, mais de ~10 arquivos |

Registre os domínios carregados. O /dev passa essa lista ao ledger (`--loaded-domains`).

## 2. Prioridade em conflito

`CLAUDE.md` do repo > skill da empresa > overlay da empresa > learned do repo > learned da empresa > learned global > domínio > núcleo.

Regra aprendida com a mesma origem (`review-x/categoria`) de uma regra do núcleo ou de domínio substitui a original.

## 3. Antes de entregar

0. Checagens determinísticas do diff (régua afrouxada e checagens aprendidas), zero achado:
   `python3 ~/.claude/skills/code-guard/scripts/diff_checks.py run --repo . --base <branch base> --uncommitted`
1. Type-check, lint e testes só dos arquivos tocados e dos consumidores diretos, via trava de processo pesado e com workers limitados:
   `~/.claude/skills/dev/scripts/heavy_lock.sh npx vitest run <arquivos> --maxWorkers=2`
2. Tela alterada: siga o fluxo real de cliques nas três telas, iPhone SE (375×667), depois tablet (768×1024) e depois desktop (1280×720), e olhe os prints:
   `python3 ~/.claude/skills/master-review/scripts/mobile_flow.py --url <url> --out <dir> --device iphone-se --steps <steps.json>`
   O Chrome headless não abre janela com menos de 500 px. Print de `--window-size=375` sai cortado. Use sempre o `mobile_flow.py`.
3. Mudança de comportamento: a /test-audit (Mode A) vem antes do código.

## 4. Ciclo de aprendizado

A master-review grava todo BLOCKER e MAJOR confirmado em `~/.claude/code-guard/ledger.jsonl` (com a evidência literal e o nível de prova) e depois chama:

```bash
python3 ~/.claude/skills/code-guard/scripts/ledger.py triggers
```

Para cada trigger (mesma identidade `especialista:categoria`, 3 ocorrências, 2 tasks ou mais), suba na hierarquia de imposição. Use o primeiro nível que pega o erro:

1. **Checagem automática** (o erro aparece como padrão numa linha: supressão, API proibida, import, literal, chamada perigosa). Escreva a regex e registre:
   ```bash
   python3 ~/.claude/skills/code-guard/scripts/diff_checks.py add-check --id <id> --pattern '<regex>' --files '<regex de arquivo>' \
     --message "<o que está errado>" --origin review-x/categoria --identity <identidade do trigger>
   ```
   O script recusa a checagem se ela não disparar em nenhuma ocorrência real do ledger. A checagem roda em todo `diff_checks.py run`, sem token. Registre também a linha de texto com `· impõe: check:<id>`.
2. **Tipo ou lint do repo**: quando a correção certa é uma regra de lint ou um tipo no próprio repo, não edite a config do repo. Proponha a regra no MR e registre a linha de texto com `· impõe: lint:<regra>` ou `· impõe: tipo` só depois que o repo adotar.
3. **Texto** (só o que pede julgamento): linha em `learned/` com `· impõe: texto`.

Depois do nível escolhido:

- Procure regra parecida (origem igual ou texto equivalente) no núcleo, nos domínios e em `learned/`. Reescreva em vez de duplicar.
- `domain_loaded` falso: o roteamento falhou. Corrija a tabela da seção 1 (`learned/global.md` registra a correção até ela entrar no repo).
- `escalate` verdadeiro: a regra já existia só como texto e o erro voltou. Tente o nível 1. Se o erro não cabe numa regex, reescreva a regra mais concreta, com as ocorrências reais como exemplo.
- Destino do texto: genérica → `learned/global.md`; de empresa (o repo tem overlay) → `learned/company-<nome>.md`; de um repo só → `learned/repo-<nome>.md`. Nunca edite os arquivos versionados desta skill: promover regra para o repo é tarefa manual do Marcelo.
- `python3 ~/.claude/skills/code-guard/scripts/check_budget.py ~/.claude/skills/code-guard --learned ~/.claude/code-guard/learned`. Acima do teto: consolide regras parecidas. Nunca remova regra de categoria que gera BLOCKER.
- `python3 ~/.claude/skills/code-guard/scripts/ledger.py mark-processed --identity <id> --action created|rewritten|routing`.
- Com feature ativa do /dev: `devstate.py decision <feature_dir> '{"id":"…","text":"regra …","origin":"code-guard"}'`.

A retro do fim de feature (`/dev`) também propõe checagens e regras sem efeito. Trate cada proposta de checagem pelo nível 1 acima.

## 5. Formato das regras

- Linha de regra: `- [PREFIXO] Diretriz no imperativo. — origem: review-<tema>/<categoria>`.
- Regra aprendida acrescenta `· ocorrências: N · impõe: texto|check:<id>|lint:<regra>|tipo`.
- Tetos: `core.md` 150 linhas, cada domínio 120, cada `learned/*.md` 80. O `check_budget.py` confere teto e origem.
