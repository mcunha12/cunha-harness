---
name: review-seguranca
description: Revisa segurança de um diff com OWASP Top 10 e OWASP API Security Top 10 2023 (BOLA/IDOR, authN/authZ, injeção, XSS, SSRF, segredos, crypto, abuso, supply chain, LGPD). Acione em "revisa a segurança desse PR", "tem vulnerabilidade nesse diff?", `/review-seguranca` ou via master-review. Não cobre prompt injection e output de LLM (review-ia), PII em logs (review-observabilidade), performance de query (review-queries), timeouts e retry (review-resiliencia), shape de contrato (review-contratos) nem acessibilidade.
argument-hint: "[--base <branch>] [--path <glob>] [--uncommitted]"
---

# review-seguranca

## Missão

Encontrar no diff vulnerabilidades que um atacante explora com acesso real ao sistema: acesso a dado de outro tenant, escalada de privilégio, injeção, execução de script no navegador do aluno, vazamento de segredo e abuso que gera custo. Cada achado traz o sinal no código, o cenário de exploração e a correção em código. O agente reporta só o que o diff introduziu ou tocou. Zero achados é resultado válido.

## Escopo

Cada item segue o formato sinal, impacto, correção. Os detalhes por tecnologia ficam em `references/`.

### 1. AuthN e AuthZ (API1, API2, API3, API5 de 2023)

- **BOLA/IDOR.** Sinal: handler recebe `:id`, `turmaId`, `matriculaId` ou `userId` de params, query ou body e busca o recurso só por esse id (`findUnique({ where: { id } })`). Impacto: qualquer usuário autenticado lê ou altera recurso de outro aluno, turma ou tenant. Correção: filtrar a query pelo dono (`where: { id, alunoId: user.id }`) ou checar ownership/tenant antes de devolver. Verifique também ids aninhados (`/turmas/:t/alunos/:a`): o `a` pertence ao `t`?
- **BFLA.** Sinal: rota administrativa ou de professor sem guard de role, ou guard aplicado só ao controller vizinho. Impacto: aluno chama operação de professor. Correção: guard de role/permissão declarado na rota, com deny por padrão.
- **Mass assignment.** Sinal: `repo.update(id, req.body)`, `prisma.x.update({ data: body })`, spread de DTO sem whitelist, `class-validator` sem `whitelist: true`/`forbidNonWhitelisted`. Impacto: cliente grava `role`, `isAdmin`, `tenantId`, `preco`. Correção: DTO de entrada com campos explícitos e mapeamento campo a campo.
- **AuthZ só no front.** Sinal: botão escondido por role no client sem checagem equivalente na rota consumida. Impacto: chamada direta à API ignora o front. Correção: checagem no servidor.
- **Rota nova pública.** Sinal: decorator `@Public()`, `skipAuth`, rota registrada antes do middleware de auth, allowlist de rotas ampliada. Impacto: endpoint sem autenticação. Correção: remover o bypass ou justificar com comentário e restringir o payload.
- **JWT e sessão.** Sinal: `jwt.verify` sem `algorithms`, `jwt.decode` usado como validação, `ignoreExpiration: true`, segredo curto ou fixo, `alg: none` aceito, token em `localStorage`, `exp` longo sem refresh, claims confiadas sem checar `aud`/`iss`. Impacto: forja de token ou roubo via XSS. Correção: `verify` com `algorithms: ['RS256']` e `audience`/`issuer`; cookie `httpOnly; Secure; SameSite` quando o repo controla a sessão. Se o repo usa IdP gerenciado (Cognito, Auth0), confirme o padrão local antes de reportar storage.
- **CSRF.** Sinal: autenticação por cookie com rota mutante sem token CSRF nem `SameSite=Lax/Strict`. Impacto: site de terceiro dispara ação em nome do aluno. Correção: `SameSite`, token anti-CSRF ou header customizado verificado. Auth por `Authorization: Bearer` não sofre CSRF.
- **CORS.** Sinal: `origin: '*'` com `credentials: true`, `origin` refletindo o header `Origin` sem allowlist, regex de origem sem âncora (`/acme.com/`). Impacto: site malicioso lê resposta autenticada. Correção: allowlist exata por ambiente.
- **Enumeração e recuperação de conta.** Sinal: mensagens distintas para "usuário não existe" e "senha errada", token de reset previsível ou sem expiração, sem lockout. Correção: mensagem única, token aleatório de uso único com TTL.

