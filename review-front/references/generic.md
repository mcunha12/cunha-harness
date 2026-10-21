# review-front — regras agnósticas de stack

Valem para qualquer framework de UI (React, Vue, Svelte, Angular, vanilla). O detalhe de React fica em `react.md`.

## 1. Orçamento de performance
- Meça em números. LCP bom: até 2,5 s no p75. INP bom: até 200 ms. CLS bom: até 0,1. TBT de laboratório acima de 300 ms indica INP em risco.
- Chunk inicial de JS acima de 170 KB gzip em rota de entrada pesa em 4G médio. Cite o delta que o diff adiciona.
- Pergunte para cada import novo: quantos KB gzip, em qual chunk, em qual rota. Sem número, a confiança do achado cai para `media`.

## 2. Carregamento de recursos
- Sinal: recurso crítico (fonte, imagem hero, CSS) descoberto só depois de JS executar. Impacto: LCP atrasa 300-1500 ms. Correção: `<link rel="preload">` ou `fetchpriority="high"`.
- Sinal: `<script>` sem `defer`/`async`/`type="module"` no head. Impacto: bloqueia o parser. Correção: `defer`.
- Sinal: `preload` de recurso que a página não usa em 3 s. Impacto: consome banda do recurso crítico. Correção: remover.
- Sinal: imagem sem `width`/`height`/`aspect-ratio`. Impacto: CLS. Correção: declarar as dimensões.
- Sinal: imagem PNG/JPEG de mais de 200 KB em tela de lista. Correção: WebP/AVIF, `srcset` e `sizes`.
- Sinal: `@font-face` sem `font-display`. Correção: `swap` (ou `optional` para fonte decorativa) e `size-adjust` para reduzir CLS.
- Sinal: terceiro (analytics, chat, tag manager) carregado antes do conteúdo. Correção: carregar em `requestIdleCallback` ou após `load`.

## 3. Thread principal
- Sinal: loop síncrono sobre mais de 5 000 itens no handler de input. Impacto: INP acima de 200 ms. Correção: debounce, janela de render, Web Worker.
- Sinal: `JSON.parse` de payload acima de 1 MB na thread principal. Correção: paginar no servidor ou parsear em worker.
- Sinal: leitura de layout (`offsetWidth`, `getBoundingClientRect`, `scrollTop`) misturada com escrita de DOM em loop. Impacto: reflow síncrono por iteração. Correção: ler tudo, depois escrever; `requestAnimationFrame`.
- Sinal: listener de `scroll`/`resize`/`mousemove` sem `passive: true`, throttle ou `IntersectionObserver`/`ResizeObserver`. Correção: trocar pelo observer.
- Sinal: animação em `top/left/width/height`. Correção: `transform` e `opacity`.

## 4. Rede e cache no cliente
- Sinal: requests independentes disparados em sequência (`await a; await b;`). Correção: `Promise.all`.
- Sinal: o mesmo endpoint chamado por 3 componentes sem camada de cache. Correção: cache de query com dedup por chave.
- Sinal: request disparado a cada tecla. Correção: debounce de 250-400 ms e cancelamento do anterior.
- Sinal: `fetch` sem tratamento de `response.ok`. Impacto: 4xx/5xx tratado como sucesso. Correção: checar `ok` e lançar erro tipado.
- Sinal: polling com `setInterval` fixo sem pausa em aba oculta. Correção: `visibilitychange`, backoff, ou SSE/WebSocket.
- Sinal: resposta cacheável servida sem `Cache-Control`/`ETag` (arquivo estático, JSON de catálogo). Correção: headers no servidor; ponto de contato com review-queries.

## 5. Estado e ciclo de vida
- Cada recurso adquirido tem liberação pareada: listener, timer, subscription, observer, WebSocket, object URL (`URL.revokeObjectURL`), stream de câmera.
- Sinal: recurso adquirido no mount sem liberação no unmount. Impacto: leak proporcional ao número de navegações; handlers duplicados. Correção: cleanup.
- Sinal: estado de servidor duplicado em dois lugares. Correção: uma fonte, derivar o resto.
- Sinal: estado de UI (modal aberto, aba) persistido em store global compartilhado entre telas. Impacto: estado vaza para outra sessão de uso. Correção: estado local ou reset no unmount.

## 6. Resiliência da UI
- Toda tela com dado remoto tem 4 estados: carregando, vazio, erro, sucesso. Falta de um é MINOR; falta de erro em tela crítica é MAJOR.
- Sinal: erro de rede mostrado como "Nenhum resultado". Impacto: usuário conclui que não tem dado. Correção: estado de erro distinto, com ação de tentar de novo.
- Sinal: botão de submit sem estado `disabled`/`loading` durante a mutation. Impacto: duplo envio. Correção: desabilitar enquanto pendente e enviar idempotency key quando a API suportar.
- Sinal: perda de dados digitados em falha de envio. Correção: manter o estado do form e mostrar o erro.
- Sinal: decode de dado externo (`JSON.parse`, `atob`, `new URL`) sem try/catch. Correção: try/catch e estado de erro local.
- Sinal: dado de `localStorage`/`sessionStorage` lido sem try/catch e sem validação de forma. Impacto: modo privado e storage corrompido derrubam a tela. Correção: try/catch e fallback.

## 7. Dependências e build
- Sinal: lib duplicada por função (`moment` + `dayjs`, `axios` + `fetch` wrapper). Correção: uma.
- Sinal: import de pacote inteiro quando existe subpath (`lodash`, `date-fns/locale`, bibliotecas de ícone). Correção: subpath.
- Sinal: `sideEffects` ausente ou `true` em pacote interno consumido via barrel. Impacto: tree shaking falha. Correção: `"sideEffects": false` quando verdadeiro.
- Sinal: `import()` dinâmico sem `webpackChunkName`/`magic comment` quando o repo padroniza nomes. Impacto menor; reporte como NIT.
- Sinal: source map público de produção. Impacto: expõe código-fonte. Ponto de contato com review-seguranca.

## 8. Web APIs de robustez
- Sinal: `navigator.onLine` usado como verdade absoluta. Impacto: `true` com rede sem saída. Correção: tratar falha de request como fonte real.
- Sinal: `window.open` sem `noopener`. Impacto: `window.opener` exposto; segurança fica com review-seguranca.
- Sinal: `localStorage` usado como fila de escrita crítica sem versionamento do schema. Correção: chave versionada e migração.
- Sinal: envio de analytics no `beforeunload` com `fetch` comum. Impacto: request cancelado. Correção: `navigator.sendBeacon` ou `fetch` com `keepalive: true`.
