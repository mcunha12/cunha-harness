# Code review — <repo> · <branch> → <base> · <YYYY-MM-DD HH:MM>

**Veredito: BLOQUEAR | APROVAR COM RESSALVAS | APROVAR**

<3-5 linhas: o que o diff faz, quantos achados confirmados, o que bloqueia.>

| Agente | BLOCKER | MAJOR | MINOR | NIT |
|---|---|---|---|---|

## BLOCKER
### `<arquivo>`
#### SEG-001 — <título> · review-seguranca (+ review-contratos)
**Linhas:** 42-58 · **Confiança:** alta · **Verificação:** confirmado · **Prova:** nível 4 (script `<run>/proofs/SEG-001.sh`)
**Evidência:**
```ts
```
**Problema:** ...
**Correção:**
```diff
```

## MAJOR
## MINOR

<details><summary>NITs (n)</summary>
</details>

## Spec
| Achado | Tipo | Linha da spec | Diff | Verificação |
|---|---|---|---|---|
Tipos: faltando, a mais, errado.

## Lacunas
Especialistas que falharam duas vezes no contrato. Cada lacuna limita o veredito a APROVAR COM RESSALVAS.

## Roast
Uma linha por crítica do review-roast que sobreviveu à verificação: id, arquivo:linhas, crítica, motivo e consequência. Críticas descartadas por contradizer convenção documentada vão em `<details>` com o motivo.

## Trade-offs
| Trecho | Agente A pede | Agente B pede | Decisão |
|---|---|---|---|

## Débito pré-existente (máx. 5)

## Agentes
| Agente | Status | Motivo |
|---|---|---|

## Handoffs não resolvidos

## Verificação dos BLOCKER/MAJOR
| Achado | Resultado | Motivo |
|---|---|---|

## Correção
| Task | Achados | Status | Verificação |
|---|---|---|---|

Tasks manuais: ...
Type-check: ... · Lint: ... · Testes: ...
