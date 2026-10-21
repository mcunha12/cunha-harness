#!/usr/bin/env bash
# Roda um comando pesado (tsc, testes, build, browser) só quando há slot livre; limite global DEV_HEAVY_SLOTS.
set -u
DIR="${DEV_HEAVY_DIR:-$HOME/.claude/dev/heavy}"
SLOTS="${DEV_HEAVY_SLOTS:-2}"
STALE_SECONDS=10
mkdir -p "$DIR"
[ "$#" -eq 0 ] && { echo "uso: heavy_lock.sh <comando> [args...]" >&2; exit 2; }
held=""
child=""

age() { echo $(( $(date +%s) - $(stat -f %m "$1" 2>/dev/null || stat -c %Y "$1" 2>/dev/null || echo 0) )); }

slot_alive() {
  # o arquivo pid guarda o wrapper e o filho; o slot vive enquanto qualquer um viver
  local p
  for p in $(cat "$1/pid" 2>/dev/null); do
    # zumbi responde ao kill -0 mas já morreu
    kill -0 "$p" 2>/dev/null && ! ps -o stat= -p "$p" 2>/dev/null | grep -q '^Z' && return 0
  done
  return 1
}

reclaim() {
  local slot="$1" mutex="$DIR/.reclaim"
  if ! mkdir "$mutex" 2>/dev/null; then
    [ "$(age "$mutex")" -gt "$STALE_SECONDS" ] && rm -rf "$mutex"
    return
  fi
  if [ -f "$slot/pid" ]; then
    slot_alive "$slot" || rm -rf "$slot"
  elif [ -d "$slot" ] && [ "$(age "$slot")" -gt "$STALE_SECONDS" ]; then
    rm -rf "$slot"
  fi
  rmdir "$mutex" 2>/dev/null
}

release() { [ -n "$held" ] && rm -rf "$held"; }
on_signal() {
  [ -n "$child" ] && kill -TERM "$child" 2>/dev/null && wait "$child" 2>/dev/null
  exit 143
}
trap release EXIT
trap on_signal TERM INT

while [ -z "$held" ]; do
  for i in $(seq 1 "$SLOTS"); do
    slot="$DIR/slot-$i"
    [ -d "$slot" ] && reclaim "$slot"
    if mkdir "$slot" 2>/dev/null; then
      echo $$ > "$slot/pid.tmp" && mv "$slot/pid.tmp" "$slot/pid"
      held="$slot"
      break
    fi
  done
  [ -z "$held" ] && sleep 2
done
"$@" <&0 &
child=$!
echo "$$ $child" > "$held/pid.tmp" && mv "$held/pid.tmp" "$held/pid"
wait "$child"
exit $?
