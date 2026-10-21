# IA — TypeScript

Carregue quando o repo tem `tsconfig*.json` ou `typescript` nas deps.

## Tipagem da fronteira com o modelo

- Saída do modelo chega como `string` ou `unknown`. `JSON.parse(text) as Quiz` é `as` mentiroso: o compilador aceita e o runtime não garante. Correção: schema zod como fonte única do tipo e do parse.

```ts
const QuizSchema = z.object({
  questions: z.array(z.object({
    stem: z.string().min(10).max(2000),
    options: z.array(z.string()).length(4),
    answerIndex: z.number().int().min(0).max(3),
  })).min(1).max(20),
});
type Quiz = z.infer<typeof QuizSchema>;

const parsed = QuizSchema.safeParse(JSON.parse(text));
if (!parsed.success) return repair(parsed.error.issues);
```

- `JSON.parse` lança em texto inválido: `try/catch` com ramo de reparo. `safeParse` não cobre o `JSON.parse`.
- Tipos de tool: `args` como `unknown`, validados pelo schema da tool antes do handler. Um mapa tipado liga `name` ao schema e ao handler:

```ts
const tools = {
  getLesson: { schema: z.object({ lessonId: z.string().uuid() }), run: (a: { lessonId: string }, ctx: Ctx) => lessons.get(a.lessonId, ctx.userId) },
} as const;
type ToolName = keyof typeof tools;
function isToolName(n: string): n is ToolName { return Object.hasOwn(tools, n); }
```

- `Object.hasOwn`/`Map.has` na seleção da tool. `tools[name]` com `name` vindo do modelo acessa `constructor`, `__proto__` e `toString` em objeto literal. Use `Map` ou `Object.hasOwn`.
- `ctx.userId` vem da sessão, fora do schema exposto ao modelo.
- Union discriminada para resultado de chamada: `{ kind: 'ok'; data } | { kind: 'truncated' } | { kind: 'refusal'; text } | { kind: 'blocked' }` com `switch` exaustivo e `assertNever`. Obriga o chamador a tratar os ramos.
- `finish_reason` e `stop_reason` tipados como union do SDK: `switch` exaustivo.
- Non-null assertion em `choices[0].message.content!`: o valor é `null` em refusal e em tool call. Trate.

## Segurança de renderização

- `dangerouslySetInnerHTML={{ __html: answer }}` com resposta do modelo: BLOCKER sem sanitização.
- `react-markdown` com `rehype-raw` sem `rehype-sanitize`: HTML bruto da resposta é renderizado. Correção: remova `rehype-raw` ou adicione `rehype-sanitize` com schema restrito.

```tsx
<ReactMarkdown
  rehypePlugins={[[rehypeSanitize, schema]]}
  components={{ a: SafeLink, img: () => null }}
>{answer}</ReactMarkdown>
```

- `SafeLink` valida protocolo (`https:`), host em allowlist, `rel="noopener noreferrer"` e `target="_blank"` consciente. `javascript:` e `data:` bloqueados. `img` remoto removido ou proxied, pois imagem por URL vaza contexto na query.
- Markdown do modelo com tabela, código e links: o conjunto de elementos permitidos é a allowlist do produto (por exemplo, a lista de recursos suportada pelo renderer deve acompanhar a lista que o prompt autoriza o modelo a usar).
- Streaming parcial: Markdown incompleto renderiza mal; sanitize a cada atualização.

## Chamadas e cancelamento

```ts
const ac = new AbortController();
req.on('close', () => ac.abort());
const res = await client.chat.completions.create({ model: cfg.model, messages, max_tokens: 800 }, { signal: ac.signal, timeout: 30_000 });
```

- Sem `signal` ligado ao request, o cliente que fecha a aba não interrompe a geração: o provedor cobra os tokens inteiros.
- `AbortError` do SDK não é falha de negócio: não reporte ao monitoramento de erro.
- `for await (const chunk of stream)` com `try/finally` que fecha o stream e libera recursos; erro no meio do stream chega como exceção na iteração.
- `Promise.all` de N chamadas de LLM sem limite de concorrência: `p-limit`.
- Em Nest, `@Sse` ou `StreamableFile` com `Observable`: `finalize` cancela a chamada do provedor quando o cliente desconecta.

## Config e segredos

- `process.env.OPENAI_API_KEY` lido no servidor. Em Next.js, variável sem `NEXT_PUBLIC_`. Em Vite, `import.meta.env.VITE_*` vai ao bundle: chave de provedor nunca.
- Em app com `window.env` injetado, qualquer valor ali é público.
- Validação de config no boot com zod: `LLM_MODEL`, `LLM_TIMEOUT_MS`, `LLM_MAX_TOKENS` com defaults seguros.
- Model ID em um único módulo de config exportado e tipado:

```ts
export const LLM = { quizModel: env.LLM_QUIZ_MODEL, tutorModel: env.LLM_TUTOR_MODEL } as const;
```

## Prompts em TypeScript

- Template literal com `${userInput}` dentro do bloco `system`: injection. Mantenha em `user`.
- Função de montagem de prompt pura e testável:

```ts
export const PROMPT_VERSION = 'tutor@3';
export function buildTutorMessages(question: string, chunks: Chunk[]): Message[] { /* ... */ }
```

- `escapeTags(s)` neutraliza o delimitador (`</documento>`). Delimitador aleatório (`crypto.randomUUID()`) por request reforça.
- Constante de prompt grande dentro do handler recriada a cada request: mova para o módulo (também ajuda o prompt caching, pois o prefixo é idêntico).
- `JSON.stringify(user)` ou `${JSON.stringify(entity)}` no prompt: minimize campos (`pick`).
- Evite `as const` sobre strings de prompt que variam por request.

## Testes

- Mock do cliente LLM com respostas de refusal, truncamento (`finish_reason: 'length'`), JSON inválido, tool call com nome desconhecido e args malformados, e erro 429. Teste cada ramo (a escrita é do test-audit).
- Teste de regressão de injeção com texto adversarial em documento recuperado: a tool destrutiva não é chamada sem confirmação.
