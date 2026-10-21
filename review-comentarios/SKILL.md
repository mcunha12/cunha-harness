---
name: review-comentarios
description: Revisa e corrige a higiene de comentários de um diff pela regra do time - comentário que não é one-liner sai, one-liner entra onde falta o porquê. Remove multi-linha, comentário que repete o código, código comentado, changelog, banner, comentário desatualizado e TODO sem dono. Acione em "revisa os comentários desse PR", "limpa os comentários", `/review-comentarios` ou via master-review na fase de correção. Único especialista que edita código, e só em comentários. Não cobre naming, complexidade e legibilidade do código (review-legibilidade) nem documentação em README, ADR ou wiki.
argument-hint: "[--base <branch>] [--path <glob>] [--uncommitted]"
---

# review-comentarios

## Missão

Aplicar a regra do time sobre comentários nas linhas que o diff adicionou ou tocou. Todo comentário vira one-liner. O que não cabe em uma linha sai do código e vai para README, ADR ou ticket. Onde falta o porquê de uma decisão não óbvia, o agente adiciona um one-liner. O agente produz um patch unificado que só altera comentários. Comportamento do código fica intacto.

## Regra do time

- Comentário de uma linha: permitido, e só quando explica o porquê.
- Comentário de duas linhas ou mais (bloco `/* */`, JSDoc multi-linha, docstring multi-linha, várias linhas `//` ou `#` seguidas): removido, ou condensado em um one-liner quando a informação for essencial.
- Se a explicação precisa de mais de uma linha, melhore o nome ou extraia uma função bem nomeada. Quando isso é o caminho, registre handoff para review-legibilidade.

## Escopo

### 1. Preservar sempre

Nunca remova, reescreva nem condense:

- Licença e copyright (`/*! ... */`, `@license`, `SPDX-License-Identifier`, `Copyright`).
- Diretivas e pragmas: `@ts-expect-error`, `@ts-ignore`, `@ts-nocheck`, `eslint-disable`, `eslint-enable`, `eslint-disable-next-line`, `prettier-ignore`, `istanbul ignore`, `c8 ignore`, `webpackChunkName`, `webpackIgnore`, `/* #__PURE__ */`, `/// <reference />`, `# noqa`, `# type: ignore[...]`, `# pylint: disable`, `# fmt: off|on`, `# pragma: no cover`, `# isort: skip`, `# mypy:`, `# pyright:`, `// @flow`, `// +build`, `//go:generate`, `//nolint`.
- Shebang (`#!/usr/bin/env node`) e coding (`# -*- coding: utf-8 -*-`).
- Marcador de arquivo gerado (`// Code generated ... DO NOT EDIT`, `@generated`, `AUTO-GENERATED`). Não revise arquivo gerado: pule o arquivo inteiro.
- Docblock consumido por ferramenta: Swagger/OpenAPI (`@ApiProperty`, `@swagger`, `@openapi`), docgen ativo (Storybook `@component`/`@description`/`@param` em `*.stories.*` e props de componente quando o repo usa `react-docgen`), TypeDoc/Sphinx/pdoc quando o repo gera a documentação (cheque `typedoc.json`, `docs/conf.py`, script `docs` no `package.json`), `@deprecated` (consumido por IDE e lint), JSDoc que serve de tipo em arquivo `.js` com `checkJs`.
- Comentário com marcador de ferramenta: `TODO(JIRA-123)`, `FIXME(JIRA-123)` com dono e ticket, `NOSONAR`, `@internal`, `@public`.
- Comentário dentro de string, template literal, fixture, snapshot, JSON/YAML de configuração com semântica (`# yamllint`, `# renovate:`, `# syntax=docker/dockerfile`).
- Cabeçalho de seção de arquivo de configuração (`# ---- Database ----` em `.env.example`, `docker-compose`, `nginx.conf`, Helm values) onde o repo adota esse padrão: preserve e não reporte.

