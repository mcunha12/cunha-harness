#!/usr/bin/env bash
# Bloqueia termos proibidos (lista fora do repo) em arquivos, no conteúdo e nos nomes staged, ou na mensagem de commit.
set -u
TERMS="${FORBIDDEN_TERMS:-$HOME/.claude/overlays/forbidden-terms.txt}"
if [ ! -f "$TERMS" ]; then
  echo "lista de termos ausente: $TERMS" >&2
  exit 2
fi
if ! grep -E -f "$TERMS" /dev/null 2>/dev/null; [ "${PIPESTATUS[0]:-$?}" -eq 2 ]; then
  echo "lista de termos com regex inválida: $TERMS" >&2
  exit 2
fi
check() {
  local out code
  out=$("$@" 2>/dev/null); code=$?
  [ "$code" -ge 2 ] && { echo "erro ao procurar termos" >&2; exit 2; }
  [ -n "$out" ] && echo "$out"
  return 0
}
if [ "${1:-}" = "--commit-msg" ]; then
  hits=$(check grep -n -i -o -E -f "$TERMS" -- "$2")
elif [ "$#" -gt 0 ]; then
  hits=$(check grep -n -i -o -E -f "$TERMS" -- "$@" /dev/null)
else
  # sem argumento confere o conteúdo e os nomes staged, que é o que entra no commit
  hits=$(check git grep --cached -n -i -o -E -f "$TERMS")
  names=$(git diff --cached --name-only --diff-filter=ACMR | grep -i -E -f "$TERMS" | sed 's/^/nome: /')
  hits=$(printf '%s\n%s' "$hits" "$names" | sed '/^$/d')
fi
if [ -n "$hits" ]; then
  echo "$hits"
  echo "termo proibido encontrado" >&2
  exit 1
fi
exit 0
