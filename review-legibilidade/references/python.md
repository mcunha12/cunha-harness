# review-legibilidade — Python

Mais curto que os outros. Regras que mudam em Python.

## 1. Nomes (PEP 8)
- `snake_case` para função, variável, módulo; `PascalCase` para classe; `UPPER_SNAKE_CASE` para constante de módulo. Desvio do padrão do repo: reporte se o linter (`ruff`, `flake8`) não cobre.
- Booleano `is_/has_/should_/can_`. Função com verbo. Evite `data`, `info`, `obj`, `item`, `tmp`, `res`, `val`, `lst`, `dct`, `mgr`.
- Unidade no nome: `timeout_seconds`, `price_cents`, `size_bytes`.
- Nome `_privado` com um underscore para uso interno. Dois underscores (`__x`) faz name mangling; use só quando precisa.
- Não sombreie builtins: `id`, `type`, `list`, `dict`, `filter`, `input`, `format`, `object`, `str`, `min`, `max`. Sombreamento de `id` em parâmetro vale MINOR e se resolve com `enrollment_id`.
- Termos do domínio no idioma do repo (`aluno`, `turma`, `matricula`), consistentes entre módulos.

## 2. Complexidade e fluxo
- Aninhamento acima de 3: guard clauses. `continue` no topo do loop em vez de `if` embrulhando 20 linhas.
- Comprehension com 2+ `for` ou 2+ condições, ou aninhada: loop com variáveis nomeadas, ou função geradora.
```python
# antes
result = [f(x) for row in matrix for x in row if x is not None and x.active if g(x)]
# depois
def active_cells(matrix):
    for row in matrix:
        for cell in row:
            if cell is not None and cell.active and g(cell):
                yield cell
result = [f(cell) for cell in active_cells(matrix)]
```
- `lambda` com lógica (ou atribuída a nome): `def` nomeado.
- Ternário `a if c else b` simples. Aninhado, não.
- `if x == True`, `if len(xs) == 0`, `if not x is None`: `if x`, `if not xs`, `if x is not None`. Cuidado: `if x` trata `0` e `""` como falso. Use `is None` quando `0` é valor válido (nota 0.0, progresso 0).
- Booleano posicional (`run(job, True, False)`): parâmetros keyword-only (`def run(job, *, dry_run, retry)`).
- `*args, **kwargs` repassados em 3 camadas escondem o contrato. Parâmetros nomeados, ou dataclass.
- Valor default mutável (`def f(items=[])`) é bug; cite como MAJOR e corrija com `None`.
- `try/except` amplo (`except Exception: pass`): custo de leitura e de correção (review-resiliencia é dono do tema; aqui, só o trecho que envolve linhas demais).

## 3. Clareza
- `dataclass`/`NamedTuple`/`TypedDict` com campos nomeados no lugar de tupla posicional `(a, b, c)` e dict sem forma. Tipo é de review-tipagem; aqui reporte a ilegibilidade de `row[2]`.
- Magic number: constante de módulo `UPPER_SNAKE`. Regex: `re.compile` com `re.VERBOSE` e comentário de parte, ou constante nomeada (`CPF_PATTERN`).
- f-string no lugar de `%` e `.format` em código novo, se o repo usa f-string.
- `enumerate` e `zip` no lugar de `range(len(x))`. `pathlib` no lugar de concatenação de string de caminho, conforme o repo.
- Import com `*` esconde a origem dos nomes.
- Ordem: constantes e tipos, funções públicas, helpers privados. Python não tem hoisting de função em tempo de import, mas a chamada em runtime resolve depois; a ordem step-down é aceita.

## 4. Docstring
- Docstring multilinha em função de projeto segue a regra do time para comentários (one-liner). Remoção é de review-comentarios; reporte aqui só nome ruim que levou ao docstring.

## 5. Ferramentas
- `ruff check --select C901,PLR0912,PLR0913,PLR0915,N <arquivos>` mede complexidade, ramos, argumentos, instruções e nomes, se `ruff` está instalado.
- `radon cc -s -n C <arquivos>` mede complexidade ciclomática; `radon` indica a função, o ranking C ou pior vale olhar.
- `pylint --disable=all --enable=invalid-name,redefined-builtin <arquivos>` quando `pylint` já está no projeto.
