# cunha-harness

Skills do Claude Code do Marcelo Cunha. Uma pasta por skill.

## Instalar

```bash
./install.sh --dry-run   # mostra o que muda
./install.sh             # cria um symlink de cada pasta em ~/.claude/skills/
```

O `install.sh` nunca apaga. Pasta existente em `~/.claude/skills/` vai para `~/.claude/skills-backup/<data>/` antes do symlink.

## Skills

| Skill | O que faz |
|---|---|
| `dev` | Pipeline de desenvolvimento: requisitos, grafo de tasks, 4 workers, gates, pausa e retomada. |
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
