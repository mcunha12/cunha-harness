---
name: review-a11y
description: "Revisa acessibilidade (WCAG 2.2 AA) de um diff de UI: semântica HTML, nome acessível, ARIA, teclado e foco, conteúdo dinâmico, contraste, target size, motion, reflow, formulários e mídia. Acione em 'revisa a acessibilidade desse PR', 'isso passa em WCAG?', '/review-a11y' ou via master-review. Prefixo A11Y. NÃO cobre performance de render (review-front), XSS e authZ (review-seguranca), naming (review-legibilidade) nem testes (test-audit). Defeito em componente de design system externo vira handoff para o repo do DS."
argument-hint: "[--base <branch>] [--path <glob>] [--uncommitted]"
---

# review-a11y

## Missão

Encontrar no diff as barreiras que impedem alguém de usar a tela com teclado, leitor de tela, zoom, baixa visão, daltonismo ou preferência de movimento reduzido. O critério é WCAG 2.2 nível AA. Cada achado cita o critério de sucesso (ex.: 2.1.1), o sinal no código, quem fica bloqueado e a correção com código. Teste de referência: todo fluxo do diff termina só com teclado, e um leitor de tela anuncia o que o usuário precisa para decidir a próxima ação.

## Escopo

Cada item segue o formato sinal, impacto, correção. Detalhe por tecnologia em `references/`.

### 1. Semântica (WCAG 1.3.1, 4.1.2)
- Sinal: `<div onClick>` ou `<span onClick>` como controle. Impacto: não recebe foco, não aciona com Enter/Espaço, leitor de tela não anuncia "botão". Correção: `<button type="button">`. Link que navega usa `<a href>`.
- Sinal: `<a>` sem `href`, ou `<a href="#" onClick>` que executa ação. Correção: `<button>`.
- Sinal: heading escolhido por tamanho visual (`<h4>` logo após `<h1>`, vários `<h1>`). Impacto: navegação por headings do leitor de tela fica quebrada. Correção: nível pela hierarquia, tamanho por CSS.
- Sinal: página sem landmarks (`<main>`, `<nav>`, `<header>`, `<footer>`), ou duas `<nav>` sem `aria-label` distinto. Correção: um `<main>` por página e `aria-label` para diferenciar landmarks repetidos.
- Sinal: lista de itens feita com `<div>`s. Correção: `<ul>/<li>`. Tabela de dados com `<div>` ganha `<table>`, `<th scope>`, `<caption>`.
- Sinal: tabela usada para layout, ou `<table>` de dados sem `<th>`. Correção: CSS grid, ou cabeçalhos reais.
- Sinal: `<html>` sem `lang`, ou trecho em outro idioma sem `lang`. Correção: `lang="pt-BR"`, `lang="en"` no trecho.
- Sinal: `<title>` igual em todas as rotas. Impacto: aba e histórico indistinguíveis (2.4.2). Correção: título por rota.

### 2. Nome acessível (WCAG 1.1.1, 2.5.3, 3.3.2, 4.1.2)
- Sinal: botão só com ícone (`<button><Icon/></button>`) sem `aria-label`. Impacto: leitor de tela lê "botão" sem nome. Correção: `aria-label="Fechar"` e `aria-hidden="true"` no SVG.
- Sinal: `<img>` sem `alt`. Correção: `alt` descritivo, ou `alt=""` para imagem decorativa. Imagem com texto repete o texto no `alt`.
- Sinal: `alt="imagem"`, `alt="foto"`, nome do arquivo. Correção: descrever a função ou conteúdo.
- Sinal: `<input>` sem `<label for>`/`aria-label`/`aria-labelledby`. `placeholder` como único rótulo desaparece ao digitar e tem contraste baixo. Correção: `<label>` visível.
- Sinal: nome acessível diferente do texto visível (`aria-label="Enviar formulário"` em botão com texto "Salvar"). Impacto: usuário de comando de voz diz "Salvar" e nada acontece (2.5.3 Label in Name). Correção: o nome acessível começa com o texto visível.
- Sinal: vários links "Saiba mais" / "Clique aqui" sem contexto. Correção: texto distinto ou `aria-label` que inclua o destino.
- Sinal: ícone SVG decorativo sem `aria-hidden="true"` e `focusable="false"`. Impacto: leitor anuncia lixo; IE/Edge legado foca o SVG. Correção: esconder.
- Sinal: `title` como único nome do controle. Impacto: tooltip não aparece em toque nem teclado. Correção: nome real.

