# Segurança: regras agnósticas de stack

Cada item: sinal no código, impacto, correção. Use depois de ler o diff e antes do reference da tecnologia.

## Modelo de ameaça rápido

Para cada mudança, responda em 4 linhas antes de caçar sinais.
1. Quem controla a entrada? (anônimo, aluno, professor, admin, serviço, webhook de terceiro, saída de LLM)
2. Qual ativo muda de mãos? (nota, matrícula, dado pessoal, pagamento, token, custo de API)
3. Onde a confiança é checada? (gateway, guard, service, query, nenhum)
4. O que o atacante ganha se a checagem falhar?

Sem resposta para 3, o achado é candidato a BLOCKER. Com a checagem em camada que o diff não mostra, abra a camada antes de reportar.

## Autorização por objeto

- Todo recurso identificado por id vindo do cliente tem ownership verificado no servidor. Cadeia completa: `usuário -> matrícula -> turma -> aula -> comentário`. Cada elo precisa de checagem. Id aninhado trocado (`/turmas/A/alunos/B` com B de outra turma) é o bypass mais comum.
- Operação em lote (`ids: string[]`) checa cada id. Checar só o primeiro item é bug.
- Listagem filtra por escopo do usuário na query. Filtrar depois do fetch, em memória, vaza por timing, paginação e contagem total.
- `404` em vez de `403` quando a existência do recurso é informação sensível.
- Operações de leitura derivada (export, relatório, download de PDF, URL assinada) herdam a mesma checagem da leitura primária. URL assinada gerada sem checar o dono entrega o arquivo a quem tiver o link.
- Multi-tenant: `tenantId` vem do token autenticado. `tenantId` vindo de body, header ou query é input do atacante.

## Entrada

- Valide na borda com schema (class-validator, zod, Pydantic): tipo, tamanho máximo, formato, enum. Valor inesperado de tipo (objeto no lugar de string) vira injeção de operador em NoSQL e bypass de comparação.
- Allowlist para: nome de coluna em `ORDER BY`, nome de campo em filtros dinâmicos, hosts de URL, tipos de arquivo, destinos de redirect.
- Normalize antes de validar (Unicode NFKC, trim, lowercase de e-mail, decode de URL uma vez). Validar antes de normalizar permite bypass.
- Limite de tamanho em body, array, string, profundidade de JSON, número de itens em lote.

## Saída

- Escape no ponto de uso, conforme o contexto (HTML, atributo, URL, JS, SQL, shell). Sanitização genérica na entrada não substitui.
- DTO de resposta com campos explícitos. Entidade do ORM serializada direto vaza coluna nova adicionada depois.
- Mensagem de erro ao cliente sem stack, SQL, caminho de arquivo, versão de lib.
- Header de cache correto: resposta autenticada ou com dado pessoal usa `Cache-Control: private, no-store`. Resposta autenticada com `public` ou cacheada em CDN por URL entrega dado de um usuário a outro.

## Segredos

- Padrões de alto sinal: `AKIA[0-9A-Z]{16}`, `sk-[A-Za-z0-9_-]{20,}`, `ghp_[A-Za-z0-9]{36}`, `glpat-[A-Za-z0-9_-]{20}`, `xox[abp]-`, `eyJ[A-Za-z0-9_-]{10,}\.eyJ` (JWT), `-----BEGIN (RSA |EC )?PRIVATE KEY-----`, URL com credencial (`postgres://user:pass@`).
- Segredo em arquivo versionado exige rotação. Cite isso no `fix`.
- Segredo em argumento de linha de comando, em `ARG` de Docker, em log de CI ou em mensagem de erro.
- Variável de ambiente injetada no client é pública. Liste o que o bundle recebe e confirme que cada valor é público por design.
- Config por ambiente: o default seguro vale para prod. `if (env !== 'production') skipAuth` inverte o risco quando a variável falta. Prefira `if (env === 'development')`.

## Sessão e token

- Expiração curta no access token. Refresh token com rotação e revogação.
- Logout invalida no servidor quando o repo guarda sessão.
- Token em storage legível por script (`localStorage`, `sessionStorage`) sofre exfiltração por qualquer XSS. Em repo cuja autenticação é de SDK gerenciado, trate como decisão de arquitetura e reporte só uso novo inseguro.
- Não coloque dado sensível em claims do JWT (ele é legível por qualquer um).
- Reset de senha e magic link: token aleatório com ≥128 bits, uso único, TTL curto, invalida ao trocar senha.

## Criptografia

- Não invente protocolo. Use biblioteca de alto nível (libsodium, `crypto.subtle`, `cryptography`).
- Senha: argon2id (m≥19 MiB, t≥2) ou bcrypt cost ≥ 12. Hash rápido de senha é MAJOR.
- Aleatoriedade de segurança vem de CSPRNG: `crypto.randomBytes`, `secrets`, `SecureRandom`.
- Compare segredos em tempo constante.
- Não reutilize chave para propósitos diferentes. Chave no código é segredo commitado.

## Abuso e custo

- Todo endpoint sem autenticação e todo endpoint que chama serviço pago (LLM, SMS, e-mail, OCR, geração de PDF) tem rate limit por identidade e por IP, e teto de custo diário.
- Fluxos de negócio (cupom, resgate, inscrição, avaliação) tem limite por usuário e idempotência. Sem isso, concorrência burla a regra (race de resgate duplo).
- Operação de enumeração (login, "esqueci a senha", checar e-mail) responde igual para existente e inexistente, com tempo similar.

## Fila, job e webhook

- Mensagem de fila vinda de outro serviço é input não confiável quando a fila é compartilhada. Valide schema e ownership dentro do consumer.
- Webhook: verifique assinatura sobre o corpo bruto, compare em tempo constante, confira timestamp (janela de 5 min) e deduplique por id do evento.
- Job que age em nome de usuário recebe o id do usuário e reaplica autorização. Job não herda permissão do enfileirador por magia.

## Supply chain

- Pacote novo: nome exato, repositório oficial, downloads semanais, data do último release, quem publica, `scripts` de install, licença (GPL/AGPL em produto fechado é risco jurídico, MINOR com handoff humano).
- Lockfile muda junto com o manifesto. Mudança de `resolved`/`integrity` sem mudança de versão é sinal de adulteração.
- Pin por SHA em actions e imagens base de produção. Imagem `latest` é MINOR.
- Dependência que ressuscita pacote abandonado, dono transferido ou versão publicada há <7 dias (janela de ataque de conta comprometida): MAJOR com confiança `media`.

## LGPD

- Dado pessoal novo coletado precisa de finalidade registrada no PR/ticket. Dado sensível (saúde, biometria, orientação) tem base legal própria. Aponte a ausência como MAJOR com confiança `baixa` e peça a base legal.
- Retenção: tabela nova com dado pessoal sem rotina de expurgo ou anonimização.
- Direito de exclusão: ids de usuário espalhados em tabela nova sem cascata ou rotina de anonimização.
- Transferência a terceiros (analytics, LLM, e-mail): dado mínimo, sem identificadores diretos quando possível.

## Severidade: calibragem do tema

- A exploração parte de um ator realista (aluno logado, visitante anônimo, site de terceiro) sem acesso privilegiado prévio.
- Alcance: um registro próprio (MINOR), registros de outros usuários (BLOCKER), todos os usuários (BLOCKER), execução de código (BLOCKER).
- Pré-condição rara (precisa de XSS prévio, precisa de rede interna) rebaixa um nível ou reduz a confiança.
