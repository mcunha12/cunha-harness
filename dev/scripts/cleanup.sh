#!/usr/bin/env bash
# Apaga worktrees e branches de uma feature já mergeada. Recusa se a branch local tem commit fora do MR.
set -u
USAGE="uso: cleanup.sh <repo_path> <slug> <mr_head_sha> [--dry-run]"
REPO="${1:-}"; SLUG="${2:-}"; HEAD_SHA="${3:-}"; DRY="${4:-}"
[ -z "$REPO" ] || [ -z "$SLUG" ] || [ -z "$HEAD_SHA" ] && { echo "$USAGE" >&2; exit 2; }
cd "$REPO" || exit 2
run() { echo "+ $*"; [ "$DRY" = --dry-run ] || "$@"; }
FEAT="feat/$SLUG"
git fetch --prune origin >/dev/null 2>&1

if git rev-parse --verify -q "$FEAT" >/dev/null; then
  tip="$(git rev-parse "$FEAT")"
  if [ "$tip" != "$HEAD_SHA" ] && ! git merge-base --is-ancestor "$tip" "$HEAD_SHA"; then
    echo "RECUSADO: $FEAT ($tip) tem commit fora do MR ($HEAD_SHA). Abra MR de follow-up." >&2
    exit 5
  fi
fi
if [ -n "$(git status --porcelain --untracked-files=no)" ] && [ "$(git branch --show-current)" = "$FEAT" ]; then
  echo "RECUSADO: checkout em $FEAT com mudança não commitada." >&2
  exit 5
fi

git worktree list --porcelain | awk '/^worktree /{p=$2; n++} /^branch /{if (n>1) print p" "$2}' | while read -r path ref; do
  b="${ref#refs/heads/}"
  case "$b" in "$FEAT"|dev/"$SLUG"/*) run git worktree remove --force "$path" ;; esac
done
run git worktree prune

if [ "$(git branch --show-current)" = "$FEAT" ]; then
  base="$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#origin/##')"
  run git checkout "${base:-main}"
  run git pull --ff-only
fi
for b in $(git for-each-ref --format='%(refname:short)' "refs/heads/$FEAT" "refs/heads/dev/$SLUG/"); do
  run git branch -D "$b"
done
git ls-remote --exit-code --heads origin "$FEAT" >/dev/null 2>&1 && run git push origin --delete "$FEAT"
run git gc --auto --quiet
echo "limpo: $SLUG em $REPO"
