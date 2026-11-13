#!/usr/bin/env bash
# Vigia um MR/PR até o merge com CI verde; rode em background. Saída: 0 mergeado+verde, 3 fechado sem merge, 4 CI vermelho, 2 uso.
set -u
USAGE="uso: mr_scout.sh <repo_path> <mr_number> [intervalo_s=300]"
REPO="${1:-}"; MR="${2:-}"; EVERY="${3:-300}"
[ -z "$REPO" ] || [ -z "$MR" ] && { echo "$USAGE" >&2; exit 2; }
cd "$REPO" || exit 2
HOST=gitlab
git remote get-url origin | grep -q github.com && HOST=github

state() {
  if [ "$HOST" = github ]; then
    gh pr view "$MR" --json state,mergeCommit -q '.state + " " + (.mergeCommit.oid // "")'
  else
    glab mr view "$MR" -F json | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["state"].upper(), d.get("merge_commit_sha") or d.get("squash_commit_sha") or "")'
  fi
}

ci() {
  local sha="$1"
  if [ "$HOST" = github ]; then
    gh api "repos/{owner}/{repo}/commits/$sha/check-runs" -q '[.check_runs[].conclusion] | if length==0 then "none" elif any(.==null) then "running" elif all(.=="success" or .=="skipped" or .=="neutral") then "success" else "failed" end'
  else
    glab ci list -F json 2>/dev/null | python3 -c "import json,sys; p=[x for x in json.load(sys.stdin) if x.get('sha')=='$sha']; s=p[0]['status'] if p else 'none'; print({'success':'success','failed':'failed','canceled':'failed'}.get(s, 'running' if p else 'none'))"
  fi
}

none_seen=0
while true; do
  read -r st sha <<<"$(state 2>/dev/null)"
  case "$st" in
    CLOSED) echo "fechado sem merge"; exit 3 ;;
    MERGED)
      c="$(ci "$sha" 2>/dev/null)"
      echo "$(date +%H:%M) mergeado $sha ci=$c"
      [ "$c" = success ] && exit 0
      [ "$c" = failed ] && exit 4
      # repo sem pipeline no merge: 3 leituras seguidas sem pipeline contam como verde
      if [ "$c" = none ]; then none_seen=$((none_seen+1)); [ "$none_seen" -ge 3 ] && exit 0; fi ;;
  esac
  sleep "$EVERY"
done
