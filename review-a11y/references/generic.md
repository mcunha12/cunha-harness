# review-a11y — regras agnósticas de stack

Base: WCAG 2.2 AA e WAI-ARIA Authoring Practices (APG). Valem para HTML, qualquer framework e qualquer CSS.

## 1. Critérios novos do WCAG 2.2 (AA) que o diff costuma violar
| Critério | Regra | Sinal no código |
|---|---|---|
| 2.4.11 Focus Not Obscured (Minimum) | O elemento focado não fica totalmente escondido por conteúdo fixo | header/banner/chat `position: fixed` cobrindo o foco; falta `scroll-padding-top` |
| 2.5.7 Dragging Movements | Todo arrastar tem alternativa de ponteiro único | reorder, slider, upload só por drag |
| 2.5.8 Target Size (Minimum) | Alvo de 24x24 CSS px, ou espaçamento equivalente | ícones de 16-20 px agrupados sem gap |
| 3.2.6 Consistent Help | Ajuda (chat, contato) na mesma posição relativa entre páginas | widget de suporte muda de lugar por rota |
| 3.3.7 Redundant Entry | Dado já informado não é pedido de novo na mesma sessão | wizard que repete CPF/e-mail |
| 3.3.8 Accessible Authentication (Minimum) | Login sem teste cognitivo (decorar, transcrever) | bloqueio de colar em senha, CAPTCHA de caracteres sem alternativa |

Correção do 2.4.11: `html { scroll-padding-top: <altura do header fixo>; }`.

## 2. Ordem de decisão para widgets
1. Existe elemento HTML nativo? Use (`button`, `a`, `input`, `select`, `details/summary`, `dialog`, `progress`, `meter`).
2. Existe padrão no APG? Implemente roles, estados e teclas do padrão completo.
3. Sem padrão: reduza o widget até existir um.

Teclas do APG que o diff costuma esquecer:
- Tabs: Setas movem entre abas, Tab sai do tablist para o painel; roving tabindex (apenas a aba ativa com `tabindex="0"`).
- Menu/menubutton: Enter/Espaço/Seta abrem, Escape fecha e devolve o foco, Setas navegam, Home/End.
- Combobox: `aria-expanded`, `aria-controls`, `aria-activedescendant` na opção ativa, Escape fecha, Seta Baixo abre.
- Accordion/disclosure: `<button aria-expanded aria-controls>`; Enter/Espaço alternam.
- Dialog: foco inicial dentro, trap, Escape, retorno de foco.
- Radio group: Setas movem seleção, um tab stop.
- Slider: Setas ajustam, Home/End, `aria-valuenow/min/max/valuetext`.
- Tooltip: aparece com foco e hover, fecha com Escape, o conteúdo é referenciado por `aria-describedby`.

## 3. Cálculo de contraste
- Luminância relativa: converta sRGB para linear (`c <= 0.03928 ? c/12.92 : ((c+0.055)/1.055)^2.4`), `L = 0.2126 R + 0.7152 G + 0.0722 B`.
- Razão: `(L1 + 0.05) / (L2 + 0.05)`, com L1 a maior luminância.
- Limiares: 4.5:1 texto normal, 3:1 texto grande e componentes de UI/gráficos, 7:1 para AAA (fora do piso).
- Calcule com a cor de fundo efetiva. Fundo com `rgba` ou imagem exige o pior caso do fundo.
- Texto sobre imagem ou gradiente: aplique overlay sólido ou calcule no ponto mais claro.
- Estados (hover, focus, disabled, selected) são pares próprios. Cada um passa por 3:1 no indicador.