### 2. Remover ou condensar

Cada categoria vira achado, com o trecho no `evidence` e o patch no `fix`.

| Categoria | Sinal | Ação |
|---|---|---|
| Multi-linha | 2 ou mais linhas consecutivas de comentário, `/** ... */` com 2+ linhas de texto | condensar em um one-liner com o porquê, ou remover |
| Repete o código | `// incrementa i`, `// retorna o usuário`, `/** Gets the name */ getName()`, `@param id the id` | remover |
| Código comentado | linhas de código sob `//` ou `#`, bloco `/* ... */` com statements | remover. O histórico está no git |
| Changelog | `// alterado por fulano em 12/03`, `// v2: agora faz X`, `// added for JIRA-123` sem porquê vigente | remover |
| Banner | `// ======`, `/*** SECTION ***/`, `// --------` | remover |
| Desatualizado | comentário descreve comportamento que o código do diff já não tem (parâmetro removido, ordem trocada, condição invertida) | corrigir para o comportamento atual em um one-liner ou remover |
| Mentiroso | comentário afirma o contrário do código (`// nunca nulo` com `?? null`) | corrigir ou remover. Severidade MAJOR |
| TODO sem dono | `TODO`, `FIXME`, `HACK`, `XXX` sem ticket | trocar para `// TODO(JIRA-123): ...` quando o ticket for conhecido pelo diff ou branch, senão remover e registrar no `problem` |
| Ruído de IA e de ferramenta | `// Step 1:`, `// Added by Claude`, `// Here we ...`, `// Now we ...`, `// This function ...` | remover |
| Separador de narrativa | `// First, ...` `// Then, ...` em sequência | remover. Se as etapas merecem nome, handoff para review-clean (extract function) |
| Marcador vazio | `//`, `/* */`, `#` sem texto | remover |

### 3. Adicionar um one-liner

Adicione só o porquê, nunca o que o código já diz. Cada adição é um achado `MINOR` (ou `MAJOR` quando a ausência esconde risco: segurança, perda de dados, ordem crítica).

- Workaround de bug de terceiro, com link ou versão: `// Workaround: react-query v3 deixa isLoading=false com enabled=false (ver issue #123)`.
- Regra de negócio não evidente: `// Aprovação exige nota >= 7 e frequência >= 75% (regulamento 2024)`.
- Invariante ou pré-condição que o tipo não expressa: `// Lista já vem ordenada por data desc do BFF`.
- Unidade e escala: `// em centavos`, `// timeout em ms`, `// minutos`.
- Justificativa de constante com valor arbitrário: `const REQUIRED_MINUTES = 600; // 10h exigidas pelo pos-api`.
- Intenção de regex: `// Aceita CPF com ou sem pontuação`.
- Ordem importa: `// Registrar antes do guard de auth, senão o request id some do log`.
- Hack de performance: `// Map evita O(n²) no cruzamento com 10k matrículas`.
- Alerta de segurança: `// Não logar: contém token do aluno`.
- Efeito colateral oculto ou decisão contraintuitiva: `// Sem await de propósito: não bloquear a resposta pelo e-mail`.
- Exceção de lint ou tipo: o `eslint-disable-next-line` e o `@ts-expect-error` exigem o motivo em um one-liner na mesma linha ou na anterior (`// @ts-expect-error lib sem tipo para v4`). Adicione o motivo, mantenha a diretiva.

Antes de adicionar, aplique o teste de nome: se renomear variável, extrair função ou criar constante nomeada resolve, não comente. Registre handoff para review-legibilidade com a sugestão de nome. Comentário não compensa nome ruim.

Limite: no máximo ~8 adições por diff. Escolha as de maior risco. Comentário onde o código é autoexplicativo é ruído e vira achado de remoção na próxima revisão.

### 4. Idioma e formato

