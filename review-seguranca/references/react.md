# Segurança em React (e Next.js)

## XSS

- **`dangerouslySetInnerHTML`.** Sinal: qualquer uso. Origem do valor: literal do código, CMS, campo de usuário, resposta de API, saída de LLM. Impacto: script na origem da app lê `sessionStorage`/`localStorage`, chama API como o aluno. Correção: sanitizar na hora do render com `DOMPurify.sanitize(html, { USE_PROFILES: { html: true } })` ou renderizar como texto. Sanitizar na entrada do banco não basta se outro caminho grava sem passar pela função.
- **Markdown.** Sinal: `react-markdown` com `rehypePlugins={[rehypeRaw]}`, `remark-html` com `sanitize: false`, `marked`/`markdown-it` com `html: true` e saída injetada via `dangerouslySetInnerHTML`. `react-markdown` puro escapa HTML. `rehype-raw` reabre a porta. Correção: `[rehypeRaw, rehypeSanitize]` nessa ordem, com schema que remove `script`, `style`, `iframe`, handlers `on*` e URLs `javascript:`. Se o conteúdo vem de LLM, registre handoff para review-ia.
- **URL como atributo.** Sinal: `<a href={url}>`, `<iframe src={url}>`, `<img src>`, `<form action>`, `window.open(url)`, `location.href = url` com `url` externa. `javascript:` e `data:text/html` executam no clique. React 18 só avisa. Correção: `const safe = /^(https?:|mailto:|tel:)/i.test(url) ? url : '#'` ou `new URL(url, base)` com checagem de `protocol`.
- **Escape hatches.** `ref.current.innerHTML = ...`, `document.write`, `insertAdjacentHTML`, `eval`, `new Function`, `setTimeout(string)`, `createElement('script')` com `src` dinâmico.
- **Props espalhadas.** Sinal: `<div {...userProps} />` ou `<a {...data} />` com objeto vindo de API/URL. Impacto: injeta `dangerouslySetInnerHTML`, `onClick` como string em libs antigas, `href`. Correção: whitelist de props.
- **Template com string em `styled-components`.** Sinal: ``css`${userInput}```, `createGlobalStyle` com valor externo, ``style={{ background: `url(${u})` }}``. Impacto: exfiltração por CSS (`url()` com seletor de atributo), clickjacking visual. Correção: validar contra allowlist de cor/valor.
- **Links externos.** `target="_blank"` sem `rel="noopener noreferrer"` em link com URL de usuário. Browsers modernos aplicam `noopener` por padrão, então MINOR.

## Armazenamento e estado

- Token em `localStorage`: persiste entre abas e sessões, fica exposto a XSS por mais tempo. `sessionStorage` limita à aba e ainda é legível por script. Em app que usa SDK de IdP (Cognito Amplify, Auth0 SPA) que escolheu `sessionStorage`, trate como padrão e reporte só leitura nova e insegura do token.
- Token em React state, Context, Redux devtools exposto em prod, `window.__STATE__`.
- `console.log(token|user|response)` com dado sensível chega em extensão do navegador e ferramentas de suporte. Handoff para review-observabilidade se for telemetria, achado seu se for segredo.
- Dados sensíveis em URL (`?token=`, `?cpf=`) vão para Referer e analytics. Correção: header, body ou estado de navegação (`navigate(path, { state })`).
- Cache do react-query com dado de um usuário e `queryKey` sem o id do usuário: após logout/login na mesma sessão, o próximo usuário vê dado anterior. Correção: `queryClient.clear()` no logout e id do usuário na key.

## Variáveis de ambiente do bundle

