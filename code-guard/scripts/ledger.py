#!/usr/bin/env python3
"""Ledger de achados BLOCKER/MAJOR confirmados e gatilho do ciclo de aprendizado da code-guard."""
import argparse
import datetime
import glob
import json
import os
import re
import sys
import unicodedata

CORE_DOMAINS = {"seguranca", "legibilidade", "clean", "dry", "comentarios", "tipagem"}
KEPT = {"confirmado", "rebaixado para MAJOR"}
GUARD_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def home():
    return os.environ.get("CODE_GUARD_HOME", os.path.expanduser("~/.claude/code-guard"))


def slug(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def identity(agent, category):
    return f"{agent}:{slug(category)}"


def _read(path):
    if not os.path.exists(path):
        return []
    rows = []
    with open(path) as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue  # linha corrompida (escrita interrompida) não derruba o ledger
    return rows


def _append(path, record):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def find_rule(agent, category):
    needle = f"origem: {agent}/{slug(category)}"
    files = glob.glob(os.path.join(GUARD_DIR, "*.md")) + glob.glob(os.path.join(GUARD_DIR, "domains", "*.md"))
    files += glob.glob(os.path.join(home(), "learned", "*.md"))
    for path in files:
        with open(path) as f:
            for line in f:
                if needle in line:
                    return line.strip()
    return None


def append(findings, repo, feature, task, loaded):
    items = findings.get("findings", []) if isinstance(findings, dict) else findings
    now = datetime.datetime.now().replace(microsecond=0).isoformat()
    written = 0
    for item in items:
        if item.get("severity") not in ("BLOCKER", "MAJOR") or item.get("verification", "confirmado") not in KEPT:
            continue
        agent, category = item["agent"], item.get("category", "")
        domain = agent.replace("review-", "")
        _append(os.path.join(home(), "ledger.jsonl"), {
            "at": now, "repo": repo, "feature": feature, "task": task, "agent": agent, "category": category,
            "identity": identity(agent, category), "severity": item["severity"],
            "file": (item.get("location") or {}).get("file"), "problem": item.get("problem", "")[:200],
            "covered_rule": find_rule(agent, category), "domain_loaded": domain in loaded or domain in CORE_DOMAINS})
        written += 1
    return written


def triggers(threshold=3, min_tasks=2):
    ledger = _read(os.path.join(home(), "ledger.jsonl"))
    processed = {}
    for p in _read(os.path.join(home(), "processed.jsonl")):
        processed[p["identity"]] = p["ledger_index"]
    groups = {}
    for index, row in enumerate(ledger):
        if index >= processed.get(row["identity"], 0):
            groups.setdefault(row["identity"], []).append(row)
    out = []
    for ident, rows in groups.items():
        tasks = {(r.get("feature"), r.get("task")) for r in rows}
        if len(rows) >= threshold and len(tasks) >= min_tasks:
            last = rows[-1]
            out.append({"identity": ident, "agent": last["agent"], "category": last["category"], "occurrences": rows,
                        "covered_rule": last.get("covered_rule"), "domain_loaded": last.get("domain_loaded")})
    return out


def mark_processed(ident, action):
    count = len(_read(os.path.join(home(), "ledger.jsonl")))
    _append(os.path.join(home(), "processed.jsonl"), {
        "identity": ident, "action": action, "ledger_index": count,
        "at": datetime.datetime.now().replace(microsecond=0).isoformat()})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("append")
    a.add_argument("--findings", required=True)
    a.add_argument("--repo", required=True)
    a.add_argument("--feature", default="avulsa")
    a.add_argument("--task", default="avulsa")
    a.add_argument("--loaded-domains", default="")
    t = sub.add_parser("triggers")
    t.add_argument("--threshold", type=int, default=3)
    t.add_argument("--min-tasks", type=int, default=2)
    m = sub.add_parser("mark-processed")
    m.add_argument("--identity", required=True)
    m.add_argument("--action", choices=["created", "rewritten", "routing"], required=True)
    args = parser.parse_args(argv)
    if args.cmd == "append":
        with open(args.findings) as f:
            data = json.load(f)
        loaded = {d.strip() for d in args.loaded_domains.split(",") if d.strip()}
        print(json.dumps({"written": append(data, args.repo, args.feature, args.task, loaded)}))
    elif args.cmd == "triggers":
        print(json.dumps(triggers(args.threshold, args.min_tasks), ensure_ascii=False))
    else:
        mark_processed(args.identity, args.action)
        print(json.dumps({"ok": True}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
