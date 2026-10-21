# Clean em Python

- Parâmetros: 4+ posicionais ou `*args, **kwargs` que repassam e mudam comportamento. Correção: `@dataclass(frozen=True)` de parâmetros, parâmetros `*` keyword-only (`def f(a, *, flag)`).
- Flag arguments: `def run(x, dry_run=False, force=False, verbose=False)`. Correção: funções separadas ou `Enum` de modo.
- Mutable default: `def f(items=[])`. Correção: `None` e criação no corpo. BLOCKER quando o default é compartilhado entre chamadas em código de servidor.
- Mutação de parâmetro: `list.sort()`, `dict.update()` no argumento. Correção: `sorted(...)`, `{**a, **b}`.
- Estado global: variável de módulo mutada por funções, `global` statement, singleton com atributo de request. Correção: injetar, `contextvars` para escopo por request.
- DIP: `requests.get`, `boto3.client`, `OpenAI()` e `datetime.now()` dentro da regra. Correção: parâmetro, `Protocol` mínimo, `clock: Callable[[], datetime]`.
- ISP/LSP: `Protocol` pequeno por consumidor. `ABC` com `raise NotImplementedError` em subclasse usada polimorficamente é LSP.
- Herança só para reuso: prefira composição. Mixins com estado: smell.
- Value objects: `@dataclass(frozen=True)` com `__post_init__` validando (CPF, dinheiro, período). `Decimal` para dinheiro, nunca `float`.
- Result: exceção tipada de domínio ou `Union[Ok, Err]`. `return None` com 3 significados: MAJOR.
- Fluxo: guard clauses, `match` (3.10+) para union discriminado, `assert_never` no default.
- CQS: `@property` que faz IO ou grava. Correção: método com verbo.
- FastAPI: lógica de domínio dentro do path operation. Correção: função/serviço puro chamado pela rota, `Depends` para dependências.
- Dead code: `vulture`. Complexidade: `radon cc -s -n C`.
