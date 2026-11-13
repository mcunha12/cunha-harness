# cunha-harness

Skills do Claude Code do Marcelo Cunha. Uma pasta por skill.

## Instalar

```bash
./install.sh --dry-run   # mostra o que muda
./install.sh             # cria um symlink de cada pasta em ~/.claude/skills/
```

O `install.sh` nunca apaga. Pasta existente em `~/.claude/skills/` vai para `~/.claude/skills-backup/<data>/` antes do symlink.

### Dependências da /dev

O `install.sh` instala cada uma pelo instalador oficial, só se ainda não existe. Pré-requisito: Node.js e a CLI `claude`.

| Dependência | Para quê | Comando que o script roda |
|---|---|---|
| Impeccable | propostas de UI, task de UI, `detect` no gate | `npx impeccable install` |
| Superpowers | `systematic-debugging` na investigação de bug | `claude plugin install superpowers@claude-plugins-official` |
| agent-browser | QA e `review-ux` nas 3 telas | `npm i -g agent-browser` |

Flags: `--sem-deps` pula as 3. `--sem-impeccable` pula só o Impeccable. Para atualizar o Impeccable: `npx impeccable update`.

## Skills

| Skill | O que faz |
|---|---|
| `dev` | Pipeline de desenvolvimento: requisitos, um plano por feature, até 3 tasks em paralelo, testes e gate único com QA no fim (lean por padrão), Impeccable quando o repo tem setup, pausa e retomada. |
| `retro` | Retro de uma feature do `/dev`, só quando chamada. |
| `master-review` | Swarm de code review pós-código. Modos full e `--lean`, roast opcional. |
| `code-guard` | A master-review como diretriz de escrita, usada durante a implementação. Aprende com erros repetidos. |
| `review-*` | Especialistas da master-review, um tema cada. |
| `test-audit` | Spec e testes antes do código; gate de conferência antes do MR. |

## Dados fora do repo

- `~/.claude/overlays/`: regras de empresa, `overlays.json` (qual overlay vale para qual remote) e `forbidden-terms.txt`.
- `~/.claude/code-guard/`: ledger de achados e regras aprendidas.
- `~/.claude/dev/`: estado das features.

## Regra do repo

O repo é público. Nenhum arquivo, nome de arquivo ou mensagem de commit contém termo de `~/.claude/overlays/forbidden-terms.txt`. Os hooks versionados em `.githooks/` (pre-commit e commit-msg) rodam `scripts/check-anonymized.sh`. O `./install.sh` liga esses hooks na clone (`core.hooksPath`).

Testes: `python3 -m unittest <arquivo de teste>`.