### 2. Injeção (A03)

- **SQL.** Sinal: `$queryRawUnsafe`, `$executeRawUnsafe`, template string em `query()`, `sequelize.query` com concatenação, `ORDER BY ${req.query.sort}`. Impacto: leitura/escrita arbitrária no banco. Correção: parâmetros (`$queryRaw` com tagged template, `$1`), allowlist para nome de coluna e direção de ordenação.
- **NoSQL e operador.** Sinal: `find({ email: req.body.email })` com objeto não validado. Impacto: `{ "$ne": null }` contorna filtro. Correção: validar tipo string no DTO.
- **Command injection.** Sinal: `exec`, `execSync`, `spawn(..., { shell: true })`, `os.system`, `subprocess(..., shell=True)` com input. Correção: `execFile`/`spawn` com array de argumentos, sem shell.
- **SSRF (API7).** Sinal: `axios.get(req.body.url)`, `fetch(url)` com URL vinda do usuário, webhook configurável, download de imagem por URL, proxy de PDF. Impacto: alcance a `169.254.169.254` (metadata de cloud), serviços internos, `localhost`. Correção: allowlist de host, resolver DNS e bloquear IP privado/link-local/loopback depois da resolução, `maxRedirects: 0`, timeout.
- **Path traversal.** Sinal: `path.join(base, req.params.file)`, `readFile(userInput)`, `res.sendFile`, extração de zip sem checar entradas. Correção: `path.resolve` e conferir `startsWith(base + path.sep)`, rejeitar `..`, validar nome por regex.
- **Template, header e log injection.** Sinal: `res.setHeader(k, userInput)`, `Location` com input, template server-side com string do usuário, log com `\n` do usuário. Correção: validar charset, remover CR/LF, usar template com autoescape.
- **Prototype pollution.** Sinal: `merge`/`extend`/`set` profundo com chave do usuário, `obj[key][sub] = v` com `key` externo, `Object.assign` recursivo. Impacto: `__proto__` altera comportamento global. Correção: bloquear `__proto__`/`constructor`/`prototype`, `Object.create(null)`, `Map`.
- **Desserialização insegura.** Sinal: `pickle.loads`, `yaml.load` sem SafeLoader, `eval`, `new Function`, `vm.runInNewContext` com input. Correção: formato de dados puro (JSON) com schema.
- **Redirect aberto.** Sinal: `res.redirect(req.query.next)`, `window.location = param`. Correção: allowlist de destino ou só path relativo.

### 3. XSS e superfície do navegador (A03, A05)

- Sinal: `dangerouslySetInnerHTML`, `innerHTML`, `outerHTML`, `document.write`, `insertAdjacentHTML`, `v-html`, `bypassSecurityTrust*`, `href`/`src` com string do usuário (`javascript:`), Markdown renderizado com `rehype-raw` sem `rehype-sanitize`, HTML vindo de CMS ou de LLM. Impacto: script roda na origem da aplicação e lê token do `sessionStorage`. Correção: sanitizar com DOMPurify/`rehype-sanitize` com schema restrito, validar esquema de URL (`https:`, `mailto:`), renderizar como texto.
- `target="_blank"` sem `rel="noopener noreferrer"` em link externo de conteúdo de usuário.
- `postMessage` sem checagem de `event.origin`, `targetOrigin: '*'` com dado sensível. Relevante para WebView e Module Federation.
- Ausência ou afrouxamento de CSP (`unsafe-inline`, `unsafe-eval`, `*`) em `nginx.conf`, helmet ou meta tag, quando o diff mexe nesses arquivos.
- Iframe de terceiro sem `sandbox`.

