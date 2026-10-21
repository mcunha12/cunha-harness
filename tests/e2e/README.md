# E2E

`fixture-app/base` é o app limpo. `fixture-app/defects` é o mesmo app com três defeitos plantados:

1. `server.js`: `catch` que engole o erro e devolve `[]` com status 200 (esperado: `RES` MAJOR).
2. `public/index.html`: ação principal "Ativar lembrete" abaixo da primeira dobra em 375×667 (esperado: `UX` MAJOR).
3. `public/index.html`: ternário aninhado (esperado: `LEG` MAJOR).

Como rodar:

```bash
W=$(mktemp -d) && cp -R tests/e2e/fixture-app/base/. "$W" && cd "$W" && git init -q && git add -A && git commit -qm base
git checkout -qb defeitos && cp -R <repo>/tests/e2e/fixture-app/defects/. . && git add -A && git commit -qm defeitos
```

Depois, no diretório `$W`: `/master-review --lean --report-only --base main` (esperado: os 3 achados MAJOR, sem MINOR, sem seção Roast) e `/master-review --lean --roast --report-only --base main` (esperado: seção Roast, toda crítica com motivo). Para a revisão visual: `node server.js` e URL `http://localhost:4321`.
