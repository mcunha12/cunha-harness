#!/usr/bin/env bash
# Roda um comando pesado (tsc, testes, build, browser) só quando há slot livre; limite global DEV_HEAVY_SLOTS.
set -u
DIR="${DEV_HEAVY_DIR:-$HOME/.claude/dev/heavy}"
SLOTS="${DEV_HEAVY_SLOTS:-2}"
mkdir -p "$DIR"
[ "$#" -eq 0 ] && { echo "uso: heavy_lock.sh <comando> [args...]" >&2; exit 2; }
held=""
release() { [ -n "$held" ] && rm -rf "$held"; }
trap release EXIT
trap 'exit 130' INT TERM
while [ -z "$held" ]; do
  for i in $(seq 1 "$SLOTS"); do
    slot="$DIR/slot-$i"
    if [ -d "$slot" ]; then
      if [ -f "$slot/pid" ]; then
        kill -0 "$(cat "$slot/pid" 2>/dev/null)" 2>/dev/null || rm -rf "$slot"
      else
        # slot sem pid há mais de 10 s é órfão de um kill entre mkdir e a escrita do pid
        mtime=$(stat -f %m "$slot" 2>/dev/null || stat -c %Y "$slot" 2>/dev/null || echo 0)
        [ $(( $(date +%s) - mtime )) -gt 10 ] && rm -rf "$slot"
      fi
    fi
    if mkdir "$slot" 2>/dev/null; then
      echo $$ > "$slot/pid.tmp" && mv "$slot/pid.tmp" "$slot/pid"
      held="$slot"
      break
    fi
  done
  [ -z "$held" ] && sleep 2
done
"$@"
exit $?