### 3. ARIA (WCAG 4.1.2)
- Primeira regra: use elemento nativo antes de ARIA. `role="button"` em `div` exige `tabindex="0"`, Enter e Espaço: mais código que `<button>`.
- Sinal: `role` inválido ou redundante (`<button role="button">`, `<nav role="navigation">`). Correção: remover.
- Sinal: `aria-hidden="true"` em elemento focável ou que contém focáveis. Impacto: o foco vai para algo que o leitor de tela não enxerga (4.1.2). Correção: `inert`, ou remover do tab order, ou não esconder.
- Sinal: `aria-labelledby`/`aria-describedby`/`aria-controls` apontando para id inexistente ou duplicado. Correção: id único e existente.
- Sinal: `aria-expanded` fixo, ou ausente em disclosure/accordion/menu. Correção: valor reflete o estado (`aria-expanded={open}`).
- Sinal: `aria-selected`, `aria-checked`, `aria-pressed`, `aria-current` com valor errado ou sempre `true`. Correção: refletir o estado.
- Sinal: widget composto (tabs, menu, combobox, listbox, tree) com roles incompletos. Exemplo: `role="tab"` sem `role="tablist"` pai e sem `role="tabpanel"`. Correção: seguir o APG do W3C, com navegação por setas.
- Sinal: `role="menu"` em navegação de site comum. Impacto: o modo de aplicação do leitor desliga a navegação normal. Correção: `<nav>` com lista de links e botão disclosure.
- Sinal: `aria-label` em `<div>`/`<span>` sem role. Impacto: ignorado. Correção: role apropriado ou remover.
- Sinal: `role="alert"` em conteúdo estático renderizado no load. Impacto: anúncios no carregamento. Correção: usar só para mensagem inserida dinamicamente.
- Sinal: `aria-live` em container que já nasce com texto. Correção: região viva existe vazia no DOM antes da inserção do texto.

### 4. Teclado e foco (WCAG 2.1.1, 2.1.2, 2.4.3, 2.4.7, 2.4.11)
- Sinal: ação só em `onMouseDown`/`onMouseEnter`/`onClick` de elemento não focável. Impacto: usuário de teclado e de switch não alcança. Correção: elemento nativo focável, ou `tabIndex={0}` + `onKeyDown` para Enter/Espaço.
- Sinal: `tabIndex` maior que 0. Impacto: ordem de tab desconectada da ordem visual. Correção: 0 ou -1, e ordem do DOM correta.
- Sinal: `outline: none`/`outline: 0` sem substituto de `:focus-visible`. Impacto: o usuário de teclado perde onde está (2.4.7). Correção: `:focus-visible { outline: 2px solid <cor 3:1>; outline-offset: 2px; }`. WCAG 2.2 pede indicador visível não coberto por conteúdo fixo (2.4.11 Focus Not Obscured).
- Sinal: modal/drawer sem focus trap, sem foco inicial dentro, sem Escape, sem retorno de foco ao disparador ao fechar. Impacto: foco escapa para a página atrás, usuário se perde. Correção: `<dialog>` com `showModal()`, ou biblioteca (Radix, Reach, react-aria) com `aria-modal="true"`, `role="dialog"`, `aria-labelledby`; restaurar foco ao elemento que abriu.
- Sinal: conteúdo atrás do modal permanece acessível (`aria-hidden` no resto ausente, sem `inert`). Correção: `inert` no fundo ou `aria-modal` com implementação conforme.
- Sinal: foco preso fora de modal (trap sem saída, 2.1.2). Correção: Escape fecha e devolve o foco.
- Sinal: sem skip link em página com navegação longa. Correção: `<a href="#main">Pular para o conteúdo</a>` visível ao receber foco (2.4.1).
- Sinal: `focus()` programático em elemento recém-montado sem necessidade. Impacto: salto de foco inesperado em carregamento. Correção: mover foco só após ação do usuário (abrir modal, erro de submit).
- Sinal: item removido (da lista, do carrinho) que tinha o foco, e o foco cai no `<body>`. Correção: mover o foco para o item vizinho ou o título da lista.
- Sinal: hover-only (tooltip, menu, ação em linha de tabela que só aparece no `:hover`). Impacto: invisível no teclado e no toque (1.4.13). Correção: mostrar também no `:focus-within`; conteúdo de hover fica persistente, dispensável (Esc) e passável (o ponteiro entra nele sem sumir).
- Sinal: arrastar como única forma de interação (reordenar, slider, upload por drag). Impacto: 2.5.7 Dragging Movements falha. Correção: alternativa de clique/botões de mover.
- Sinal: atalho de tecla única (letra solta) sem opção de desligar ou remapear (2.1.4). Correção: exigir modificador, ou permitir desligar.

