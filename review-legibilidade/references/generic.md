# review-legibilidade — regras agnósticas de stack

## 1. Complexidade cognitiva (SonarSource), como contar
- +1 para cada `if`, `else if`, `else`, ternário, `switch`, `for`, `foreach`, `while`, `do while`, `catch`, `goto`/`break label`, e para cada sequência de operadores lógicos iguais trocada por outro tipo (`a && b && c` soma 1; `a && b || c` soma 2).
- +1 extra por cada nível de aninhamento em que a estrutura aparece (um `if` dentro de um `for` dentro de um `if` soma 1+2+3).
- +1 por recursão direta.
- Não soma: `else` de um `if` já contado conta só 1, `switch` conta uma vez independente do número de `case`, early return, lambdas triviais.
- Limiar de reporte: 16 a 25 MINOR, acima de 25 MAJOR em função nova.
- Calcule à mão em funções do diff com 3+ níveis de indentação. Cite o número no `problem`.

## 2. Guard clauses e achatamento
```
// antes: caminho feliz no fundo
function charge(order) {
  if (order) {
    if (order.items.length > 0) {
      if (!order.paid) {
        return pay(order);
      }
    }
  }
  return null;
}
// depois
function charge(order) {
  if (!order || order.items.length === 0 || order.paid) return null;
  return pay(order);
}
```
- Retorno ambíguo (`null` para "não existe", "inválido" e "já pago") vale o relato quando o caller depende de distinguir. O dono do desenho de erro explícito/Result é review-clean; aqui reporte só a ilegibilidade do ponto de chamada.
- Inverta condição para reduzir aninhamento quando o bloco do `else` é curto.

## 3. Variáveis explicativas
- Condição com 3+ termos ou com termo que exige conhecimento de domínio ganha nome:
```
const isWithinGracePeriod = daysSinceExpiration <= GRACE_PERIOD_DAYS;
const hasActiveException = exceptions.some((e) => e.active);
if (isWithinGracePeriod || hasActiveException) { ... }
```
- Expressão aritmética com fórmula de negócio ganha nome por termo (`netPrice = listPrice - discount + tax`).
- Cuidado com variável explicativa que não explica (`const check = a && b`). O nome diz a regra de negócio, não "check".

## 4. Naming: protocolo de avaliação
1. O nome diz a intenção sem abrir o corpo?
2. O corpo faz exatamente o que o nome diz, nem mais, nem menos? Se faz mais: nome mentindo (MAJOR). Se o nome inclui "And" (`validateAndSave`), são duas funções.
3. O termo é o mesmo que o repo usa para o conceito? `grep -rn "<termo>"` nos arquivos existentes. Um conceito, um termo.
4. A unidade está clara (Ms, Seconds, Cents, Bytes, Percent)?
5. O booleano lê como pergunta (`is/has/should/can/was/will`)?
6. A função tem verbo, o dado tem substantivo, a classe tem substantivo, o tipo tem substantivo?
7. Existe antônimo consistente (`add/remove`, `start/stop`, `open/close`, `enable/disable`)? `add`/`delete` no mesmo par é inconsistência MINOR.
- Lista de nomes de baixa informação: `data`, `info`, `item`, `obj`, `thing`, `stuff`, `temp`, `tmp`, `foo`, `result`, `value`, `val`, `ret`, `list`, `arr`, `map`, `flag`, `status`, `type`, `manager`, `handler`, `helper`, `util`, `utils`, `common`, `misc`, `service` sem qualificador, `process`, `handle`, `do`, `run`, `execute`. Reporte quando há nome específico no domínio.
- Agrupe nomes ruins do mesmo arquivo num achado só.
- Sugestão de renome cita o nome concreto e lista os usos no repo (`grep -rn`).

## 5. Linguagem ubíqua
- Termos do domínio educacional vigentes: aluno, turma, matrícula, cronograma, curso, disciplina, módulo, aula, prova, nota, certificado, trilha, pack, professor. Use o termo do repo. Mistura de `student`/`aluno`, `class`/`turma`, `enrollment`/`matrícula`/`subscription` para o mesmo conceito é achado.
- Idioma do identificador segue o idioma dominante do módulo. Termo de domínio em PT-BR dentro de código em inglês é aceito quando o repo já faz isso.
- Termo técnico e termo de domínio não se misturam no mesmo nome (`studentDto`, `turmaService` é aceitável; `studentTurmaMap` com os dois idiomas é achado quando o módulo todo usa um).
- Sigla de domínio vale uma definição no primeiro uso (nome de tipo ou comentário one-liner).