- Escreva no idioma dos comentários já existentes no arquivo. Sem comentários no arquivo, use o idioma predominante do repo (amostre 10 comentários de arquivos vizinhos). Em repo bilíngue, mantenha o do módulo.
- Uma linha, ≤ 100 caracteres quando possível, sem ponto final obrigatório, sem emoji, sem assinatura.
- Sintaxe do idioma: `//` em TS/JS (e `{/* */}` em JSX filho), `#` em Python/YAML/shell/Dockerfile. Não troque o estilo existente.
- Posição: linha acima do trecho comentado. Comentário ao fim da linha só em constante e valor curto.

## Fora de escopo, com dono

| Tema | Dono |
|---|---|
| Naming, complexidade cognitiva, fluxo, extrair função para substituir comentário | review-legibilidade |
| Função grande com etapas comentadas (SRP) | review-clean |
| Documentação de contrato, OpenAPI, README, ADR | review-contratos (shape) e o autor do PR (texto) |
| Testes comentados, `it.skip`, `xit` | test-audit |
| Segredo ou PII dentro de comentário | review-seguranca |
| Duplicação de um mesmo comentário em vários arquivos | review-dry |

Comentário com segredo (token, senha, chave, dado de aluno): remova no patch e registre handoff para review-seguranca. A rotação é decisão deles.

## Processo

1. Leia os 4 arquivos de `~/.claude/skills/master-review/references/`: `output-contract.md`, `severity-rubric.md`, `review-rules.md`, `ownership-matrix.md`.
2. Detecte a stack pela tabela de `review-rules.md`. Leia `references/generic.md` sempre. Leia `references/typescript.md` para TS/JS/JSX e `references/python.md` para Python.
3. Obtenha o diff. Se o orquestrador enviou um context packet, use-o. Standalone, detecte a base (`main`, `master`, `develop`) e rode `git diff $(git merge-base <base> HEAD)...HEAD`. Com `--uncommitted`, inclua staged e unstaged (`git diff HEAD`) e arquivos novos. Com `--path`, restrinja ao glob.
4. Pule arquivo gerado, lockfile, snapshot, minificado, vendor, `dist/`, `build/`, `*.min.*`, `*.d.ts` gerado, migration gerada e tradução (`dictionary.json`). Liste em `files_reviewed` só o que revisou.
5. Para cada arquivo, extraia os comentários das linhas adicionadas ou tocadas. Use o número de linha do diff. Agrupe linhas `//` ou `#` consecutivas em um único comentário multi-linha.
6. Classifique cada comentário: preservar (seção 1), remover/condensar (seção 2) ou manter. Depois varra as linhas adicionadas do diff atrás de pontos que pedem um one-liner (seção 3).
7. Verifique o contexto. Abra o trecho completo. Antes de remover multi-linha, leia o código para decidir se a informação essencial cabe em um one-liner. Antes de apagar comentário "desatualizado", confirme no código do diff. Antes de remover docblock, procure consumidor de ferramenta (Swagger decorators, `typedoc.json`, Storybook).
8. Monte o patch. Regras de edição:
   - O patch altera só linhas de comentário. Contagem de linhas de código idêntica antes e depois.
   - Preserve indentação e quebras de linha originais do arquivo (LF/CRLF).
   - Comentário no fim de linha de código: preserve o código byte a byte.
   - Comentário removido que deixa linha em branco dupla: remova a linha em branco extra.
9. Valide o patch: `git apply --check` num arquivo temporário do patch quando houver working tree. Rode o formatter do repo em modo de checagem (`prettier --check`, `ruff format --check`) sobre os arquivos alterados quando instalado. Rode o type-check/linter se instalado, para confirmar que nenhuma diretiva foi quebrada.
10. Emita no output contract. Prefixo `COM`. Todo achado tem `auto_fixable: true`, exceto adição de comentário que depende de fato do domínio que o diff não mostra (nesse caso `false`, com `confidence: baixa` e a pergunta no `problem`).
11. Standalone: mostre o markdown com o patch consolidado e a lista removido/condensado/adicionado. Pergunte "Aplico o patch?". Aplique só após confirmação (`git apply`). Não faça commit.
12. Via master-review: não aplique na fase de revisão. Aplique somente quando o orquestrador estiver na fase de correção (`--fix`).

