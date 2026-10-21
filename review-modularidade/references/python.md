# Modularidade em Python

- Camadas: router/view → service → repository. Router sem SQL e sem regra. Service sem objeto de request. Domínio sem SQLAlchemy/Django ORM quando o repo declara camada de domínio. Em Django clássico (fat models), o padrão local vale: reporte lógica em view que o model ou o service do app já cobre.
- Ciclos: `ImportError: cannot import name` ou import dentro de função para fugir. Correção: extrair módulo comum, `TYPE_CHECKING` só para anotação (`if TYPE_CHECKING: from x import Y`). Ciclo só de tipos sob `TYPE_CHECKING` é MINOR.
- API pública: `__init__.py` com `__all__` curto. `from pkg import *` e `__init__` que importa a árvore inteira: custo de import e ciclo. Nomes com `_` prefixados são privados por convenção. Import de `_privado` de outro pacote é deep import.
- Side effects no import: criar engine, abrir conexão, `load_dotenv()`, `boto3.client(...)`, registrar signals no topo do módulo. Correção: factory, `lifespan` do FastAPI, `AppConfig.ready()` do Django.
- Estado global: singleton de módulo (`settings = Settings()` com mutação), `global`. Pydantic `BaseSettings` lido uma vez e injetado (`Depends(get_settings)`) é o padrão.
- Vendor no domínio: tipos do `openai`/`stripe`/`boto3` em assinatura de função de regra. Correção: `Protocol` de porta com tipos próprios e adapter.
- Django: app A importando `models` internos de app B. Correção: service/selector público do app B (`selectors.py`, `services.py`). Signals entre apps para desacoplar com consciência do fluxo implícito.
- FastAPI: `Depends` aninhado entre routers de features diferentes, `APIRouter` importando outro router. Correção: dependência em módulo comum.
- Pacotes: `src/` layout com `pyproject.toml`. `sys.path.append` e import relativo fora do pacote: quebra de fronteira.
- Monorepo/multi-repo: código copiado de serviço irmão. Correção: pacote interno versionado (`pip install` de registry privado) ou geração a partir de OpenAPI.
- Ferramentas: `import-linter` (contracts `layers`, `forbidden`, `independence`), `pydeps --show-cycles`, `pylint --enable=cyclic-import`, `vulture` para código sem uso. Checagem: `command -v lint-imports pydeps pylint`.
