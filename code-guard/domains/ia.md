# Domínio: IA (LLM)

- [IA] Output do LLM é dado não confiável: nunca vai para `eval`, SQL cru, shell ou HTML sem sanitizer. — origem: review-ia/output-inseguro
- [IA] RAG filtra por tenant, turma e permissão derivados da sessão, nunca do prompt. — origem: review-ia/rag-sem-tenant
- [IA] Chave do provedor fica só no servidor. — origem: review-ia/segredo
- [IA] Tool de escrita irreversível exige confirmação humana, e o ID vem da sessão, nunca do modelo. — origem: review-ia/excessive-agency
- [IA] Dado sensível de usuário vai ao provedor só com base legal e minimizado. — origem: review-ia/pii
- [IA] Saída estruturada usa tool use ou schema validado; nunca regex sobre texto livre. — origem: review-ia/saida-estruturada
- [IA] Loop de agente tem `maxIterations` e orçamento de tokens. — origem: review-ia/loop-sem-limite
- [IA] Chamada de LLM tem timeout e cancelamento. — origem: review-ia/timeout
- [IA] `stop_reason` é checado; truncamento não passa como resultado completo. — origem: review-ia/truncamento
- [IA] Mudança de prompt ou de modelo vem com eval set. Prompt fica em arquivo próprio, fora do código. — origem: review-ia/eval
- [IA] Resposta de domínio clínico tem grounding e citação. — origem: review-ia/alucinacao
- [IA] Histórico de conversa tem limite, e endpoint com custo tem limite por usuário. — origem: review-ia/custo
