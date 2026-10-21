---
name: review-arquitetura
description: Revisa a arquitetura de um diff (ARQ) - conformidade com o jeito que o repo já resolve o mesmo problema, escalabilidade com mais dados, carga e features, dependência ou padrão novo que pede ADR, e tamanho da solução frente ao problema (excesso e falta). Acione em "revisa a arquitetura desse PR", "isso segue o padrão do repo?", "isso escala?", "/review-arquitetura" ou via master-review. NÃO cobre camadas, fronteiras, ciclos e acoplamento (review-modularidade), SRP e smells de classe (review-clean), duplicação (review-dry), shape de API (review-contratos), performance de query (review-queries).
argument-hint: "[--base <branch>] [--path <glob>] [--uncommitted]"
---

# review-arquitetura

## Missão

Garantir que alguém olha a arquitetura do diff como um todo. O critério é o custo de manter e de crescer: o código novo segue o caminho que o repo já usa, aguenta 10× mais dados e uso, e tem o tamanho que o problema pede. O achado nomeia o precedente no repo (`arquivo:linha` de como já se faz), a divergência e o custo dela.

## Escopo

Cada item segue: sinal no código, impacto, correção típica.

### 1. Conformidade com o repo

- Sinal: o diff resolve um problema que o repo já resolve de outro jeito. Exemplos: novo client HTTP quando existe um client configurado; novo jeito de ler config; novo padrão de erro, de paginação, de fila ou de estado global; pasta organizada por camada num repo organizado por feature.
- Impacto: dois jeitos de fazer a mesma coisa. O próximo dev escolhe um ao acaso, e a correção de um bug precisa acontecer nos dois.
- Correção: usar o precedente. Se o precedente é ruim, a troca é decisão explícita (ADR) e vale para o repo todo.

### 2. Escalabilidade

- Sinal: estrutura que cresce com usuários ou dados sem limite (lista em memória, varredura de tabela inteira, job que processa tudo de uma vez, estado por usuário guardado em processo); solução que só funciona com uma instância (cron em processo, lock em memória, cache local sem invalidação entre instâncias).
- Impacto: funciona no preprod e cai com o volume de produção ou com a segunda réplica.
- Correção: paginação ou lote, processamento assíncrono, estado compartilhado (banco, Redis, fila), idempotência para rodar em várias réplicas.

### 3. Dependência ou padrão novo

- Sinal: lib nova no manifesto, serviço ou infra nova, padrão de projeto novo (event sourcing, CQRS, state machine lib, novo framework de UI) sem ADR ou nota no MR.
- Impacto: custo de manutenção, superfície de segurança e curva de aprendizado entram sem decisão registrada.
- Correção: checar se o repo já tem algo equivalente; se a entrada se justifica, registrar a decisão (ADR curto) com alternativas.

### 4. Tamanho da solução

- Sinal de excesso: abstração genérica com um caso de uso, camada de indireção sem segundo implementador, configuração para variações que ninguém pediu. Sinal de falta: regra crítica espalhada em handlers, script ad hoc onde o repo tem estrutura.
- Impacto: excesso custa leitura e mudança; falta custa duplicação e bug.
- Correção: o menor desenho que atende o requisito atual e o crescimento já previsto na spec.

## Fora de escopo e dono

| Tema | Dono |
|---|---|
| Direção de dependência entre camadas, ciclos, deep import, barrel | review-modularidade |
| SRP, smells de função e classe | review-clean |
| Regra replicada | review-dry |
| Shape de payload, breaking change | review-contratos |
| N+1, índice, cache | review-queries |

## Processo

1. Leia `~/.claude/skills/master-review/references/`: `output-contract.md`, `severity-rubric.md`, `review-rules.md`, `ownership-matrix.md`.
2. Obtenha o diff (context packet do orquestrador ou `git diff $(git merge-base <base> HEAD)...HEAD`).
3. Para cada arquivo novo, dependência nova ou mecanismo novo, procure o precedente no repo: arquivos com o mesmo sufixo ou papel (`*.client.ts`, `*.repository.ts`, `use*.ts`), o mesmo tipo de lib no manifesto, o mesmo tipo de problema (grep por palavras do domínio). Leia o README, o `CLAUDE.md` e ADRs existentes.
4. Para cada estrutura que cresce, pergunte: o que acontece com 10× os dados, 10× as requests e 2 réplicas?
5. Classifique com a rubrica abaixo e a global.
6. Emita no output contract. Prefixo dos ids: `ARQ`. Máximo de ~15 achados.

Standalone: mostre o markdown no final. Não altere código.

## Rubrica de severidade do tema

**BLOCKER**
- Solução que quebra com a segunda réplica em produção (cron em processo duplicando cobrança, lock em memória protegendo recurso disputado).
- Estrutura sem limite que cresce com usuários em rota síncrona (carregar todas as matrículas em memória para filtrar).

**MAJOR**
- Segundo jeito de resolver um problema que o repo já resolve, sem decisão registrada.
- Dependência nova pesada ou com superfície de segurança relevante sem ADR, havendo equivalente no repo.
- Job ou processamento que não escala com o volume previsto na spec.
- Abstração genérica com um único uso que o diff introduz em código central.

**MINOR**
- Organização de pasta que diverge do vizinho.
- Dependência leve nova sem nota no MR.

**NIT**
- Preferência de padrão sem custo concreto.

## Heurísticas anti-falso-positivo

- Precedente ruim documentado como legado (README, ADR, `@deprecated`) não conta como padrão a seguir.
- Repo sem padrão estabelecido para o problema: não há divergência; no máximo MINOR sugerindo registrar a escolha.
- Escalabilidade exige número: sem volume esperado (spec, schema, tráfego), confiança `media` e a condição no `problem`.

## Exemplos

### [MAJOR] ARQ-001 — Segundo client HTTP para o mesmo serviço

- Evidência: `src/notifications/send.ts` cria `axios.create({ baseURL: process.env.MAIL_URL })`.
- Precedente: `src/http/mail.client.ts:12` já expõe `mailClient` com timeout, retry e trace.
- Problema: o envio novo sai sem timeout e sem trace; correções no client padrão não chegam aqui.
- Fix: importar `mailClient`.
