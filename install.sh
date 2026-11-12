#!/usr/bin/env bash
# Instala cada pasta com SKILL.md como symlink em SKILLS_DIR; nunca apaga, só move para o backup.
set -eu
REPO_DIR="${REPO_DIR:-$(cd "$(dirname "$0")" && pwd)}"
SKILLS_DIR="${SKILLS_DIR:-$HOME/.claude/skills}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/.claude/skills-backup/$(date +%Y%m%d-%H%M%S)}"
DRY=0; NO_DEPS=0; NO_IMPECCABLE=0
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    --sem-deps) NO_DEPS=1 ;;
    --sem-impeccable) NO_IMPECCABLE=1 ;;
  esac
done
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
# dependências da /dev: instaladas pelo instalador oficial de cada uma, nunca copiadas
deps() {
  [ "$NO_DEPS" -eq 1 ] && { echo "dependências puladas (--sem-deps)"; return; }
  if ! command -v node >/dev/null 2>&1; then
    echo "AVISO: Node.js não encontrado. Instale (https://nodejs.org) e rode de novo: Impeccable, agent-browser e o servidor de protótipos da /dev precisam dele."
    return
  fi
  if [ "$NO_IMPECCABLE" -eq 1 ]; then
    echo "impeccable pulado (--sem-impeccable)"
  elif [ -d "$SKILLS_DIR/impeccable" ]; then
    echo "ok impeccable (atualize com: npx impeccable update)"
  else
    echo "instala impeccable"
    [ "$DRY" -eq 0 ] && { npx -y impeccable install || echo "AVISO: falhou. Rode à mão: npx impeccable install"; }
  fi
  if ! command -v claude >/dev/null 2>&1; then
    echo "AVISO: CLI claude não encontrada. Rode à mão: claude plugin install superpowers@claude-plugins-official"
  elif claude plugin list 2>/dev/null | grep -q "superpowers@"; then
    echo "ok superpowers"
  else
    echo "instala superpowers"
    [ "$DRY" -eq 0 ] && { claude plugin install superpowers@claude-plugins-official || echo "AVISO: falhou. Rode à mão: claude plugin install superpowers@claude-plugins-official"; }
  fi
  if command -v agent-browser >/dev/null 2>&1; then
    echo "ok agent-browser"
  else
    echo "instala agent-browser"
    [ "$DRY" -eq 0 ] && { npm i -g agent-browser || echo "AVISO: falhou. Rode à mão: npm i -g agent-browser"; }
  fi
}
deps
exit 0
