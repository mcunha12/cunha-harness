# Domínio: front

- [FRT] Tela nova nasce em 375 px (iPhone SE) e só depois cresce para desktop; confira com `mobile_flow.py`. — origem: review-front/mobile
- [FRT] Remote de Module Federation renderiza dentro de error boundary com fallback. — origem: review-front/module-federation-sem-error-boundary
- [FRT] Fetch em effect tem cleanup (AbortController ou flag) e ignora resposta de recurso anterior. — origem: review-front/effect-fetch-sem-cleanup
- [FRT] Dependência de effect é estável. Nunca função ou objeto inline em deps de effect que faz `setState`. — origem: review-front/loop-de-render
- [FRT] Value de context é memoizado quando há muitos consumidores. — origem: review-front/context-recriado
- [FRT] Requests independentes da rota de entrada vão em paralelo. — origem: review-front/waterfall
- [FRT] Lib pesada (acima de ~100 KB gzip) entra por import dinâmico, fora do chunk inicial. — origem: review-front/bundle
- [FRT] `setInterval`, listener e subscription têm cleanup no unmount. — origem: review-front/leak
- [FRT] Mutation invalida ou atualiza o cache dos dados que ela altera. — origem: review-front/dado-velho
- [FRT] Progresso do usuário é salvo durante o uso, nunca só no unload. — origem: review-front/progresso-no-unload
- [FRT] Use os tokens, componentes e breakpoints do design system do repo. Sem cor, espaçamento ou media query hardcoded. — origem: review-front/design-system
