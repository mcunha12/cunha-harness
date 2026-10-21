# Contratos em Python

## Pydantic e FastAPI

- Sinal: handler FastAPI com `body: dict` ou `Request` lido com `await request.json()`. Impacto: sem validação e sem OpenAPI. Correção: modelo Pydantic.
- Sinal: `response_model` ausente. Impacto: o retorno inteiro sai, inclusive campos internos. Correção: `response_model=FooOut` (ou `response_model_exclude_unset` com cuidado).
- Sinal: o mesmo modelo para entrada e saída (`Foo` com `id`, `password_hash`). Correção: `FooIn`, `FooOut`, `FooDb` separados.
- Sinal: `model_config = ConfigDict(extra="allow")` em entrada de usuário. Impacto: campo arbitrário passa. Em resposta de terceiro, `extra="ignore"` (default) é o tolerant reader desejado.
- Sinal: `Optional[X]` sem default (`x: Optional[int]`). No Pydantic v2 o campo é obrigatório e aceita `None`. No v1 era opcional. Verifique a versão em `pyproject.toml` e a intenção do contrato.
- Sinal: `float` para dinheiro. Correção: `Decimal` com `condecimal` e serialização em string, ou inteiro em centavos.
- Sinal: `datetime` sem fuso (`naive`). Correção: `AwareDatetime` (v2) ou validator que rejeita naive.
- Sinal: `Enum` de entrada fechado e valor novo vindo de terceiro. Mesma lógica do tolerant reader: `str` com validação de domínio em ramo próprio.
- Sinal: `Literal[...]` e union sem `Field(discriminator="type")`. Impacto: erro ilegível e parse lento.
- Sinal: `model_validate_json` ausente onde o dado vem de bytes. Usar `model_validate_json(raw)` evita um parse intermediário.
- Sinal: o endpoint muda `response_model` (campo removido ou renomeado). Aplicam-se as regras de breaking change. `alias`, `validation_alias` e `serialization_alias` alteram o nome na fronteira: confira qual direção mudou.

## Django REST Framework e Flask

- Sinal: `Serializer` com `fields = '__all__'`. Impacto: coluna nova vira campo público. Correção: lista explícita.
- Sinal: `request.data` ou `request.GET` lidos sem serializer ou schema (marshmallow, pydantic).
- Sinal: mudança de `to_representation` sem checar consumidores.

## Tipos e OpenAPI

- FastAPI gera o OpenAPI do código. Sinal: `openapi.json` commitado e não regenerado no diff. Correção: regenerar.
- Sinal: `TypedDict` na borda sem validação. `TypedDict` não valida em runtime. Correção: modelo Pydantic ou `TypeAdapter(...).validate_python(...)`.

## Mensageria e jobs

- Sinal: task Celery, consumidor Kombu ou handler de fila com argumentos alterados (assinatura da task). Impacto: mensagens enfileiradas com a assinatura antiga falham após o deploy. Correção: aceitar os dois formatos (`*args`, defaults), drenar, depois remover.
- Sinal: `pickle` como serializer de mensagem. O risco de segurança é do review-seguranca. O contrato quer JSON com schema.
