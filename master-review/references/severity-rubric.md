# Rubrica global de severidade

- **BLOCKER:** bug em produção, falha de segurança explorável, perda ou corrupção de dados, quebra de contrato com consumidor ou indisponibilidade provável. Bloqueia o merge.
- **MAJOR:** problema real com custo provável e relevante: degradação de performance mensurável, dívida que se propaga, risco plausível ou violação de arquitetura.
- **MINOR:** melhoria clara, de baixo risco, que vale fazer agora.
- **NIT:** preferência. Sai colapsada no relatório.

## Confiança

- **alta:** o código citado prova o problema. O contexto (caller, callee, config) foi lido.
- **media:** o problema depende de uma condição plausível que o diff não mostra (volume, configuração de runtime).
- **baixa:** hipótese. Diga o que confirmaria.

## Regras de combinação

- BLOCKER com confiança baixa vira MAJOR até ser confirmado.
- Severidade mede o impacto se o problema existir. Confiança mede a chance de ele existir. Não misture as duas.
- A rubrica de cada especialista refina esta. Em conflito, esta vence.

## Nível de prova (`proof_level`)

1. Afirmado pelo especialista.
2. `arquivo:linha` lido com o contexto.
3. O caso que tornaria o achado falso foi descartado no código.
4. Código rodado (script curto, teste, request) mostra o defeito.
5. Reproduzido no app pelo fluxo real.

BLOCKER exige nível 4 ou mais; abaixo disso, vira MAJOR com a nota "não provado (nível N)". MAJOR exige nível 2 ou mais.
