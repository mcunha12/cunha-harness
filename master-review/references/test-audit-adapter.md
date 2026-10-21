# Adapter: test-audit → output contract

A skill `test-audit` (`~/.claude/skills/test-audit/SKILL.md`) não é modificada. Ela devolve prosa com veredito por teste. O orquestrador converte assim. Prefixo de id: `TST`.

| Saída da test-audit | severity | category | auto_fixable |
|---|---|---|---|
| Comportamento novo sem teste nenhum no diff | MAJOR | sem-teste | false |
| Bugfix sem teste que reproduz o bug | MAJOR | bugfix-sem-repro | false |
| Fixture com nome, CPF, e-mail, telefone ou endereço real | BLOCKER | PII-em-fixture | true |
| Tautological | MINOR | tautologico | true (deletar) |
| Change-detector | MINOR | change-detector | true (deletar) |
| Regression without gap | MINOR | regressao-sem-lacuna | true (deletar) |
| Dead | MINOR | teste-morto | true (deletar) |
| Unit outside the exception | MINOR | unit-fora-da-excecao | false |
| Testes vieram depois da implementação (ordem dos commits) | NIT | ordem-commits | false |
| Behavior | não vira achado | — | — |

- `evidence`: o nome do teste (`describe > it`) e as linhas que justificam o veredito.
- `problem`: a linha de motivo da test-audit.
- `fix`: "deletar o caso X de arquivo:linhas" ou o teste de comportamento que falta, com o caso da spec.
- `confidence`: alta quando a test-audit cita o código; media no resto.
- Tasks de categoria `sem-teste` e `bugfix-sem-repro` vão para fixer com `changes_behavior=sim`, que segue o Mode A da test-audit.
