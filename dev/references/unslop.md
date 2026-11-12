# Unslop no /dev

Adaptado do unslop de Damir Sokolovsky (@heydamir), https://github.com/heydamir/unslop, licença CC BY 4.0. Mantenha este crédito em toda cópia.

Vale para toda task com UI, com ou sem Impeccable. Onde esta página conflita com a spec, o `DESIGN.md` ou outra regra do /dev, a regra do /dev ganha.

## 1. Triagem

Antes de editar, liste cada sinal de UI com cara de IA, 1 linha por sinal, com o arquivo e o trecho: gradiente de matiz em superfície, texto com gradiente, glow, sombra colorida, blob ou orbe decorativo, emoji como ícone, badge `Novo ✨`, rótulo em caixa alta com espaçamento largo, peso 700 a 900 em título, animação em loop sem dado ao vivo, valor fora da grade de 4 px, texto que grita.

Classifique a tela e grave a classe no resumo da task:

| Classe | Critério | O que a task faz |
|---|---|---|
| Pesada | muitos sinais em cor, tipografia, ícones e texto | as 9 passadas inteiras |
| Leve | tela quase pronta, poucos sinais | corrige só os sinais listados |
| Limpa | nenhum sinal | só o que a spec pede; sugestões de até 3 ajustes vão para o resumo, sem aplicar |

Nunca mude uma tela boa só para ela ficar diferente.

## 2. Nove passadas, em ordem

Termine cada passada na tela inteira antes da próxima: espaçamento, cor, ícones, texto, tipografia, layout, detalhes, visuais, movimento.

1. Espaçamento: grade de 4 px; mesma coisa, mesmo tamanho; espaço dentro do grupo menor que entre grupos; ícones numa coluna, rótulos numa linha, números alinhados à direita.
2. Cor: superfícies neutras; 1 acento, usado pouco; cor semântica só com significado; borda em hairline.
3. Ícones: 1 conjunto, 1 tamanho, 1 traço; cor do papel do texto; ícone que não acrescenta sai.
4. Texto: regras da seção 3.
5. Tipografia: hierarquia por tamanho e cor; `tabular-nums` e 1 formato de número na tela.
6. Layout: 1 ação primária e no máximo 1 secundária por bloco.
7. Detalhes: raio aninhado (interno = externo − padding, mínimo 4); 1 gráfico principal; 1 acento por gráfico; card de número sem sparkline decorativa.
8. Visuais: decoração sem significado sai.
9. Movimento: animação em loop sem motivo sai. Animação da cena de jogo fica.

## 3. Texto da interface

1. Sem ponto de exclamação.
2. Sem palavra de propaganda: "revolucionário", "mágico", "turbinar", "sem esforço", "com IA" em tudo.
3. Título nomeia o contexto. Sem saudação com emoji.
4. Rótulo curto: "Buscar", não "Busque qualquer coisa...".
5. Variação diz contra o quê compara: "+12% vs semana passada".
6. Número que não dá para conferir ("10x mais rápido", "10 mil jogadores") vai para o resumo da task como pergunta ao Marcelo e sai da tela até ele confirmar.
7. Dado de exemplo com cara de real: nomes e números plausíveis, nunca `[X]` ou `123.456`.

## 4. Direção

As 5 linhas de direção saem do brainstorm e estão na spec (`references/brainstorm.md`, "Propostas de UI com Impeccable"). A task segue a direção da spec e não cria outra.
