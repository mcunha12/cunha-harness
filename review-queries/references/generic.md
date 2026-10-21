# Queries e rotas: princípios agnósticos de stack

Cada item: sinal, impacto, correção.

## Estimar antes de reportar

Todo achado de performance responde cinco perguntas com número ou com "não sei":

1. N: quantos itens a coleção tem (média e máximo) e quem limita (DTO, tabela, domínio).
2. Quantas queries e chamadas externas a rota executa, em função de N.
3. Quantas linhas e bytes cada uma toca.
4. Frequência: requisições por segundo da rota (rota de tela inicial e de login pesam mais que painel interno).
5. Orçamento: o que a rota precisa cumprir (p95 do repo, timeout do proxy, SLO).

Sem os números, `confidence` é `media` e o `problem` diz o que falta medir.

Referências de ordem de grandeza (use como estimativa, declare como estimativa):
- Round trip a banco na mesma região: ~0,5-2 ms. Chamada HTTP entre serviços: ~5-50 ms mais o tempo do serviço. LLM: centenas de ms a dezenas de s.
- Seq scan de tabela de 1 milhão de linhas: dezenas a centenas de ms. Index scan: <1 ms.
- Serialização JSON: ~100-500 MB/s por core em Node. Payload de 5 MB bloqueia o event loop por 10-50 ms.

## N+1

- Forma: 1 query traz N pais, e N queries trazem os filhos.
- Formas escondidas: getter que consulta, serializer que acessa relação lazy, `map(async)` com `await` por item, resolver GraphQL por campo, hook de ORM, middleware que carrega o usuário a cada item, helper `isEnrolled(userId, courseId)` chamado em loop.
- Correção por ordem de preferência: join ou eager load na query de origem, 2 queries com `IN`/`ANY` e agrupamento em `Map`, DataLoader (batch por tick), view materializada ou coluna desnormalizada com regra de atualização.
- N pequeno e fixo não é N+1 de produção (ver heurísticas).

## Paginação

- Toda listagem tem teto de tamanho, imposto no servidor (`take = Math.min(limit, MAX)`).
- Offset: custo cresce com a página. Aceitável para tabelas até ~10^4-10^5 linhas e páginas rasas.
- Keyset: `WHERE (sort_col, id) > (:lastSort, :lastId) ORDER BY sort_col, id LIMIT :n`. Exige índice `(sort_col, id)`. Não permite pular para a página K, e isso é decisão de produto.
- Total exato (`COUNT`) custa um scan. Alternativas: `take + 1` para `hasNext`, total aproximado (`pg_class.reltuples`), total em cache.
- Ordenação sem desempate único gera páginas inconsistentes.

## Índices: modelo mental

- Um índice B-tree ordena por colunas na sequência declarada. A consulta o usa bem quando filtra pelo prefixo da esquerda com igualdade, seguido de um range ou da ordenação.
- Igualdade, range, ordenação: nesta ordem de colunas.
- Seletividade: índice vale quando o filtro reduz a poucas porcentagens da tabela. Índice em coluna com 2 valores equilibrados raramente é usado.
- Parcial: indexa só o subconjunto quente (`WHERE status = 'PENDING'`, `WHERE deleted_at IS NULL`).
- Covering: `INCLUDE (colunas)` permite index-only scan. Depende de `VACUUM` para o visibility map.
- Funcional: indexa a expressão exata usada na consulta.
- Custo de escrita: cada índice aumenta insert/update/delete e espaço. Reporte também índice redundante.
- Pergunta de revisão: "para esta consulta do diff, qual índice existente a atende, e o que o plano mostra?" Se a resposta é "não sei", peça o `EXPLAIN`.

## Chamadas entre serviços

- Independentes em paralelo, dependentes em sequência. Desenhe o grafo de dependências da rota. O tempo é o caminho crítico, não a soma.
- Limite de concorrência em fan-out (`p-limit`, semáforo): 5-20 por lote, conforme a capacidade do serviço a jusante.
- Falha parcial: decida se a rota degrada (resposta parcial com campo ausente) ou falha inteira. Decisão explícita no código (`allSettled`). A política de erro é do review-resiliencia.
- Chamada repetida com mesmos argumentos na mesma requisição: memoize por requisição.
- APIs chatty: o cliente que faz 6 chamadas para 1 tela pede um endpoint de composição. A camada que compõe fica onde o README define (BFF, gateway, o próprio serviço).
- Evite chamada de volta ao produtor para cada item de um evento (evento fino sem dados). Alternativa: evento com os campos necessários.

## Cache

Checklist por cache novo:

- Chave: inclui tudo que muda a resposta (tenant, usuário, idioma, versão do schema, parâmetros). Chave sem usuário em dado por usuário vaza entre usuários.
- TTL: toda entrada expira. TTL combina com a tolerância de desatualização do produto.
- Invalidação: toda escrita que muda o dado invalida a chave, ou o TTL curto cobre. Escrever e ler a mesma chave no mesmo fluxo sem invalidar mostra dado velho ao próprio autor.
- Stampede: quando a chave expira sob carga, N requisições recalculam. Mitigações: single-flight (uma promise por chave), lock curto, TTL com jitter, refresh em background, `stale-while-revalidate`.
- Cache de ausência e de erro: TTL curto e separado.
- Tamanho: limite de entradas ou bytes em cache em memória (LRU). Mapa global sem limite é vazamento de memória.
- Camadas: HTTP (`Cache-Control`, `ETag`), CDN, aplicação (Redis/memória), banco (materialized view). Cache em duas camadas soma o atraso de invalidação.
- Dado por usuário: `Cache-Control: private`. `public` em resposta autenticada é achado grave (dono do vazamento: review-seguranca).
- Memória por processo com várias réplicas gera inconsistência entre réplicas. Use Redis quando a consistência importa.

## Trabalho pesado e assíncrono

- Se uma requisição passa de ~1-2 s ou toca >10^4 itens, transforme em job: fila, resposta 202, endpoint de estado, notificação ao concluir.
- Operações em lote seguem: leitura em lotes (cursor), escrita em lotes (500-1000), concorrência limitada, checkpoint para retomar.
- O job tem timeout, idempotência e DLQ (review-resiliencia).

## Memória e streams

- Pergunta: o tamanho máximo do dado em memória depende da entrada do usuário? Se sim, use stream, cursor ou limite.
- Upload e download de arquivo: stream do disco/objeto ao socket, sem `Buffer` completo.
- Exportação (CSV, XLSX): gerar em stream ou em job com URL assinada.

## Complexidade algorítmica

- Busca linear dentro de loop sobre coleção grande é O(n²). Indexe em `Map`/`Set`/dict uma vez.
- Ordenar dentro de loop. Ordene uma vez.
- Ordenação, `distinct` e `groupBy` no banco quando há índice a favor, em memória quando a coleção é pequena e já carregada.
- Concatenação de string em loop de grande porte: use array e `join`.
- Regex com backtracking catastrófico: ReDoS é do review-seguranca, a lentidão do caminho legítimo é daqui.

## Contagem de custo no formato do achado

No `problem`, escreva a conta: "N = 50, 4 relações, 201 queries por request, ~1-2 ms por query, ~200-400 ms só de round trip". Número estimado leva a palavra "estimado".