## 4. Padrões de CSS que quebram a11y
- `display: none` e `visibility: hidden` removem da árvore de acessibilidade. Texto só para leitor de tela usa classe `sr-only`:
```css
.sr-only { position: absolute; width: 1px; height: 1px; margin: -1px; padding: 0; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
```
- `opacity: 0` mantém o elemento focável e anunciável. Combine com `visibility: hidden` quando deve sumir.
- `pointer-events: none` não remove do teclado. Elemento desabilitado visual precisa de `disabled`/`aria-disabled`.
- `content: "..."` em `::before/::after` é anunciado por parte dos leitores. Texto significativo fica no DOM.
- `text-transform`/`letter-spacing` podem fazer o leitor soletrar. Escreva o texto no formato desejado quando o leitor soletra.
- `order`, `flex-direction: row-reverse` e `grid-area` descolam ordem visual da ordem de foco (2.4.3, 1.3.2). Mova no DOM.
- `@media (hover: hover)` protege estilo de hover para dispositivos sem hover, mas o conteúdo só em hover continua inacessível por teclado.
- `:focus-visible` para anel de teclado, `:focus` para foco programático necessário.
- `scroll-behavior: smooth` sem `@media (prefers-reduced-motion: no-preference)`.
- `font-size` em `rem`/`em`. `px` em `html` anula a preferência do usuário.
- `100vh` em mobile corta conteúdo com a barra do navegador; use `dvh` com fallback. Reflow em 320 px.

## 5. HTML que o formatter não pega
- `<button>` dentro de `<a>` e `<a>` dentro de `<button>`: interativo aninhado, inválido, comportamento inconsistente.
- `<label>` sem controle associado (`htmlFor`/`for`) ou duas labels no mesmo input.
- `id` duplicado quebra `for`, `aria-labelledby` e `aria-describedby`. Em componente reusável, gere id único (`useId` em React 18).
- `<input>` com `disabled` perde o foco e é omitido do envio. Quando o motivo do bloqueio importa ao usuário, use `aria-disabled="true"` e mantenha focável com texto explicativo.
- `<select>` customizado com `div`s: exige o padrão combobox/listbox completo. Prefira `<select>` nativo.
- `<table>` responsiva que vira `display: block` perde a semântica de tabela em alguns leitores. Reponha `role="table"`, `role="row"`, `role="cell"`/`columnheader`.
- `<details>`/`<summary>` entrega disclosure acessível sem JS.
- Links que abrem nova aba (`target="_blank"`) avisam no texto ou `aria-label` ("abre em nova aba").
- Ícone de link externo ou de download com texto oculto que descreve a ação.

## 6. Conteúdo gerado e rico
- HTML vindo de CMS, markdown ou LLM: valide a hierarquia de headings, o `alt` das imagens e a presença de `<th>`. O renderer controla o que o conteúdo pode produzir. Sanitização é de review-seguranca.
- Markdown renderizado: links com texto, listas reais, código em `<pre><code>` com `tabindex="0"` quando rola horizontalmente (2.1.1 para região rolável).
- Região rolável (`overflow: auto`) precisa de foco por teclado: `tabindex="0"`, `role="region"` e `aria-label`, quando não contém controle focável.

## 7. Idioma e linguagem
- `lang` no `<html>`. Trecho em outro idioma ganha `lang` próprio.
- Abreviações e siglas técnicas da área da saúde (ex.: ECG) usam `<abbr title>` na primeira ocorrência quando o diff introduz o termo sem expansão.
- Texto de erro diz o que fazer ("Informe o e-mail no formato nome@dominio.com"). "Campo inválido" falha 3.3.3.

## 8. Tempo e movimento
- Carrossel, banner rotativo, ticker: botão de pausa, sem auto-rotação por mais de 5 s sem controle (2.2.2).
- Sessão com timeout: aviso com 20 s ou mais para estender (2.2.1).
- Animação por scroll e parallax respeitam `prefers-reduced-motion`.
- Vídeo em loop sem som com mais de 5 s ganha controle de pausa.

## 9. Teste manual mínimo que o revisor deve simular no código
1. Tab do início ao fim: todo controle é alcançado, a ordem faz sentido, o foco aparece.
2. Enter e Espaço acionam cada controle. Escape fecha cada overlay.
3. Leitor de tela: cada controle tem nome, papel e estado.
4. Zoom 200% e viewport 320 px: nada cortado, sem rolagem em 2 dimensões (exceto tabela/mapa).
5. Cor desligada (escala de cinza): estados continuam distinguíveis.
6. `prefers-reduced-motion: reduce`: movimento reduzido.