### 4. Segredos e configuração (A02, A05)

- Sinal: string com formato de chave (`sk-`, `AKIA`, `ghp_`, `glpat-`, `xox[bp]-`, JWT, `-----BEGIN PRIVATE KEY`), `password = "..."`, `.env` ou `.npmrc` com token versionado, `docker-compose` com senha real, `Dockerfile` com `ARG TOKEN` que vai para a layer.
- Variável pública de bundle com segredo: `NEXT_PUBLIC_*`, `VITE_*`, `REACT_APP_*`, `window.env` injetado no client por `env-config.js`. Tudo que o bundle recebe é público. Impacto: chave de LLM, token de serviço ou URL interna no navegador de qualquer visitante. Correção: mover a chamada para o servidor e expor só um endpoint próprio.
- Impacto de segredo commitado: a rotação é obrigatória, remover do HEAD não basta. Escreva isso no `fix`.
- Config insegura: `NODE_TLS_REJECT_UNAUTHORIZED=0`, `rejectUnauthorized: false`, `verify=False`, `DEBUG=True`, Swagger/GraphQL playground/introspection aberto em prod, `helmet` removido.

### 5. Dados e LGPD (A01, API3)

- **Excessive data exposure.** Sinal: `return user` ou `return entity` com `passwordHash`, `cpf`, `email`, `notas`, flags internas; `select` ausente; serialização automática de entidade ORM. Correção: DTO de resposta explícito (`@Exclude`/`class-transformer`, `select`).
- **Minimização.** Sinal: endpoint novo devolve CPF, data de nascimento ou dado de saúde sem necessidade comprovada no caller. Correção: remover o campo ou mascarar.
- **Erro vazando internals.** Sinal: `res.status(500).json({ error: err.stack })`, mensagem do ORM com nome de tabela ao cliente, `DEBUG` em prod. Correção: erro genérico com correlation id e log no servidor.
- **Dado sensível em URL.** Sinal: token, CPF ou e-mail em query string. Impacto: vai para access log, Referer e histórico. Correção: header ou body.
- Dado pessoal em log ou telemetria: handoff para review-observabilidade.

### 6. Criptografia (A02)

- Hash de senha com `md5`, `sha1`, `sha256` simples ou bcrypt com cost < 10. Correção: argon2id ou bcrypt cost ≥ 12.
- `Math.random()`, `random.random()`, `uuid v1` ou `Date.now()` como token, código de reset, nonce ou id de sessão. Correção: `crypto.randomBytes(32)`, `crypto.randomUUID()`, `secrets.token_urlsafe`.
- Comparação de segredo, HMAC ou token com `===`/`==`. Correção: `crypto.timingSafeEqual` (compare o tamanho antes), `hmac.compare_digest`.
- Cifra com ECB, IV fixo ou reutilizado, chave derivada de string literal, `createCipher` (depreciado). Correção: AES-256-GCM com IV aleatório por mensagem.
- TLS desligado, URL `http://` para serviço com credencial.

### 7. Abuso e disponibilidade (API4, API6, API8)

- **Rate limit ausente** em login, reset de senha, OTP, criação de conta, envio de e-mail/SMS e endpoint que chama LLM (cada chamada tem custo em dinheiro). Correção: `@nestjs/throttler`, `express-rate-limit` ou limite no gateway, chave por usuário e por IP.
- **Fluxo sensível sem proteção de negócio.** Sinal: cupom, resgate, nota, inscrição sem limite por usuário nem idempotência. Impacto: automação em massa.
- **Upload.** Sinal: `multer` sem `limits`, validação só por `Content-Type` ou extensão, arquivo salvo com nome original, servido do mesmo domínio da app, SVG/HTML aceito. Correção: limite de tamanho, checagem de magic bytes, nome gerado, bucket separado com `Content-Disposition: attachment`.
- **Paginação sem teto.** Sinal: `limit` do cliente sem máximo. Impacto: dump completo da tabela. Correção: `Math.min(limit, 100)`.
- **Webhook.** Sinal: endpoint de webhook sem verificação de assinatura (HMAC com secret, timestamp e tolerância) ou sem proteção contra replay. Correção: verificar sobre o raw body com `timingSafeEqual`.
- **ReDoS.** Sinal: regex com quantificador aninhado (`(a+)+`, `(.*)*`, alternância sobreposta) aplicada a input do usuário. Correção: regex linear, limite de tamanho do input, `re2`.
- **Consumo de recursos.** Sinal: parse de JSON/XML sem limite de body, `express.json()` com `limit` elevado, zip bomb, GraphQL sem depth/complexity limit.

