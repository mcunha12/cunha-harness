# Segurança em Node (runtime, Express, Fastify, Koa e libs comuns)

## Execução e processo

- `child_process.exec`/`execSync` com string montada: injeção de comando. Correção: `execFile(bin, [args])`, sem `shell: true`. Valide o argumento contra allowlist, e prefixe `--` antes de argumentos de usuário para evitar injeção de flag (`git log -- ${ref}`).
- `eval`, `new Function`, `vm.runInThisContext`, `vm.runInNewContext` com input. `vm` não é sandbox de segurança. Correção: parser de dados (JSON) ou `isolated-vm` quando inevitável.
- `require(userInput)`, `import(userInput)`: carrega código arbitrário. Correção: map de nomes permitidos.
- `process.env` repassado a processo filho (`env: process.env`) vaza segredos a binário de terceiros.

## Arquivos e paths

- `fs.readFile(path.join(base, req.params.name))`: traversal com `..%2f`. Correção: `const full = path.resolve(base, name); if (!full.startsWith(base + path.sep)) throw ...`. Resolva symlinks com `fs.realpath` quando o diretório aceita upload.
- `res.sendFile(userPath)`, `express.static` com `dotfiles: 'allow'`, `serve-index` aberto.
- Escrita com nome do usuário: gere nome (uuid), ignore o original. `path.basename` remove diretórios e preserva `..` em nomes especiais, então valide por regex.
- Extração de zip/tar sem checar entradas (`zip slip`): cada `entry.path` resolvido precisa ficar dentro do destino.
- Arquivos temporários com nome previsível em `/tmp`: use `fs.mkdtemp`.

## HTTP server (Express, Fastify, Koa)

- **Ordem de middleware.** `app.use(authMiddleware)` registrado depois das rotas que protege não protege nada. Rota nova acima do middleware de auth é rota aberta.
- **Body e limites.** `express.json({ limit: '50mb' })`, `urlencoded({ extended: true })` com objetos profundos, `bodyParser` sem limit: DoS por memória. Correção: limite por rota, `parameterLimit`.
- **HPP.** `req.query.x` pode ser array (`?x=a&x=b`) ou objeto (`?x[$ne]=1`). Código que chama `.toLowerCase()` no valor quebra com array (500, DoS por exceção não tratada) e passa objeto a queries. Correção: validar tipo com schema (zod, Joi, Ajv).
- **Headers.** `helmet()` ausente. `app.disable('x-powered-by')`. `trust proxy` incondicional permite spoof de `X-Forwarded-For`.
- **Cookies.** `res.cookie` sem `httpOnly`, `secure`, `sameSite` quando guarda sessão. `express-session` com `secret` fraco, `MemoryStore` em produção, `saveUninitialized: true`.
- **CORS.** `cors()` sem opções, `origin: (o, cb) => cb(null, true)`, `origin: /acme/` sem âncora, `credentials: true` com `*`.
- **Erros.** Handler padrão do Express imprime stack em `NODE_ENV !== 'production'`. Confirme `NODE_ENV=production` no deploy. `res.status(500).send(err)` serializa a exceção inteira.
- **Redirect.** `res.redirect(req.query.next)`. Correção: aceite só path relativo que começa com `/` e não com `//`, ou allowlist.
- **Fastify.** Schema JSON por rota valida e remove campos (`removeAdditional`). Rota sem `schema` aceita qualquer coisa. Plugin `@fastify/rate-limit`, `@fastify/helmet`, `@fastify/cors` com opções explícitas.
- **Server-Sent Events/WebSocket.** Upgrade sem autenticação no handshake, sem checagem de `Origin` (CSWSH), sem limite de mensagem (`maxPayload`) e de conexões por usuário.

## Prototype pollution