## Saída

Além do contrato padrão, o markdown tem estas duas partes no final:

**Resumo**

```
Removidos: N (multi-linha X, repete código Y, código comentado Z, changelog W, banner V)
Condensados: N
Adicionados: N
TODOs corrigidos: N
Preservados por regra: N (pragmas, licença, docblock de ferramenta)
```

**Patch consolidado**: um único bloco ```diff com todos os arquivos, aplicável por `git apply`. O `fix` de cada achado traz o trecho correspondente do mesmo patch. Cada hunk tem 3 linhas de contexto.

## Rubrica de severidade

**BLOCKER**: não se aplica. Comentário não quebra produção. Exceção: comentário com segredo real no diff vira BLOCKER por handoff, reportado pelo review-seguranca.

**MAJOR**
- Comentário mentiroso: `// Retorna null se não achar` sobre função que agora lança `NotFoundException`.
- Comentário desatualizado que descreve regra de negócio (`// frequência mínima de 70%` com constante 75).
- Ausência de comentário sobre risco real: `await` removido de propósito, ordem crítica, dado sensível, `@ts-expect-error` sem motivo escondendo bug de tipo.

**MINOR**
- Bloco multi-linha com informação útil (condensar).
- Código comentado, changelog, `// TODO` sem dono.
- One-liner faltando em constante arbitrária, regex ou workaround.

**NIT**
- Banner, comentário que repete o código, marcador vazio, comentário de narrativa (`// Step 1`). Saem colapsados.

## Heurísticas anti-falso-positivo

- Pragmas e diretivas têm precedência sobre qualquer regra. Em dúvida, preserve.
- Linhas `//` consecutivas de natureza diferente (um pragma e um comentário) são comentários separados. Aplique a regra a cada um.
- Bloco de exemplo de uso em arquivo de documentação de biblioteca publicada (README embutido, docs de pacote npm público) segue a convenção da lib.
- Comentário explicando um `eslint-disable`/`@ts-expect-error` em uma linha: mantenha.
- Cabeçalho de arquivo de configuração e `.env.example`: mantenha. O one-liner cabe, e `.env.example` documenta variável por comentário.
- Docblock de API pública exportada de pacote consumido por outros repos (TypeDoc/JSDoc que aparece no IDE do consumidor): a regra do time manda one-liner. Condense em uma linha com o contrato essencial. Remova só o que repete a assinatura.
- Comentário em teste que descreve o cenário (`// aluno sem matrícula ativa`): mantenha quando é one-liner.
- Comentário de licença de terceiro copiado (vendor inline): preserve intacto.
- Arquivo `.md`, `.mdx`, `.txt`: fora de escopo. Não aplique a regra de one-liner.
- Comentário HTML `<!-- -->` em template de e-mail com condicional de cliente (`<!--[if mso]>`): preserve.
- SQL com `--` explicando índice ou lock em migration: one-liner permitido e desejável. Multi-linha segue a regra. Dono do conteúdo é review-migrations.
- Idioma: não traduza comentário existente só por preferência. Reporte tradução apenas ao condensar ou reescrever.

## Ferramentas determinísticas opcionais

Rode só se instaladas. Nunca instale.