### 8. Supply chain (A06, A08)

- Dependência nova no diff: confira nome (typosquatting: `lodahs`, `reqeusts`), downloads, último release, mantenedor, licença incompatível, `postinstall`/`preinstall` em `package.json` do pacote.
- Lockfile alterado sem mudança em manifesto, `resolved` apontando para URL fora do registry, `integrity` removido.
- Dependência por git URL ou tarball sem hash. Versão `latest` ou `*`.
- Registry privado: `.npmrc` com token no repo. Escopo `@org` fora do registry da empresa (dependency confusion).
- CI: `curl | sh`, action de terceiro sem pin por SHA, `pull_request_target` com checkout de código do fork.
- Downgrade de versão com CVE conhecido.

### 9. Infra como código e container (A05)

- `Dockerfile` rodando como root, `latest` como base, `COPY . .` incluindo `.env`, porta de debug exposta.
- `nginx.conf` sem `server_tokens off`, sem headers de segurança, `autoindex on`, `proxy_pass` com variável do usuário.
- Bucket/S3 público, Security Group `0.0.0.0/0` em porta de banco, IAM com `*:*`.

## Fora de escopo, com dono

| Tema | Dono |
|---|---|
| Prompt injection, output do LLM sem sanitização, excessive agency, RAG multi-tenant | review-ia |
| PII em log, telemetria e analytics | review-observabilidade |
| Performance de query, índice, N+1 | review-queries |
| Timeout, retry, idempotência de job | review-resiliencia |
| Breaking change de contrato, validação de shape entre serviços | review-contratos |
| Contraste, teclado, ARIA | review-a11y |
| Tipo `any`, `as` mentiroso | review-tipagem |
| Testes de segurança ausentes | test-audit |

Registre o handoff com `{ "to": "...", "location": "arquivo:linhas", "note": "uma linha" }` e siga. Se o sinal toca duas áreas (por exemplo `rehype-raw` com saída de LLM), o XSS é seu. A origem LLM vai em handoff para review-ia.

## Processo

1. Leia os 4 arquivos de `~/.claude/skills/master-review/references/`: `output-contract.md`, `severity-rubric.md`, `review-rules.md`, `ownership-matrix.md`.
2. Detecte a stack pela tabela de `review-rules.md`. Leia `references/generic.md` sempre. Leia só os references que batem: `typescript.md`, `react.md`, `nestjs.md`, `node.md`, `prisma-postgres.md`, `python.md`.
3. Obtenha o diff. Se o orquestrador enviou um context packet, use-o. Standalone, detecte a base (`main`, `master`, `develop`) e rode `git diff $(git merge-base <base> HEAD)...HEAD`. Com `--uncommitted`, inclua `git diff HEAD` (staged e unstaged) e arquivos novos não rastreados. Com `--path`, restrinja ao glob.
4. Mapeie a superfície de ataque do diff: toda entrada externa (rota, handler de fila, webhook, query param, `postMessage`, arquivo, variável de ambiente) e todo sink (query, exec, HTML, redirect, fetch de URL, escrita de arquivo, resposta ao cliente).
5. Para cada entrada, siga o dado até o sink. Para cada sink, volte até a origem.
6. Verifique o contexto antes de reportar. Abra o caller e o callee. Procure o guard global (`APP_GUARD`, middleware, interceptor, `ValidationPipe` global, `helmet`, gateway) que já cobre o caso. Leia o schema do ORM para saber quem é dono do recurso.
7. Classifique pela rubrica abaixo e pela rubrica global. Calcule a confiança.
8. Emita no output contract: bloco JSON, depois markdown. Prefixo `SEG`. Máximo de ~15 achados, ordenados por severidade e confiança.
9. Standalone: mostre o markdown ao final. Não altere código.

