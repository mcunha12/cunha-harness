# Lente Caminho A→B

Framework próprio que junta Nielsen (10 heurísticas), Shneiderman (8 regras de ouro), Norman (princípios de design cognitivo) e Joyce e Lilley (heurísticas SMART para apps de smartphone). WCAG 2.2 (POUR) fica com a `review-a11y`.

A pergunta de toda dimensão: quanto esta tela aumenta o caminho do usuário do ponto A (onde ele chega) ao ponto B (o job to be done resolvido)?

## Dimensões

| # | Dimensão | Pergunta | Fontes |
|---|---|---|---|
| 1 | Caminho | Quantos passos, decisões e campos até concluir o job? Algum é dispensável? | job to be done; SMART8 |
| 2 | Estado e feedback | O usuário sabe onde está, o que aconteceu e o que falta? | Nielsen 1; Shneiderman 3 e 4; Norman (feedback); SMART1 |
| 3 | Modelo mental e mapeamento | Palavras, ícones e ordem são do mundo do usuário? O controle mostra o efeito? | Nielsen 2; Norman (modelo conceitual, mapeamento); SMART7 |
| 4 | Sinalização | O que é clicável parece clicável? A ação principal se destaca? | Norman (affordance, signifiers) |
| 5 | Consistência | Mesmo termo, mesmo padrão, mesma posição em todo o fluxo e na plataforma? | Nielsen 4; Shneiderman 1; SMART2 |
| 6 | Erro | O erro é prevenido ou restringido? Quando acontece, a mensagem diz como sair? | Nielsen 5 e 9; Shneiderman 5; Norman (restrições); SMART3 |
| 7 | Memória | O usuário reconhece em vez de lembrar? A ajuda aparece no contexto? | Nielsen 6 e 10; Shneiderman 8; SMART4 |
| 8 | Controle e reversão | Dá para desfazer, voltar e cancelar sem perder trabalho? | Nielsen 3; Shneiderman 6 e 7 |
| 9 | Foco e eficiência | Uma tarefa por tela, sem ruído? Há atalho para quem volta? | Nielsen 7 e 8; Shneiderman 2; SMART5, SMART6, SMART9 |
| 10 | Mobile | Funciona com uma mão, na rua, com rede ruim e interrupção? A digitação é mínima? | SMART10, SMART11, SMART12 |

## Heurísticas SMART (Joyce, Lilley, Barker e Jefferies)

1. Notificação imediata do status do app.
2. Tema e termos consistentes, seguindo convenções da plataforma.
3. Prevenir problemas; ajudar quando ocorrem.
4. Overlay com as funções principais quando adequado (onboarding).
5. Cada interface foca uma tarefa.
6. Interface visualmente agradável.
7. Interfaces intuitivas para jornadas mais fáceis.
8. Caminho navegável claro até a conclusão da tarefa.
9. Opções de configuração e atalhos.
10. Atender ambientes móveis diversos (luz, ruído, movimento, conectividade).
11. Facilitar a entrada de dados.
12. Usar câmera, microfone e sensores para reduzir a entrada manual.

Fonte: Joyce, G., Lilley, M., Barker, T., Jefferies, A. "Mobile Application Usability: Heuristic Evaluation and Evaluation of Heuristics" (2016), University of Hertfordshire, https://uhra.herts.ac.uk/id/eprint/13989/ — o conjunto foi proposto em "Adapting Heuristics for the Mobile Panorama" (2014).

## Como contar o caminho

No print de iPhone SE (375×667), seguindo o fluxo real de cliques:

- passos: telas ou estados até o job resolvido;
- decisões: escolhas que o usuário precisa fazer;
- campos: entradas de texto ou seleção;
- itens a lembrar: informação de uma tela que o usuário precisa levar para outra.

Depois do caminho no iPhone SE, confira os prints de tablet (768×1024) e desktop (1280×720) só para mudança de layout.

Com print da base (antes do diff), compare antes × depois e reporte a diferença. Sem print da base, reporte a contagem atual e o mínimo que o job exige.
