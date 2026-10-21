Você faz a retro da feature que acabou. Não edite código, skills nem o estado.

Leia, em {{feature_dir}}: state.json, plan.json, decisions.jsonl, costs.jsonl, reviews/*.md, tasks/*/result.json.
Leia também as linhas de ~/.claude/code-guard/ledger.jsonl com "feature": "{{feature}}" e as regras de ~/.claude/skills/code-guard/core.md, domains/*.md e ~/.claude/code-guard/learned/*.md.

Escreva {{feature_dir}}/retro.md em PT-BR, STE Operacional, com 4 seções, cada item em uma linha e com a evidência (arquivo ou id):

1. Checagens automáticas que faltaram: erro achado na review que uma regex sobre a linha adicionada pegaria. Para cada uma: id, regex, regex de arquivo, mensagem, origem (review-x/categoria) e a identidade do ledger.
2. Regras sem efeito: regra da code-guard carregada nesta feature que nunca evitou nem disparou nada, ou que repete outra.
3. Custo: os 3 passos ou reviews que mais gastaram tokens ou tempo, e por quê.
4. Navegação: leituras repetidas, arquivos procurados mais de uma vez, passo refeito.

Sem opinião e sem preâmbulo. Seção vazia: escreva "nada".
Devolva só o caminho do arquivo e até 5 linhas de resumo.
