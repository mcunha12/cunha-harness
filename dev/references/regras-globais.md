# Regras globais da /dev

Vêm do `~/.claude/CLAUDE.md` do Marcelo, aprovadas uma a uma em 12/11/2026. Valem para o orquestrador e para todo subagent. Quem instala a /dev recebe estas regras sem precisar do CLAUDE.md dele.

## 1. Escrita

### STE Operacional

Vale para tudo o que a /dev escreve: mensagens, spec, plano, resumo, commit, descrição de MR.

1. Abra com a resposta, a decisão ou a ação. Contexto depois, se precisar.
2. Uma ideia por frase. Frase curta.
3. Voz ativa, com o sujeito nomeado: "o BFF grava a decisão".
4. Presente para fato. Imperativo para procedimento.
5. Uma palavra, um significado. A mesma coisa mantém o mesmo nome.
6. Número no lugar de qualificador. Sem o número, diga que não tem.
7. Fato, depois consequência.
8. Diga sempre o que é medido e o que é hipótese.
9. Corte: preâmbulo, resumo de fechamento, narrativa do próprio processo, escopo além do pedido, nome de tabela e mecânica de ferramenta em texto para leitor não técnico, adjetivo de enfeite, tom de marketing.
10. Dois testes por frase: muda o que o leitor faz? Serve ao leitor ou a quem escreveu? Corte se falhar em um.

### Anáfora correcional

Proibido negar uma coisa para afirmar outra, em qualquer idioma e texto.

| Proibido | Escreva |
|---|---|
| "O problema não é a atribuição. É a cobertura." | "O problema é a cobertura." |
| "A régua é por matrícula, não por pessoa." | "A régua é por matrícula." |
| "Atribuição? Não. Cobertura." | "O tema é cobertura." |

O contraste só vale quando o leitor tem a crença errada. Nesse caso, dois fatos simples: "A régua de hoje é por pessoa. A nova é por matrícula."

### Texto de produto sóbrio

1. Sem métrica de vaidade. Fica o número perto da operação e do usuário (envios, pessoas), sai volume de plataforma (exibições).
2. Sem abertura narrativa: "Isso não é sorte:", "O risco é concreto.", "Vale registrar". Diga o fato.
3. Sem rótulo estrutural em negrito que anuncia o argumento ("**Balanceamento: não.**"). Contar uma lista pode ("Cinco limites.").
4. Um recorte por achado. Sem repetir o mesmo achado com outro denominador.
5. Sem prova de que o atual já funciona. A spec descreve o que muda.
6. Sem categoria pequena demais para agir.
7. Limite e incerteza ficam, em 1 frase. Ressalva que muda a ação do leitor fica. Ressalva que defende o método de quem escreveu sai.

### Comentário de código

1. Comentário só em 1 linha, em qualquer linguagem. Nada de bloco, nem JSDoc.
2. Se precisa de mais de 1 linha, melhore o nome ou extraia um helper com nome bom.

## 2. Código e git

### Nunca reverter edição de outra pessoa

1. Releia o arquivo imediatamente antes de todo write. A leitura de antes não vale.
2. Monte o conteúdo novo em cima do que voltou da releitura.
3. Vale para cada destino, um por um, inclusive arquivo que a própria /dev criou.
4. Se escreveu sem reler, diga na hora qual write foi e como recuperar.

### Verificação

1. Projeto com type-check (tsc, pyright, mypy) ou lint (eslint, ruff, oxlint): rode depois de editar, antes de dizer pronto.
2. Não diga pronto sem verificar.

### Busca em rename

Em rename ou mudança de assinatura, busque separado: chamada direta, referência de tipo, string literal, import dinâmico, re-export, barrel, mock de teste. Resultado pequeno demais: refaça com escopo menor, assuma truncamento.

### Git sem main

1. Nunca commit, push ou merge em `main` ou `master`.
2. Pedido de commit na main: confirme com o Marcelo e assuma branch de feature.

## 3. Testes e tarefa grande

