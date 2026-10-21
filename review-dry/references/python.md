# DRY em Python

- Regra de negócio: o mesmo cálculo em 2+ módulos. Busque pela fórmula e pelos literais (`grep -rn "0.75"`). Correção: função pura em módulo de domínio, importada.
- Validação: modelo Pydantic e `dataclass` com os mesmos campos escritos à mão. Correção: herança de modelo base (`class Update(Base)`), `model_copy`, `create_model`. Validadores `@field_validator` repetidos em 3 modelos pedem um tipo anotado reutilizável (`Annotated[str, AfterValidator(...)]`).
- Constantes: strings de status repetidas. Correção: `enum.StrEnum` (3.11+) ou `Literal` derivado de um `Enum`. Enum Python e Enum do ORM para o mesmo conceito: use um e referencie.
- SQLAlchemy/Django: o mesmo `filter`/`where` em vários métodos. Correção: queryset/manager customizado (`objects.active()`), método de repository, `hybrid_property`.
- Pydantic versus ORM: modelo de resposta que copia colunas da tabela. Correção: `model_config = ConfigDict(from_attributes=True)` e herança para os campos comuns.
- Decorators e dependências FastAPI/Flask: checagem de permissão repetida em endpoints. Correção: `Depends` reutilizável ou decorator único.
- Anti-DRY: função com `**kwargs` que repassa e muda comportamento por chave (`mode='a'|'b'`). Classe base com `NotImplementedError` herdada para reaproveitar 2 métodos. Prefira funções e composição.
- Gerador de código: `datamodel-code-generator` a partir de OpenAPI evita modelos copiados de outro serviço.
- Ferramentas: `pylint --enable=duplicate-code` (Checagem: `command -v pylint`) e `jscpd` com `--format python`.