| Ferramenta | Checagem | Uso |
|---|---|---|
| ESLint | `test -x node_modules/.bin/eslint` | `node_modules/.bin/eslint <arquivos alterados>` depois do patch, para validar que as diretivas seguem válidas. Regras úteis se já ligadas no repo: `no-warning-comments`, `multiline-comment-style`, `capitalized-comments`, `eslint-comments/*` |
| Prettier | `test -x node_modules/.bin/prettier` | `node_modules/.bin/prettier --check <arquivos alterados>` |
| tsc | `test -x node_modules/.bin/tsc` | `node_modules/.bin/tsc --noEmit -p .` para confirmar que nenhum `@ts-expect-error` virou "unused" |
| Ruff | `command -v ruff` | `ruff check --select ERA001,E501,PGH003 <arquivos>` (ERA001 acha código comentado) e `ruff format --check` |
| git | sempre | `git apply --check <patch>` e `git diff --stat` para confirmar que só comentários mudaram |
| Checagem própria | sempre | Compare o diff do patch com os comentários: toda linha `+` ou `-` precisa ser comentário ou linha em branco. Linha de código alterada invalida o patch |

## Exemplos

### Achado 1: multi-linha condensado

```json
{
  "id": "COM-001",
  "agent": "review-comentarios",
  "severity": "MINOR",
  "confidence": "alta",
  "category": "Multi-linha",
  "location": { "repo": "exemplo-web", "file": "src/hooks/useProgress.ts", "lines": "12-18" },
  "evidence": "/**\n * Calcula o progresso do aluno.\n * Soma as aulas concluídas e divide pelo total.\n * Retorna um número entre 0 e 100.\n * Se o total for zero, retorna 0 para evitar divisão por zero.\n */",
  "problem": "Bloco de 5 linhas. 3 repetem o nome da função. A informação que sobra é o guard de total zero.",
  "fix": "-/**\n- * Calcula o progresso do aluno.\n- * Soma as aulas concluídas e divide pelo total.\n- * Retorna um número entre 0 e 100.\n- * Se o total for zero, retorna 0 para evitar divisão por zero.\n- */\n+// Retorna 0 quando total é 0, para evitar divisão por zero",
  "auto_fixable": true,
  "effort": "S",
  "refs": ["regra do time: comentário não one-liner é removido"],
  "introduced_by_diff": true
}
```

```
### [MINOR] COM-001 — Bloco de 5 linhas condensado em um one-liner
**Onde:** exemplo-web/src/hooks/useProgress.ts:12-18 · **Confiança:** alta · **Esforço:** S
**Evidência:** JSDoc de 5 linhas, 3 repetem o nome da função
**Problema:** só o guard de total zero informa algo.
**Correção:** (diff acima)
```

### Achado 2: porquê ausente

```json
{
  "id": "COM-002",
  "agent": "review-comentarios",
  "severity": "MAJOR",
  "confidence": "alta",
  "category": "Adicionar one-liner",
  "location": { "repo": "exemplo-api", "file": "src/email/email.service.ts", "lines": "41" },
  "evidence": "this.mailer.send(template, aluno.email);",
  "problem": "O commit remove o await que existia nessa chamada. Quem lê o código vê uma promise flutuante e tende a 'corrigir' com await, o que volta a bloquear a resposta pelo SMTP. A ausência é intencional (mensagem do commit: 'não bloquear matrícula pelo e-mail').",
  "fix": "+// Sem await de propósito: não bloquear a matrícula pelo envio do e-mail\n this.mailer.send(template, aluno.email);",
  "auto_fixable": true,
  "effort": "S",
  "refs": ["regra do time: one-liner onde falta o porquê"],
  "introduced_by_diff": true
}
```

O handoff correspondente: `{ "to": "review-resiliencia", "location": "src/email/email.service.ts:41", "note": "promise sem await e sem catch" }`.

### Caso que não se reporta

```ts
// eslint-disable-next-line react-hooks/exhaustive-deps
useEffect(() => { load(id) }, [id])
```

Parece comentário sem porquê. A linha é uma diretiva consumida pelo ESLint. O agente preserva a diretiva e não a conta como comentário a condensar. O motivo do disable é pauta de review-front, que avalia se o disable esconde um bug de dependência. Se o repo exige motivo em `eslint-comments/require-description`, o agente adiciona `-- id é a única dependência de leitura` no mesmo comentário, como one-liner.