### 5. Conteúdo dinâmico (WCAG 4.1.3, 3.2.2)
- Sinal: toast, erro de formulário, "salvo com sucesso", contador de resultados que aparece sem anúncio. Impacto: leitor de tela não percebe a mudança (4.1.3 Status Messages). Correção: região `role="status"` (polite) para sucesso e contagem, `role="alert"` (assertive) para erro bloqueante, presente no DOM antes de receber o texto.
- Sinal: SPA que troca de rota sem mover foco nem anunciar. Impacto: leitor continua lendo a tela antiga e o usuário de teclado fica no link clicado. Correção: no change de rota, mover foco para o `<h1>` (`tabIndex={-1}`) ou para um container `main`, e atualizar `document.title`.
- Sinal: loading sem anúncio (spinner só visual). Correção: `aria-busy="true"` na região e texto `role="status"` ("Carregando turmas") visível ou `sr-only`.
- Sinal: mudança de contexto no foco/input (3.2.1/3.2.2): `onChange` em `<select>` que navega ou envia. Correção: botão explícito de ação.
- Sinal: timeout de sessão ou carrossel auto-rotativo sem pausa (2.2.1, 2.2.2). Correção: controle de pausa e aviso antes de expirar, com opção de estender.

### 6. Visual (WCAG 1.4.1, 1.4.3, 1.4.10, 1.4.11, 1.4.4, 1.4.12, 2.3.3, 2.5.8)
- Contraste de texto: 4.5:1 para texto normal, 3:1 para texto grande (>= 24 px, ou >= 18,66 px em negrito). Calcule com os valores reais dos tokens do tema. Sem os valores, `confidence: media` e peça o par de cores.
- Contraste de componente de UI e gráfico: 3:1 para borda de input, ícone com significado, indicador de foco, estado selecionado (1.4.11).
- Sinal: informação só por cor (erro só em vermelho, status só por bolinha verde/vermelha, link sem sublinhado em parágrafo). Impacto: daltonismo, tela monocromática (1.4.1). Correção: ícone + texto, sublinhado.
- Sinal: placeholder, texto desabilitado e legenda de gráfico com cor clara sobre branco. Texto desabilitado é isento, mas placeholder não.
- Sinal: target de toque/clique menor que 24x24 CSS px sem espaçamento (2.5.8 Target Size, novo no 2.2). Correção: `min-width/min-height: 24px` (alvo recomendado de 44 px em mobile) ou espaçamento que mantenha círculo de 24 px sem sobreposição.
- Sinal: `font-size` em `px` fixo em `html`/`body`, `user-scalable=no` ou `maximum-scale=1` no viewport. Impacto: bloqueia zoom (1.4.4). Correção: `rem`, remover a restrição.
- Sinal: container com `width` fixa em px e `overflow: hidden` que corta em 320 px de largura ou 400% de zoom (1.4.10 Reflow). Correção: layout fluido, `min-width: 0`, quebra de linha; rolagem horizontal só para tabelas e mapas.
- Sinal: `line-height`, `letter-spacing` ou `word-spacing` forçados com `!important` e altura fixa em texto. Impacto: o usuário que ajusta o espaçamento perde texto (1.4.12). Correção: altura `min-height` em vez de `height`.
- Sinal: animação, parallax, auto-play de vídeo em loop, transição grande sem `@media (prefers-reduced-motion: reduce)`. Impacto: desconforto vestibular (2.3.3). Correção: reduzir ou remover o movimento nesse media query; conteúdo em movimento por mais de 5 s ganha pausa (2.2.2).
- Sinal: flash mais de 3 vezes por segundo (2.3.1). BLOCKER.
- Sinal: `prefers-color-scheme`/`forced-colors` ignorados, com ícone em `background-image` que some em modo de alto contraste. Correção: `currentColor`, `forced-color-adjust` com cuidado.
- Sinal: orientação travada (`screen.orientation.lock`) sem necessidade (1.3.4). Correção: remover.