### Testes só do que mudou

1. Rode só os testes dos arquivos alterados e dos consumidores diretos, por nome de arquivo.
2. Paralelismo limitado em toda execução (`--maxWorkers=2`).
3. Nunca a suíte inteira: ela trava a máquina. A suíte inteira fica no CI.

### Test-audit

1. Antes de escrever cada teste, decida pelos critérios da `test-audit` se ele deve existir.
2. Pule teste tautológico, change-detector (classe CSS, copy, constante, config, texto de SQL), unitário fora das exceções e mock de fronteira que só prova o fake.
3. Na /dev, os testes entram no fim da feature (SKILL.md, regra 12), pelo `prompts/final-tests.md`.
4. Quando `superpowers:test-driven-development` conflita com a `test-audit`, a `test-audit` ganha.

### Tarefa grande em fases

1. Refatoração em fases de até 5 arquivos. Termine e verifique cada fase antes da próxima.
2. Arquivo acima de 300 linhas: remova import, export e prop mortos antes, em passo separado.

### Releitura em arquivo grande

1. Conversa com 10 mensagens ou mais: releia o arquivo antes de editar.
2. Arquivo acima de 500 linhas: leia em partes com offset e limit.
3. Depois de editar, confira a mudança.

## 4. UI e QA

### UI headless em 3 telas

1. Todo trabalho de UI (construção, review, QA) roda em navegador headless. Nunca abra janela visível.
2. O navegador de QA é o `agent-browser` (skill `agent-browser-core`). Nunca `--headed`. Tamanho com `agent-browser set viewport <w> <h>`.
3. Confira 3 tamanhos: celular 375×667, tablet 768×1024, desktop 1280×720. A ordem vem da prioridade de tela da spec.
4. Siga o caminho real de cliques. Estado forçado não conta.
5. Tire screenshot de cada tela alterada e olhe antes de dizer pronto. Diga quais tamanhos conferiu.
6. Todo prompt de subagent de UI carrega estas regras.

### Fast QA

QA exploratório por agente levava de 12 a 40 min por caso. Com estas regras, cerca de 2 min.

1. Sirva build de produção (`next build` + `next start`), nunca `next dev`. Um rebuild por lote de correções.
2. Um script por caso (Playwright, headless, caminho real de cliques). Ele imprime métricas em JSON e passou ou falhou por passo, e salva screenshots. O agente de QA roda o script; não explora clicando.
3. Teto de 30 s por passo. Na falha, screenshot e próximo passo.
4. Fluxo inteiro no tamanho prioritário da spec. Nos outros dois, screenshot só das telas alteradas.
5. Meça o "antes" uma vez e guarde o número. Nunca troque de commit no meio do QA para medir de novo.
6. Guarde os scripts e reaproveite na rodada seguinte.
7. Um navegador e um servidor por vez. Sem type-check nem build durante o QA.
8. Nunca use `timeout` no macOS: o comando não existe e a saída vazia parece sucesso.

## 5. Custo

### Custo de contexto

1. Todo evento de Monitor ou poll relê o contexto inteiro. Com 500k de contexto, 1 evento custa cerca de US$ 0,75.
2. Comando longo roda com `run_in_background` e avisa na saída. Não faça poll.
3. Monitor só com filtro (`grep --line-buffered 'ERROR\|FAIL\|PASS\|Done'`). Nunca `tail -f` de log inteiro.
4. Autocompact dispara em 256k. Orquestrador enxuto: resumo de agente, nunca dump de arquivo.
5. Opus julga, Haiku lê: o agente Opus recebe só o pacote de evidência (trechos com `file:line`), coletado por um agente Haiku.

### Modelo mais barato

1. Escolha o modelo e o esforço mais baratos que não comprometem a qualidade.
2. Julgue por custo por task terminada. Modelo barato que pede retrabalho ou correção por um modelo mais forte custa mais.
3. A tabela de modelos da SKILL.md, seção 4, continua valendo.
