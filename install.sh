#!/usr/bin/env bash
# Instala cada pasta com SKILL.md como symlink em SKILLS_DIR; nunca apaga, só move para o backup.
set -eu
REPO_DIR="${REPO_DIR:-$(cd "$(dirname "$0")" && pwd)}"
SKILLS_DIR="${SKILLS_DIR:-$HOME/.claude/skills}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/.claude/skills-backup/$(date +%Y%m%d-%H%M%S)}"
DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1
mkdir -p "$SKILLS_DIR"
for dir in "$REPO_DIR"/*/; do
  dir="${dir%/}"
  [ -f "$dir/SKILL.md" ] || continue
  name="$(basename "$dir")"
  target="$SKILLS_DIR/$name"
  if [ -L "$target" ] && [ "$(cd "$target" && pwd -P)" = "$(cd "$dir" && pwd -P)" ]; then
    echo "ok $name"
    continue
  fi
  if [ -e "$target" ] || [ -L "$target" ]; then
    echo "substitui $name (backup em $BACKUP_DIR/$name)"
    if [ "$DRY" -eq 0 ]; then
      [ -d "$target" ] && [ ! -L "$target" ] && diff -rq "$target" "$dir" | head -10 || true
      mkdir -p "$BACKUP_DIR"
      dest="$BACKUP_DIR/$name"; n=1
      while [ -e "$dest" ] || [ -L "$dest" ]; do dest="$BACKUP_DIR/$name.$n"; n=$((n + 1)); done
      mv "$target" "$dest"
    fi
  else
    echo "cria $name"
  fi
  [ "$DRY" -eq 0 ] && ln -s "$dir" "$target"
done
# hooks versionados: a guarda de anonimização vale em toda clone que rodar o install
if [ "$DRY" -eq 0 ] && [ -d "$REPO_DIR/.githooks" ] && git -C "$REPO_DIR" rev-parse --git-dir >/dev/null 2>&1; then
  git -C "$REPO_DIR" config core.hooksPath .githooks
fi
exit 0
