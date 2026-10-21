#!/usr/bin/env bash
# Bloqueia termos proibidos (lista fora do repo) nos arquivos indicados ou staged.
set -u
TERMS="${FORBIDDEN_TERMS:-$HOME/.claude/overlays/forbidden-terms.txt}"
if [ ! -f "$TERMS" ]; then
  echo "lista de termos ausente: $TERMS" >&2
  exit 2
fi
if [ "$#" -gt 0 ]; then
  files=("$@")
else
  files=()
  while IFS= read -r f; do [ -f "$f" ] && files+=("$f"); done < <(git diff --cached --name-only --diff-filter=ACMR)
fi
[ "${#files[@]}" -eq 0 ] && exit 0
hits=$(grep -n -i -o -E -f "$TERMS" -- "${files[@]}" /dev/null 2>/dev/null)
if [ -n "$hits" ]; then
  echo "$hits"
  echo "termo proibido encontrado" >&2
  exit 1
fi
exit 0