### 7. Formulários (WCAG 1.3.5, 3.3.1, 3.3.2, 3.3.3, 3.3.7, 3.3.8)
- Sinal: erro só em texto vermelho abaixo do campo, sem associação. Correção: `aria-invalid="true"`, `aria-describedby` apontando para o id da mensagem, e mensagem textual que diz o que corrigir.
- Sinal: submit inválido sem mover foco ao primeiro erro ou ao resumo de erros. Correção: foco no primeiro campo inválido, ou resumo com `role="alert"` e links para os campos.
- Sinal: campo obrigatório indicado só por asterisco colorido. Correção: `required`/`aria-required="true"` e texto "(obrigatório)" na label.
- Sinal: campo de dado pessoal (nome, e-mail, telefone, CEP, CPF) sem `autocomplete` (1.3.5). Correção: `autoComplete="email"`, `"tel"`, `"name"`, `"postal-code"`.
- Sinal: `type="text"` para e-mail, telefone ou número. Correção: `type="email"`, `type="tel"`, `inputMode="numeric"`.
- Sinal: radios/checkboxes agrupados sem `<fieldset><legend>` (ou `role="group"` com `aria-labelledby`). Correção: agrupar com legenda.
- Sinal: validação que bloqueia colar em campo de senha ou código (3.3.8 Accessible Authentication). Correção: permitir colar e gerenciador de senhas; CAPTCHA de reconhecimento cognitivo precisa de alternativa.
- Sinal: o fluxo pede o mesmo dado que o usuário já informou na mesma sessão (3.3.7 Redundant Entry). Correção: preencher automático ou oferecer seleção.
- Sinal: `onBlur` que valida e mostra erro enquanto o usuário só tabula pelo campo. Correção: validar após interação e no submit.

### 8. Mídia (WCAG 1.2.x, 1.4.2, 2.1.1)
- Sinal: `<video>` pré-gravado (aula) sem `<track kind="captions">`. Impacto: aluno surdo ou em ambiente sem som perde o conteúdo (1.2.2 AA). Correção: legendas em WebVTT; transcrição para áudio puro (1.2.1) e audiodescrição ou alternativa de mídia para vídeo com informação só visual (1.2.5 AA).
- Sinal: player customizado cujos controles são `div` sem teclado. Correção: `<button>` para play/pause/mudo/tela cheia, `<input type="range">` para volume e posição com `aria-valuetext` ("1 minuto e 20 de 12 minutos"), atalhos documentados. Player que usa os controles nativos já cobre.
- Sinal: autoplay com áudio por mais de 3 s sem controle de pausa/mudo (1.4.2). Correção: `muted` no autoplay e controle visível.
- Sinal: transcrição, legenda ou velocidade de reprodução ausentes em conteúdo educacional recorrente. Reporte como MINOR com handoff ao produto quando o diff não cria o player.
- Sinal: iframe de vídeo de terceiro sem `title`. Correção: `title="Aula 3: Fisiologia"`.
- Sinal: PDF/documento gerado (certificado, material de aula) sem estrutura (tags, título, idioma). Reporte como MINOR quando o diff gera ou exibe o arquivo.

## Fora de escopo

| Tema | Dono |
|---|---|
| Re-render, bundle, Web Vitals, effects | review-front |
| XSS, `dangerouslySetInnerHTML`, authZ | review-seguranca |
| Naming e complexidade | review-legibilidade |
| Regra de produto (texto de microcopy, tradução) | produto; reporte só a barreira de acesso |
| Testes automatizados de a11y | test-audit |
| Componente do design system externo com defeito | repo do DS (handoff, sem patch local) |

Registre em `handoffs` com uma linha.

## Design system externo

Componente de pacote externo (por exemplo `@acme/design-system`) com defeito de a11y (sem `aria-label`, foco ausente, contraste do token) não recebe override no repo consumidor. Reporte um achado `MINOR` ou `MAJOR` com `category: "defeito no design system"`, descreva o componente e o critério violado, e recomende abrir issue no repo do DS. Use as props que o DS oferece (`aria-label`, `hideCloseButton`, `title`) quando a barreira se resolve no uso. Override por CSS que remove `outline` do DS é defeito do diff.

