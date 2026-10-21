#!/usr/bin/env bash
# Bloqueia termos proibidos (lista fora do repo) nos arquivos indicados ou staged.
set -u
TERMS="${FORBIDDEN_TERMS:-$HOME/.claude/overlays/forbidden-terms.txt}"
if [ ! -f "$TERMS" ]; then
  echo "lista de termos ausente: $TERMS" >&2
  exit 2
fi
if [ "$#" -gt 0 ]; then
  hits=$(grep -n -i -o -E -f "$TERMS" -- "$@" /dev/null 2>/dev/null)
else
  # sem argumento confere o conteúdo staged, que é o que entra no commit
  hits=$(git grep --cached -n -i -o -E -f "$TERMS" 2>/dev/null)
fi
if [ -n "$hits" ]; then
  echo "$hits"
  echo "termo proibido encontrado" >&2
  exit 1
fi
exit 0
