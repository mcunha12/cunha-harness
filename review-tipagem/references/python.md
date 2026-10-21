# Tipagem em Python

## Configuração

- `pyright` em `strict` (ou `typeCheckingMode = "strict"` no `pyproject.toml`) ou `mypy --strict`. Sinal no diff: remoção de `strict`, `ignore_missing_imports = true` global, `# type: ignore` em bloco, `[[tool.mypy.overrides]]` com `ignore_errors = true` para módulo novo.
- Versão de Python (`requires-python`) define a sintaxe disponível: `X | None` (3.10+), `Self` (3.11+), `type` statement (3.12+). Antes disso, `typing_extensions`.

## Furos

- `Any` explícito e implícito: parâmetro sem anotação, retorno sem anotação em função pública, `dict` sem parâmetros (`dict[str, Any]` que é na verdade `dict[str, int]`), `json.loads` (devolve `Any`), `requests.Response.json()` (`Any`), `os.environ.get` (`str | None`).
- `cast(Foo, x)` sem checagem anterior é afirmação. Correção: `isinstance`, `TypeGuard`/`TypeIs`, ou validação Pydantic (`TypeAdapter(Foo).validate_python(x)`).
- `# type: ignore` sem código: `# type: ignore[arg-type]` com motivo em uma linha. `# pyright: ignore[reportArgumentType]` idem.
- `Optional[X]` sem narrowing: `x.attr` onde `x: Optional[X]`. Correção: `if x is None: raise ...` e o checker estreita. `assert x is not None` some com `python -O`; use `if/raise` em código de produção.
- Retorno `Optional[X]` e `X` misturados no mesmo contrato sem explicar.
- `*args: Any, **kwargs: Any` em wrapper que apaga a assinatura. Correção: `ParamSpec` e `TypeVar` em decorators:

```python
P = ParamSpec("P")
R = TypeVar("R")
def timed(fn: Callable[P, R]) -> Callable[P, R]: ...
```

- Default mutável (`def f(x: list[int] = [])`). O checker não pega, e o bug é clássico. Correção: `None` e criação dentro.
- `Callable[..., Any]` onde a assinatura é conhecida. Use `Protocol` com `__call__`.

## Modelagem

- `dict` com forma conhecida: escolha pela origem.
  - Dado externo (HTTP, fila, arquivo, LLM): Pydantic (`BaseModel`) valida em runtime.
  - Estrutura interna: `@dataclass(frozen=True, slots=True)`.
  - Interop com dict (JSON já validado, kwargs): `TypedDict`, que não valida em runtime.
- `Literal["a", "b"]` e `Enum` (`StrEnum` em 3.11+) para valores fechados. `str` solto aceita typo.
- `NewType("CourseId", str)` para IDs intercambiáveis, ou `Annotated[str, ...]` com Pydantic.
- `Protocol` para contrato estrutural: evita herança só para satisfazer o checker, e deixa o teste injetar um fake.
- Exaustividade: `match` com `case _: assert_never(x)` (`typing.assert_never` em 3.11+).
- Union discriminada no Pydantic: `Annotated[Union[A, B], Field(discriminator="kind")]`.
- `Final` e `ClassVar` para constantes e atributos de classe. `frozen=True` em dataclass de valor.
- `Sequence`/`Mapping`/`Iterable` em parâmetros que só leem. `list`/`dict` em retornos que o chamador pode mutar.
- `TypeVar("T", bound=Base)` quando a função usa método de `Base`. `TypeVar` sem bound usado uma vez é ruído.
- `Self` para métodos que retornam a própria classe.
- `overload` quando o retorno depende do argumento (literal, flag), em vez de `Union` que força `isinstance` no chamador.
- Generators e async: `Iterator[T]`, `AsyncIterator[T]`, `Awaitable[T]`. `async def` devolve `Coroutine`: chamar sem `await` é achado do review-resiliencia.

## Pydantic

- v2: `model_validate`, `model_dump`, `ConfigDict`. Sinal de mistura de v1 (`.dict()`, `class Config`, `@validator`). Verifique a versão em `pyproject.toml`.
- `Optional[int]` sem default é obrigatório e aceita `None` no v2.
- `model_config = ConfigDict(strict=True)` desliga coerção (`"1"` não vira `1`). Decisão de contrato, do review-contratos.
- `computed_field` e `property` tipados com retorno explícito.
- `TypeAdapter` para tipos que não são modelos (`list[Foo]`).

## Django e SQLAlchemy

- SQLAlchemy 2.0: `Mapped[int]`, `mapped_column()`. Sinal: `Column(Integer)` sem `Mapped` em código novo num repo 2.0 tipado. `session.execute(select(...))` devolve `Result[...]` tipado por `select`.
- Django com `django-stubs`: `QuerySet[Model]`, `Manager` tipado. `.get()` lança `DoesNotExist`, `.first()` devolve `Model | None`.
- `request.GET.get(...)` devolve `str | None`: converta e valide.
