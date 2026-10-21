# Contratos com LLM: o schema como fronteira

Escopo: forma do dado. Prompt, injection, custo, retry de reparo e refusal são do review-ia.

## Saída estruturada

- Sinal: `JSON.parse(completion.choices[0].message.content)` ou `JSON.parse(response.text)` sem schema. Impacto: o modelo devolve texto fora do JSON, cerca de markdown (```json), campo faltando ou tipo trocado, e o parse falha ou passa com dado errado. Correção: pedir saída estruturada ao provedor e validar o resultado no código.
- `openai`: `response_format: { type: "json_schema", json_schema: { name, strict: true, schema } }` ou helper `zodResponseFormat(Schema, "name")` com `client.beta.chat.completions.parse(...)`. O resultado está em `message.parsed`, que pode ser `null` em refusal.
- `@google/genai`: `config: { responseMimeType: "application/json", responseSchema }` e parse de `response.text` com o schema local.
- `@anthropic-ai/sdk`: tool use com `input_schema`, `tool_choice: { type: "tool", name }`. O resultado está em `content[].input`. Valide com o schema local, porque o `input` chega como `unknown`.
- Modo strict do provedor suporta um subconjunto de JSON Schema (por exemplo, sem `minLength`, com `additionalProperties: false` obrigatório e todos os campos em `required`). Validação local continua necessária para limites e regras de negócio.
- Sinal: schema do provedor e schema zod escritos separados. Impacto: drift. Correção: derivar um do outro (`zodResponseFormat`, `z.toJSONSchema`).
- Sinal: enum do schema pede valores livres (`category: string`). Correção: `enum` fechado, com `"other"` como saída de escape.

## Tool calls

- Sinal: argumentos de tool call usados sem validação (`JSON.parse(toolCall.function.arguments)` direto na função). Impacto: argumento inventado ou ausente chega ao código. Correção: `ArgsSchema.safeParse` antes de executar, e devolver o erro de validação ao modelo como resultado da tool.
- Sinal: nome da tool no código diferente do nome declarado ao modelo. Impacto: chamada sem handler.
- Sinal: definição de tool alterada (nome, parâmetros) com conversas persistidas que referenciam a versão antiga. Impacto: histórico inválido. Correção: versionar a tool.

## MCP

- Tool exposta por servidor MCP tem `inputSchema` (JSON Schema) como contrato público. Sinal: renomear a tool ou alterar parâmetro obrigatório. Impacto: clientes e prompts que referenciam a tool quebram. Correção: tool nova, antiga marcada como depreciada na `description`.
- Sinal: `outputSchema` declarado e `structuredContent` devolvido divergente. Impacto: clientes que validam rejeitam.

## Envelope de resposta da própria API

- Sinal: endpoint que devolve o texto bruto do modelo como corpo (`{ answer: string }`) e o front interpreta markdown ou JSON dentro dele. Impacto: o front passa a depender do formato que o modelo escolher. O contrato do renderer (conjunto de recursos de markdown permitidos) e o prompt do agente mudam juntos. Correção: campos estruturados no response (`{ answer, citations[], actions[] }`) e lista fechada do que o renderer aceita.
- Campo de metadado (`model`, `finishReason`, `usage`) no response: registrar se faz parte do contrato público.
