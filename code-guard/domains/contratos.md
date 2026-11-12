# Domínio: contratos entre serviços

- [CTR] Campo de request opcional não vira obrigatório para clientes já em produção. — origem: review-contratos/CTR-BRK
- [CTR] Evento de fila muda de formato com versão; consumidor antigo continua funcionando. — origem: review-contratos/evento
- [CTR] Rota de escrita tem DTO com validação; nunca `@Body() body: any`. — origem: review-contratos/CTR-VAL
- [CTR] Dinheiro em centavos inteiros ou decimal; ID `bigint` serializado como string. — origem: review-contratos/representacao
- [CTR] Valor novo de enum em response só entra com consumidores que têm ramo default. — origem: review-contratos/enum
- [CTR] Erro usa status HTTP de erro, nunca 200 com corpo de erro. — origem: review-contratos/consistencia
- [CTR] Mudança de props host→remote define a ordem de deploy (remote compatível primeiro). — origem: review-contratos/ordem-de-deploy