- Sinal: `_.merge`, `_.set`, `_.defaultsDeep`, `Object.assign` recursivo, `deepmerge`, `qs.parse` com `allowPrototypes`, `obj[a][b] = c` com `a` e `b` do usuário, JSON.parse seguido de merge em config.
- Impacto: `{"__proto__": {"isAdmin": true}}` altera objetos criados depois, em todo o processo. Escala a bypass de autorização e RCE com gadgets de template.
- Correção: rejeitar chaves `__proto__`, `constructor`, `prototype`; `Object.create(null)`; `Map`; atualizar lodash (≥ 4.17.21); `node --disable-proto=delete`.

## ReDoS e CPU

- Regex com quantificadores aninhados ou alternância ambígua sobre input do usuário (`/^(\w+\s?)*$/`, `/(a|aa)+$/`, e-mail regex "completo"). 30 caracteres podem bloquear o event loop por segundos. Correção: regex linear, limite de tamanho (≤ 256) antes de testar, `re2`, validador de biblioteca.
- `JSON.parse` de body grande, `crypto.pbkdf2Sync`, `bcrypt.hashSync`, `zlib.*Sync` em handler: bloqueiam o event loop e viram DoS. Correção: versão assíncrona.
- Handoff para review-queries quando o problema é de performance sem vetor de ataque.

## Crypto no Node

- `crypto.createCipher` (removido), `createCipheriv('aes-256-cbc')` sem MAC, IV fixo. Correção: `aes-256-gcm`, IV de `randomBytes(12)`, guarde `authTag`.
- `crypto.createHash('md5'|'sha1')` para senha ou assinatura. Para ETag ou chave de cache é aceitável.
- `Math.random()` para token/código/ID de segurança. Correção: `crypto.randomBytes(32).toString('base64url')`, `crypto.randomInt(0, 1_000_000)` para OTP.
- Comparação: `crypto.timingSafeEqual(Buffer.from(a), Buffer.from(b))` exige buffers de mesmo tamanho. Compare o `length` antes, caso contrário lança.
- `jsonwebtoken`: `verify(token, secret)` sem `{ algorithms: [...] }`; `decode` usado como validação; `jwt.sign` sem `expiresIn`; segredo simétrico compartilhado entre serviços diferentes.
- `bcrypt` com cost < 10, `bcryptjs` síncrono em handler.

## Rede e SSRF

- `axios`, `got`, `node-fetch`, `undici`, `http.request` com URL de usuário. Correção: parse com `new URL`, `protocol` em `['https:']`, host em allowlist, resolver DNS (`dns.lookup`) e rejeitar loopback, `10/8`, `172.16/12`, `192.168/16`, `169.254/16`, `fc00::/7`, `::1`. Fixe o IP resolvido na conexão (evita DNS rebinding). `redirect: 'manual'`/`maxRedirects: 0`.
- Webhook configurável por usuário (callback URL): mesma regra.
- `NODE_TLS_REJECT_UNAUTHORIZED=0`, `rejectUnauthorized: false`, `strictSSL: false`.
- Proxy reverso feito à mão com `req.pipe(http.request(req.url))`: host e path do cliente controlam destino.

## Dependências e scripts

- `package.json` do diff: `scripts.preinstall|install|postinstall`, `bin`, dependências por URL git/tarball, `resolutions`/`overrides` que baixam versão com CVE.
- `npm install` de pacote com nome parecido com conhecido. Confira escopo (`@acme/*` precisa vir do registry privado: `.npmrc` com `@acme:registry`).
- Token em `.npmrc` versionado: `//registry/:_authToken=...`. Correção: variável de ambiente `${NPM_TOKEN}`.

## Logs e erros

- `console.log(req.headers)`, `logger.info(req.body)` em rota de login. Handoff para review-observabilidade quando o problema é PII em telemetria. Achado seu quando é segredo (senha, token, chave).
- `unhandledRejection` que encerra o processo por input malformado é DoS barato: valide e capture no handler.

## Falsos positivos frequentes

- `execFile('git', ['rev-parse', 'HEAD'])` com argumentos fixos.
- `fs.readFile` com path montado de constantes ou de config do deploy.
- Regex complexa aplicada só a literais internos.
- `md5` para ETag, checksum de cache ou dedup sem valor de segurança.
- `eval` em script de build/CLI local que não roda em produção.