Quando o `evidence` for um segredo, mascare o valor (`sk-proj-****abcd`) no JSON e no markdown.

## Rubrica de severidade

**BLOCKER**
- Rota `GET /turmas/:id/notas` busca `where: { id }` sem filtro de dono. Qualquer aluno logado lê as notas de qualquer turma.
- `$queryRawUnsafe(`... WHERE email = '${email}'`)` com `email` do body.
- Chave de provedor (LLM, cloud, banco) ou token de CI commitado no diff, ou lido de `window.env` no client.

**MAJOR**
- Endpoint de IA ou de envio de e-mail sem rate limit, com custo por chamada.
- `rehype-raw` sem `rehype-sanitize` em Markdown de usuário. Vira BLOCKER se a origem do HTML for conteúdo de terceiros e o token de sessão estiver em storage legível por script.
- Webhook sem verificação de assinatura.
- `update(id, req.body)` sem whitelist em entidade com campo privilegiado.

**MINOR**
- `target="_blank"` sem `rel="noopener"` em link de conteúdo próprio.
- Resposta devolve campo extra inofensivo (`createdAt` interno) sem necessidade.
- `Math.random()` para id de elemento de UI.

**NIT**
- CSP poderia remover `unsafe-inline` de `style-src` num repo sem CSP hoje.

Regras do tema: BLOCKER exige exploração demonstrável com o diff (origem controlável, sink alcançável, sem guard no caminho). Sem isso, MAJOR com confiança `media` e a condição que confirmaria no `problem`.

## Heurísticas anti-falso-positivo

- Guard global. `APP_GUARD` de auth, `ValidationPipe({ whitelist: true })` global ou interceptor de tenant já cobrem a rota. Abra `main.ts` e `app.module.ts` antes de reportar auth ausente ou mass assignment.
- Ownership em outra camada. O service recebe o `user` e aplica o filtro, o controller só repassa o id. Siga a chamada.
- Dado público por natureza (catálogo de cursos, página institucional). Falta de authZ é intencional.
- `dangerouslySetInnerHTML` com string literal do próprio código ou saída já sanitizada no mesmo fluxo. Confirme a origem.
- `$queryRaw` com tagged template. O Prisma parametriza. Reporte só `Unsafe` ou `Prisma.raw` com input.
- `Math.random` em jitter de retry, animação, amostragem de analytics.
- Segredo falso: fixture de teste, `.env.example`, placeholder (`changeme`, `xxx`), hash de commit, `id` público de projeto de analytics (PostHog `phc_`, Mixpanel token de projeto, Sentry DSN público).
- Chave `VITE_`/`window.env` com valor público por design (URL do BFF, chave de feature flag client-side, token de analytics).
- Token no `sessionStorage` com Cognito/Auth0 SDK. É o padrão do SDK. Reporte só se o diff adicionar leitura insegura (log, `postMessage`, innerHTML).
- Rota interna atrás de rede privada, job ou CLI sem entrada de usuário.
- Teste, mock, story e script de seed. Reporte segredo real mesmo neles. Ignore o resto.
- Dependência `devDependencies` com `postinstall` conhecido e legítimo (husky, esbuild, prisma, sharp).

## Ferramentas determinísticas opcionais

Rode só se já estiverem instaladas. Nunca instale. A saída é insumo, não veredito.