## Processo

1. Leia os 4 arquivos de `~/.claude/skills/master-review/references/`: `output-contract.md`, `severity-rubric.md`, `review-rules.md`, `ownership-matrix.md`.
2. Detecte a stack pela tabela de `review-rules.md`. Leia `references/generic.md` sempre. Leia `references/react.md` com `react`/`next`.
3. Obtenha o diff. Com context packet do orquestrador, use-o. Standalone, detecte a base (`main`, `master`, `develop`) e rode `git diff $(git merge-base <base> HEAD)...HEAD`. Com `--uncommitted`, inclua staged e unstaged (`git diff HEAD`). Respeite `--path`. Sem arquivo de UI no diff (JSX/TSX/HTML/CSS/Vue/Svelte/templates), devolva `skipped_reason`.
4. Analise cada componente do diff: a árvore renderizada, os handlers, o CSS e os estados (aberto, erro, carregando, vazio).
5. Verifique o contexto. Abra o componente do DS para ver o que ele já entrega (role, foco, `aria-*`). Abra o `ThemeProvider`/tokens para calcular contraste. Abra o pai para ver se o `<label>` ou o `aria-labelledby` vem de fora.
6. Classifique pela rubrica abaixo. Cite o critério WCAG em `refs`.
7. Emita no formato de `output-contract.md`. Prefixo `A11Y`, `agent: "review-a11y"`. Máximo de ~15 achados.

Standalone: mostre o markdown ao final. Não altere código.

## Rubrica de severidade

**BLOCKER**
- Fluxo principal (login, matrícula, assistir aula, pagamento) inoperável por teclado ou sem nome acessível no controle de ação.
- Modal sem foco dentro nem Escape que prende o usuário de teclado.
- Flash acima de 3 por segundo.
- Vídeo educacional novo sem legenda no fluxo principal, quando o diff cria o player e o conteúdo é a razão da tela.

**MAJOR**
- `div`/`span` clicável em fluxo secundário.
- Botão só com ícone sem `aria-label`.
- `outline: none` global sem substituto.
- Erro de formulário sem associação (`aria-describedby`) nem anúncio.
- Contraste de texto abaixo de 3:1.
- SPA sem gestão de foco/anúncio na troca de rota.
- `aria-hidden` em container que contém focáveis.

**MINOR**
- Contraste entre 3:1 e 4.5:1 em texto normal.
- Target com 20-23 px com espaçamento ao redor próximo de 24 px.
- Ausência de `autocomplete` em campo de dado pessoal.
- Heading com nível pulado.
- `alt` pouco descritivo.
- Ausência de `prefers-reduced-motion` em transição curta.

**NIT**
- `role` redundante em elemento nativo.
- Ordem de landmarks.
- `title` no `<a>` que repete o texto.

## Heurísticas anti-falso-positivo

- Componente do DS já entrega nome, role e foco. Abra o componente antes de pedir `aria-label` em `<Button>` do DS com texto.
- `<div onClick>` com `role="button"`, `tabIndex={0}` e `onKeyDown` para Enter/Espaço cumpre o requisito de operabilidade. Reporte como MINOR de preferência pelo elemento nativo, sem BLOCKER.
- `onClick` em elemento que já é `<button>`, `<a href>`, `<input>`, `<summary>` é correto.
- `onClick` em `<div>` que só captura bolha para fechar overlay (clique fora) com Escape disponível no mesmo overlay é aceitável.
- `aria-hidden="true"` em SVG decorativo dentro de botão com texto visível está correto.
- `alt=""` em imagem decorativa está correto. Reporte só quando a imagem carrega informação.
- `outline: none` seguido de `:focus-visible` com estilo próprio está correto.
- `tabIndex={-1}` em container que recebe foco programático (heading de rota, modal) está correto.
- Contraste: texto desabilitado, logotipo e texto puramente decorativo são isentos (1.4.3).
- `autoFocus` em campo de busca aberto por ação do usuário ou em dialog é aceitável. Em carregamento de página comum é problema.
- `placeholder` com `<label>` visível presente é aceitável.
- Sem os valores dos tokens, não afirme número de contraste com `confidence: alta`.
- `jsx-a11y` desabilitado por regra no diff exige olhar: `eslint-disable jsx-a11y/*` sem motivo é achado.

## Ferramentas determinísticas opcionais

