# Output contract

Todo especialista devolve exatamente duas partes, nesta ordem:

1. Um bloco ```json com o objeto de resultado (merge por máquina).
2. A versão legível em markdown dos mesmos achados.

O orquestrador lê só o JSON. O markdown serve ao uso standalone.

## Objeto de resultado

```json
{
  "agent": "review-seguranca",
  "summary": "2-3 linhas: o que foi revisado e o veredito do tema.",
  "files_reviewed": ["src/routes/turmas.ts"],
  "skipped_reason": null,
  "stack_references_loaded": ["typescript.md", "nestjs.md"],
  "findings": [],
  "handoffs": [],
  "preexisting_debt": []
}
```

- `skipped_reason`: string quando não havia nada no escopo do agente. Nesse caso `findings` fica vazio.
- `findings`: no máximo ~15, ordenados por severidade × confiança.
- `handoffs`: `{ "to": "review-queries", "location": "arquivo:linhas", "note": "uma linha" }`. Não desenvolver.
- `preexisting_debt`: no máximo 3 itens, fora do diff. Mesmo schema do achado, com `introduced_by_diff: false`.

## Schema do achado

```json
{
  "id": "SEG-003",
  "agent": "review-seguranca",
  "severity": "BLOCKER | MAJOR | MINOR | NIT",
  "confidence": "alta | media | baixa",
  "category": "taxonomia do agente, ex.: BOLA/IDOR",
  "location": { "repo": "nome-do-diretorio-do-repo", "file": "src/routes/turmas.ts", "lines": "42-58" },
  "evidence": "trecho exato do código que comprova o problema",
  "problem": "impacto concreto: o que quebra, para quem, em que condição",
  "fix": "correção concreta, com diff/código sempre que possível",
  "auto_fixable": true,
  "effort": "S | M | L",
  "refs": ["OWASP API1:2023"],
  "introduced_by_diff": true
}
```

Regras de preenchimento:

- `id`: prefixo do agente + número sequencial. Prefixos: DRY, CLN, MOD, FRT, A11Y, CTR, TIP, LEG, QRY, SEG, COM, RES, OBS, IA, MIG, TST, ARQ, UX, ROAST, SPEC, CHK.
- Campos que o orquestrador acrescenta no passo 8: `verification` (`confirmado` | `rebaixado para <nível>` | `descartado`) e `proof_level` (1 a 5).
- `location.repo`: nome do diretório raiz do repo (`basename` do `git rev-parse --show-toplevel`).
- `evidence`: cópia literal do código, sem paráfrase. Máximo ~15 linhas.
- `fix`: código ou diff aplicável. "Considere melhorar" é inválido.
- `auto_fixable: true` só quando o `fix` é um patch local, sem decisão de produto e sem mudança de contrato.
- `confidence: baixa` exige dizer, no `problem`, o que confirmaria o achado.

## Markdown legível

```
### [SEVERIDADE] ID — título curto
**Onde:** repo/arquivo:linhas · **Confiança:** alta · **Esforço:** S
**Evidência:** (bloco de código)
**Problema:** ...
**Correção:** (bloco de código/diff)
```

Zero achados: escreva "Nenhum achado no escopo de <tema>." e o `summary`.