| Ferramenta | Checagem | Execução |
|---|---|---|
| semgrep | `command -v semgrep` | `semgrep --config auto --error --quiet --json <arquivos do diff>` |
| gitleaks | `command -v gitleaks` | `gitleaks detect --no-banner --redact --log-opts "<base>..HEAD"` ou `gitleaks protect --staged --redact` |
| trufflehog | `command -v trufflehog` | `trufflehog git file://. --since-commit <base> --only-verified --json` |
| yarn audit | `test -f yarn.lock` | `yarn audit --groups dependencies --level high` (Yarn 1) ou `yarn npm audit --severity high` (Yarn Berry) |
| npm audit | `test -f package-lock.json` | `npm audit --omit=dev --audit-level=high --json` |
| pnpm audit | `test -f pnpm-lock.yaml` | `pnpm audit --prod --audit-level high` |
| pip-audit | `command -v pip-audit` | `pip-audit -r requirements.txt` |
| bandit | `command -v bandit` | `bandit -r <dirs> -ll -f json` |

Regras: audit só vale se o diff tocou manifesto ou lockfile. Transforme cada resultado em achado só depois de confirmar que o código do repo chama o caminho vulnerável. CVE em dependência de dev sem execução em produção é MINOR.

## Exemplos

### Achado 1: BOLA

```json
{
  "id": "SEG-001",
  "agent": "review-seguranca",
  "severity": "BLOCKER",
  "confidence": "alta",
  "category": "BOLA/IDOR",
  "location": { "repo": "exemplo-api", "file": "src/turmas/turmas.controller.ts", "lines": "34-41" },
  "evidence": "@Get(':id/notas')\nasync notas(@Param('id') id: string) {\n  return this.prisma.nota.findMany({ where: { turmaId: id } });\n}",
  "problem": "A rota autentica o usuário e não confere se ele pertence à turma. Qualquer aluno logado lê as notas de qualquer turma trocando o id na URL. Nenhum guard global de tenant existe (app.module.ts só registra JwtAuthGuard).",
  "fix": "const matricula = await this.prisma.matricula.findFirst({ where: { turmaId: id, alunoId: user.id } });\nif (!matricula) throw new NotFoundException();\nreturn this.prisma.nota.findMany({ where: { turmaId: id, alunoId: user.id } });",
  "auto_fixable": false,
  "effort": "S",
  "refs": ["OWASP API1:2023"],
  "introduced_by_diff": true
}
```

```
### [BLOCKER] SEG-001 — Notas da turma sem checagem de dono
**Onde:** exemplo-api/src/turmas/turmas.controller.ts:34-41 · **Confiança:** alta · **Esforço:** S
**Evidência:** findMany({ where: { turmaId: id } }) com id vindo da URL
**Problema:** qualquer aluno autenticado lê as notas de qualquer turma.
**Correção:** filtrar por matrícula do usuário (código acima). Devolva 404 para ocultar a existência.
```

### Achado 2: segredo no bundle

```json
{
  "id": "SEG-002",
  "agent": "review-seguranca",
  "severity": "BLOCKER",
  "confidence": "alta",
  "category": "Segredo no bundle",
  "location": { "repo": "exemplo-web", "file": "src/services/ai.ts", "lines": "8-15" },
  "evidence": "const client = new OpenAI({ apiKey: window.env.OPENAI_API_KEY, dangerouslyAllowBrowser: true });",
  "problem": "window.env é entregue ao navegador por /env-config.js. Qualquer visitante lê a chave e consome a cota da empresa. A chave exposta precisa de rotação, mesmo depois de remover o código.",
  "fix": "Remova a chave do client e chame um endpoint do servidor: const res = await api.post('/ia/resumo', { texto }); No servidor, leia a chave de process.env e aplique rate limit por usuário. Rotacione OPENAI_API_KEY.",
  "auto_fixable": false,
  "effort": "M",
  "refs": ["OWASP A02:2021", "OWASP API8:2023"],
  "introduced_by_diff": true
}
```

### Caso que não se reporta

O diff adiciona `@Get('cursos') findAll() { return this.prisma.curso.findMany() }` sem filtro de usuário. Parece BOLA. O catálogo de cursos é conteúdo público: o controller já está sob `@Public()` por decisão registrada no README e a resposta usa `select` só com `id`, `titulo` e `slug`. Nenhum dado de aluno trafega. Não reporte. Se o diff incluísse `select` com preço promocional por usuário, a conclusão mudaria.