## 6. Magic values
- Número ou string literal com significado de negócio ganha constante nomeada, com unidade no nome.
- Exceções: `0`, `1`, `-1`, `2` (par/ímpar), `100` (percentual) e `1000` (ms) em contexto óbvio, índices e status HTTP no ponto de uso.
- A mesma constante em 2+ lugares é de review-dry. Registre em `handoffs`.
- Regex: nome na constante, partes compostas por `new RegExp([...].join(''))` quando passa de ~60 caracteres, e teste de exemplos aceitos e recusados no PR.
- Chave de feature flag, nome de evento de analytics e rota em string solta: constante ou enum no módulo dono (review-dry cobre a repetição).

## 7. Ordem e colocalização
- Step-down: nome do conceito de alto nível primeiro, detalhes abaixo, na ordem das chamadas. Em linguagens com hoisting de função, o leitor desce lendo; em linguagens sem hoisting (Python, `const fn =`), a ordem inversa é obrigatória pela linguagem e não se reporta.
- Colocalização: tipo, constante e helper usados por um consumidor ficam com ele. Arquivo `utils`/`helpers`/`constants` compartilhado por 10+ consumidores sem relação vira depósito.
- Imports: o formatter ordena. Reporte só import circular ou profundo, que é tema de review-modularidade.
- Arquivo com mais de ~300 linhas no diff, com seções sem relação, perde o mapa. Sugira a divisão por conceito.

## 8. Clareza de expressão
- Prefira o idioma direto. `x ? true : false` vira `x` (se booleano). `if (x === true)` vira `if (x)`. `arr.length > 0` ou `arr.length` com intenção explícita, e nunca `arr.length &&` em JSX (renderiza `0`).
- `reduce` só para dobrar em valor único e simples. Para montar objeto com lógica, `for...of` com `const` nomeados.
- Operadores de coalescência em cadeia de 4+ (`a ?? b ?? c ?? d ?? e`) escondem a regra de prioridade. Função com nome (`resolveCourseName`).
- Booleano posicional na chamada (`fn(x, true, false)`): objeto nomeado ou duas funções.
- Efeito colateral dentro de expressão (`items.map((i) => { total += i.price; return i; })`): trocar por `reduce`/`for`. O dono do side effect é review-clean.
- `try/catch` que envolve 40 linhas: reduza ao trecho que falha.
- Callbacks aninhados em 3 níveis: `async/await` ou funções nomeadas.
- Mensagem de erro e de log com texto que localiza o caso (`"Matrícula ${id} sem turma ativa"`). `"Erro"`/`"Falha ao processar"` falha o teste de 5 minutos de quem lê o log. Observabilidade em si é de review-observabilidade.

## 9. O que não entra aqui
- Renderização, performance, segurança, tipos, contrato: outros donos.
- Preferência pessoal sem custo de leitura (aspas, ponto e vírgula, largura de linha, trailing comma, ordem de imports, espaços): formatter.
- Comentários: review-comentarios. O ponto de contato: quando a causa do comentário é nome ruim, o achado é o nome (aqui) e a remoção do comentário vai em `handoffs`.

## 10. Como escrever o achado
- `evidence`: o trecho literal, com 15 linhas no máximo.
- `problem`: o custo de leitura em fato. Exemplo: "o nome promete consulta e o corpo escreve no banco (linha 27); 4 callers usam como consulta". Exemplo: "complexidade cognitiva 19: 3 níveis de `if` dentro de `for`, 2 ternários".
- `fix`: o código reescrito, ou o renome com a lista dos usos. "Simplifique" é inválido.
- `auto_fixable: true` apenas para renome local sem uso externo, extração de constante e inversão de `if` sem mudança de comportamento.
- Renome de símbolo exportado muda API pública: `auto_fixable: false`, e liste os consumidores em outros arquivos.
