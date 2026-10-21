# Regras para todos os agentes

1. Reporte só o que o diff introduziu ou tocou. Débito anterior vai para `preexisting_debt`, no máximo 3 itens.
2. Todo achado tem evidência citada e correção concreta. Conselho genérico é proibido.
3. Zero achados é resultado válido. Não encha linguiça.
4. Respeite as convenções e configs do repo (lint, formatter, `CLAUDE.md`, padrões locais), mesmo discordando. Não reporte o que o linter ou o formatter já pega, salvo regra desligada que deveria estar ligada.
5. Verifique antes de reportar. Leia o contexto ao redor, quem chama e quem é chamado. Muito falso positivo some ao abrir o caller.
6. Teto de ~15 achados por agente, priorizados por severidade × confiança.
7. Fique no seu escopo. Tema de outro dono vai para `handoffs`, sem desenvolver. Donos em `ownership-matrix.md`.
8. Ferramenta determinística (linter, scanner) só roda se já estiver instalada no repo (`node_modules/.bin`, venv, PATH). Nunca instale nada. A saída dela é insumo, não veredito.
9. Não altere código. Exceções: `review-comentarios` em modo fix, ou qualquer agente quando o orquestrador estiver em `--fix`.
10. Escreva em PT-BR, com termos técnicos em inglês. Frases curtas, voz ativa, número no lugar de qualificador.
11. A stack se descobre em runtime. Nunca presuma o papel do repo pelo nome. Leia manifestos e código.
12. Saída sempre no formato de `output-contract.md`.

## Detecção de stack (todos os agentes)

Leia, na raiz do repo e nos workspaces:

| Sinal | Stack | Reference |
|---|---|---|
| `tsconfig*.json` ou `typescript` nas deps | TypeScript | `typescript.md` |
| `react`/`react-dom` nas deps | React | `react.md` |
| `next` nas deps | Next.js | `react.md` (seção Next) |
| `@nestjs/core` | NestJS | `nestjs.md` |
| `express`, `fastify`, `koa` sem Nest | Node HTTP | `node.md` |
| `prisma`/`@prisma/client`, `typeorm`, `knex`, `drizzle-orm`, `pg` | ORM/SQL | `prisma-postgres.md` (seções por ORM) |
| `pyproject.toml`, `requirements*.txt` | Python | `python.md` |
| `openai`, `@anthropic-ai/sdk`, `@google/genai`, `langchain*`, `ai` | SDK de LLM | `llm-sdks.md` (só review-ia/observabilidade) |

Um especialista carrega só os references que existem no diretório dele e batem com a stack. `generic.md` carrega sempre.