Rode só se instaladas no repo. A saída é insumo. Ferramenta automática cobre cerca de 30-40% dos critérios WCAG; o restante exige leitura.

- `eslint-plugin-jsx-a11y`: verifique `ls node_modules/eslint-plugin-jsx-a11y`. Rode `npx eslint --ext .tsx,.jsx <arquivos do diff>` se o plugin estiver na config do repo (`grep -r "jsx-a11y" .eslintrc* eslint.config.*`).
- `axe-core`: verifique `ls node_modules/axe-core`. Em teste Jest existente com `jest-axe`, rode só o arquivo de teste do componente tocado: `yarn test --testPathPattern="<Componente>"` com `--maxWorkers=2`.
- `@axe-core/playwright`: verifique `ls node_modules/@axe-core/playwright` e `playwright.config.*`. Rode apenas o spec da rota tocada com `npx playwright test <spec>`. Só com a app rodando; não suba servidor sem pedido.
- Calculadora de contraste: calcule à mão com a fórmula WCAG de luminância relativa para pares de cor dos tokens.

## Exemplos

### Achado 1

```json
{
  "id": "A11Y-001",
  "agent": "review-a11y",
  "severity": "MAJOR",
  "confidence": "alta",
  "category": "Nome acessível",
  "location": { "repo": "web-app", "file": "src/components/NoteDrawer/Header.tsx", "lines": "21-27" },
  "evidence": "<IconButton onClick={onClose}>\n  <CloseIcon />\n</IconButton>",
  "problem": "O botão de fechar só tem ícone. O leitor de tela anuncia 'botão' sem nome e o usuário não sabe que fecha o painel. Viola WCAG 4.1.2 e 1.1.1.",
  "fix": "<IconButton onClick={onClose} aria-label=\"Fechar anotações\">\n  <CloseIcon aria-hidden=\"true\" focusable=\"false\" />\n</IconButton>",
  "auto_fixable": true,
  "effort": "S",
  "refs": ["WCAG 4.1.2", "WCAG 1.1.1"],
  "introduced_by_diff": true
}
```

```
### [MAJOR] A11Y-001 — Botão de fechar sem nome acessível
**Onde:** web-app/src/components/NoteDrawer/Header.tsx:21-27 · **Confiança:** alta · **Esforço:** S
**Problema:** leitor de tela anuncia "botão" sem nome.
**Correção:** `aria-label="Fechar anotações"` e ícone com `aria-hidden`.
```

### Achado 2

```json
{
  "id": "A11Y-002",
  "agent": "review-a11y",
  "severity": "BLOCKER",
  "confidence": "alta",
  "category": "Foco em modal",
  "location": { "repo": "web-app", "file": "src/components/ConfirmModal/index.tsx", "lines": "12-34" },
  "evidence": "<Overlay onClick={onClose}>\n  <Box>\n    <Title>Cancelar matrícula?</Title>\n    <Button onClick={onConfirm}>Confirmar</Button>\n  </Box>\n</Overlay>",
  "problem": "O modal não tem role=dialog, não move o foco ao abrir, não fecha com Escape e não devolve o foco. O usuário de teclado continua nos elementos da página atrás do overlay e confirma uma ação destrutiva sem ouvir o título. Viola WCAG 2.1.1, 2.4.3 e 4.1.2.",
  "fix": "<dialog ref={ref} aria-labelledby=\"confirm-title\" onClose={onClose}>\n  <h2 id=\"confirm-title\">Cancelar matrícula?</h2>\n  <button type=\"button\" onClick={onConfirm}>Confirmar</button>\n</dialog>\n// useEffect: ref.current.showModal() ao abrir; o <dialog> nativo trata Escape, trap e retorno de foco",
  "auto_fixable": false,
  "effort": "M",
  "refs": ["WCAG 2.1.1", "WCAG 2.4.3", "WAI-ARIA APG Dialog (Modal)"],
  "introduced_by_diff": true
}
```

### Caso que parece problema e não se reporta

```tsx
<IconButton aria-label="Fechar" onClick={onClose}>
  <CloseIcon />
</IconButton>
```

Sinal aparente: ícone dentro de botão sem `aria-hidden`. O `<IconButton>` do DS já define `aria-hidden` nos filhos SVG e o `aria-label` fornece o nome. Confirmado ao abrir o componente do DS. Não reportar.