- `REACT_APP_*`, `VITE_*`, `NEXT_PUBLIC_*`, `process.env.X` substituído pelo Webpack `DefinePlugin`/`EnvironmentPlugin`, `window.env.*` injetado por `env-config.js`: todo valor chega ao navegador. Procure no diff: chave de LLM, `secret`, `private`, `service_role`, URL interna (`*.svc.cluster.local`), token de webhook. Correção: mover para servidor e expor endpoint próprio.
- `.env.production` com valor real versionado.
- `dangerouslyAllowBrowser: true` (SDK openai) sinaliza chave no client.
- Source maps de produção publicados abertos (`devtool: 'source-map'` servido): entrega o código-fonte e comentários. MINOR, MAJOR se o código contém segredo.

## Autorização no client

- `if (user.role === 'admin') <Botao />` oculta UI e não protege nada. Procure a rota correspondente na API (grep da rota no repo irmão se `related_repos` existir). Sem guard no servidor: achado na API, handoff do front só descreve.
- Route guard (`RequireAuth`, loader que redireciona) é UX. Dado sensível entregue no bundle (JSON de preços, lista de e-mails, regras de elegibilidade) é público mesmo atrás do guard.
- Feature flag no client como controle de acesso: flag é visível e alterável no navegador.

## Navegador e integração

- **`postMessage`.** Sinal: `window.addEventListener('message', h)` sem checar `event.origin` contra allowlist, ou `postMessage(data, '*')` com dado sensível. Relevante para WebView e iframes. Correção: `if (event.origin !== EXPECTED) return;` e valide o schema da mensagem.
- **Module Federation e remotes.** O host executa JS do remote com todos os privilégios. URL de remote vinda de `window.env`/config editável por usuário, ou de query param, é execução remota de código. Correção: URL fixa por ambiente em config de build/deploy. Remote carregado de domínio externo ao controle da empresa: MAJOR.
- **Deep link e WebView.** Rota que lê `token`, `redirect`, `returnUrl` de query: valide destino contra allowlist (open redirect e token leak).
- **Iframe.** `<iframe>` de terceiro sem `sandbox` e sem `allow` mínimo. Embed de vídeo precisa de `sandbox="allow-scripts allow-same-origin allow-presentation"` conforme o provedor.
- **CSP e headers.** Quando o diff altera `nginx.conf`, `helmet`, `next.config.js headers()` ou meta CSP: confira `script-src` sem `'unsafe-inline'`/`'unsafe-eval'`, `frame-ancestors`, `object-src 'none'`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`. Afrouxamento no diff é MAJOR.
- **Analytics/session replay.** Gravação de sessão (PostHog, Hotjar) captura campos de formulário. Procure `maskAllInputs: false`, `data-ph-no-capture` ausente em campos de CPF/senha/cartão. Handoff para review-observabilidade.

## Next.js

- Server Actions e Route Handlers são endpoints públicos: autentique e autorize dentro de cada um. Checar só no layout não cobre a Action.
- `NEXT_PUBLIC_` expõe ao client. Variável sem prefixo fica no servidor, desde que o módulo não seja importado de um Client Component. Importar módulo com segredo em arquivo `'use client'` o inclui no bundle.
- Props de Server Component para Client Component serializam tudo para o HTML/RSC payload. Passar `user` inteiro vaza `passwordHash`, `cpf`. Passe o mínimo.
- `fetch` em Server Component com cache: resposta por usuário cacheada globalmente (`force-cache`, `revalidate`) entrega dado entre usuários. Use `cache: 'no-store'` ou `cookies()/headers()`.
- Middleware de auth com matcher incompleto deixa rota fora (`/api/*`, `/_next/data`). Confira o `matcher`.
- `images.remotePatterns` com `hostname: '**'` abre o otimizador a SSRF e abuso de custo.
- `dangerouslySetInnerHTML` em `<script type="application/ld+json">` com JSON de usuário: escape `<` como `<`.

## Falsos positivos frequentes

- `dangerouslySetInnerHTML` com SVG/ícone literal do próprio repo.
- ``href={`/curso/${id}`}`` com `id` de param de rota (path relativo, sem esquema controlável).
- Token no `sessionStorage` gerenciado por SDK de IdP.
- `window.env.POS_*_BFF`, URLs e chaves públicas de analytics no bundle.
