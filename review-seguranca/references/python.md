# Segurança em Python (FastAPI, Flask, Django, scripts)

## Injeção e execução

- **SQL.** `cursor.execute(f"... {v}")`, `"..." % v`, `.format`, `text(f"...")` no SQLAlchemy, Django `.raw(f"...")`, `.extra(where=[...])`, `RawSQL` com input. Correção: parâmetros (`execute(sql, (v,))`, `text("... :v").bindparams(v=v)`, `.raw(sql, [v])`). Nome de coluna dinâmico: allowlist.
- **Comando.** `os.system`, `subprocess.run(cmd, shell=True)`, `os.popen`, `commands.getoutput` com input. Correção: `subprocess.run([bin, *args], shell=False)`, `shlex.quote` só quando shell é inevitável.
- **Código.** `eval`, `exec`, `compile` com input, `__import__(user)`, `importlib.import_module(user)`.
- **Desserialização.** `pickle.loads`, `marshal`, `shelve`, `yaml.load(x)` sem `Loader=SafeLoader` (use `yaml.safe_load`), `jsonpickle.decode`, `torch.load` sem `weights_only=True` em arquivo não confiável. Impacto: RCE. Correção: JSON com schema.
- **Template.** Jinja2 `Template(user_string).render()` e `render_template_string(user)`: SSTI. `Environment(autoescape=False)`. Correção: template fixo, `select_autoescape()`, `SandboxedEnvironment` quando o usuário edita template.
- **XML.** `xml.etree`/`lxml` com entidades externas (XXE) em XML de usuário. Correção: `defusedxml`, `resolve_entities=False`.
- **Path.** `open(os.path.join(base, user))`, `send_file(user)`, `tarfile.extractall()`/`zipfile.extractall()` sem validar membros (zip slip; Python ≥ 3.12 aceita `filter='data'`). Correção: `Path(base).joinpath(name).resolve().is_relative_to(base)`.
- **SSRF.** `requests.get(user_url)`, `httpx.get`, `urllib.request.urlopen(user)` (aceita `file://`). Correção: allowlist de host, bloquear IP privado pós-resolução (`ipaddress.ip_address(...).is_private`), `allow_redirects=False`, `timeout`.
- **Regex DoS.** `re` com quantificador aninhado sobre input. Correção: `re2`, limite de tamanho.

## AuthN/AuthZ por framework

- **FastAPI.** Rota sem `Depends(get_current_user)` (ou sem dependência no `APIRouter(dependencies=[...])`) é aberta. Parâmetro `user_id: int` na rota usado direto na query: BOLA. Use o id do usuário autenticado ou confira ownership. `response_model` define o que sai: ausente, o ORM model serializa tudo. Pydantic com `extra='allow'` ou `model_dump()` direto em `update` gera mass assignment. Correção: `extra='forbid'`, campos explícitos, `model_dump(exclude_unset=True)` sobre schema de update restrito.
- **Flask.** Rota sem `@login_required`/decorator próprio. `app.run(debug=True)` expõe o console Werkzeug (RCE). `SECRET_KEY` fraca ou literal. Cookie de sessão sem `SESSION_COOKIE_SECURE/HTTPONLY/SAMESITE`. `request.args.get` sem validação em query.
- **Django.** `DEBUG = True`, `ALLOWED_HOSTS = ['*']`, `SECRET_KEY` literal, `@csrf_exempt` em view mutante com sessão por cookie, `mark_safe(user)`, `|safe` em template com input, `ModelForm` com `fields = '__all__'` ou `exclude` (mass assignment), `queryset = Model.objects.all()` em DRF `ViewSet` sem `get_queryset` filtrado por usuário e sem `permission_classes`. `AllowAny` em view nova. `SECURE_*`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` ausentes em settings de prod.
- **DRF.** `serializer = XSerializer(data=request.data)` com `fields = '__all__'` expõe e aceita campos privilegiados. `read_only_fields` para `owner`, `role`. `PrimaryKeyRelatedField(queryset=Model.objects.all())` permite vincular a recurso alheio: restrinja o queryset ao usuário.

## Segredos e criptografia

- `SECRET_KEY`, `API_KEY`, `password` literais. `os.environ.get('KEY', 'default-inseguro')`. `.env` versionado.
- `hashlib.md5/sha1` para senha. Correção: `argon2-cffi`, `bcrypt`, `passlib`. Para checksum não sensível, aceitável.
- `random.*` para token/código. Correção: `secrets.token_urlsafe(32)`, `secrets.randbelow`.
- `==` para comparar token/HMAC. Correção: `hmac.compare_digest`.
- `jwt.decode(token, options={"verify_signature": False})`, `algorithms` ausente em `jwt.decode` (PyJWT): BLOCKER.
- `ssl._create_unverified_context`, `verify=False` em `requests`, `urllib3.disable_warnings()`. MAJOR em produção.
- `assert` para checagem de autorização ou validação: removido com `python -O`. Correção: `raise`.

## Bibliotecas de dados e IA

- `pandas.read_pickle`, `read_csv` de URL do usuário, `df.eval/query` com input (injeção de expressão).
- `langchain` com `PythonREPLTool`, `eval` sobre saída de LLM: handoff para review-ia, achado de execução arbitrária é seu quando há sink explícito.
- Notebooks (`.ipynb`) com saída contendo token, e-mail, dado de aluno: remova a saída (`nbstripout`).

## Supply chain Python

- `requirements.txt` sem pin e sem hash, `pip install` de URL git, `--extra-index-url` (dependency confusion), `--trusted-host`. Correção: `--index-url` único, hashes (`pip-compile --generate-hashes`).
- Pacote novo com nome parecido com conhecido (`python-dateutil` vs `dateutil`, `requests` vs `reqeusts`). Confira PyPI.
- `setup.py` com código no import ou `cmdclass` customizado em dependência nova.

## Falsos positivos frequentes

- `subprocess.run([...], shell=False)` com lista fixa.
- `yaml.load` com `SafeLoader` explícito.
- `assert` em testes.
- `hashlib.sha256` para chave de cache, ETag, deduplicação.
- `random` para amostragem, jitter, dados de teste.
- `DEBUG = True` em `settings/local.py` que o deploy não carrega. Confirme qual settings o deploy usa.
