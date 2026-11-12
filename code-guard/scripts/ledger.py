#!/usr/bin/env python3
"""Ledger de achados BLOCKER/MAJOR confirmados e gatilho do ciclo de aprendizado da code-guard."""
import argparse
import datetime
import glob
import hashlib
import json
import os
import re
import sys
import unicodedata

CORE_DOMAINS = {"seguranca", "legibilidade", "clean", "dry", "comentarios", "tipagem"}
KEPT = {"confirmado", "rebaixado para MAJOR"}
GUARD_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGIN_RE = re.compile(r"origem: (review-[a-z0-9-]+|test-audit)/([^\s·\"]+)", re.I)
PREFIX_RE = re.compile(r"^- \[([A-Z0-9]+)\]")


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


def _rule_files():
    files = glob.glob(os.path.join(GUARD_DIR, "*.md")) + glob.glob(os.path.join(GUARD_DIR, "domains", "*.md"))
    return files + glob.glob(os.path.join(home(), "learned", "*.md"))


def _origin_of(line):
    m = ORIGIN_RE.search(line)
    return f"{m.group(1)}/{slug(m.group(2))}" if m else None


def find_rule(agent, category):
    # casa a origem sem diferenciar caixa; sem casa exata, aceita prefixo de um lado ou do outro
    want = f"{agent}/{slug(category)}"
    partial = None
    for path in _rule_files():
        with open(path) as f:
            for line in f:
                origin = _origin_of(line)
                if origin == want:
                    return line.strip()
                if partial is None and origin and origin.split("/")[0] == agent and want.split("/")[1] and (
                        origin.startswith(want + "-") or want.startswith(origin + "-")):
                    partial = line.strip()
    return partial


def rule_id(prefix, origin, text):
    return f"{prefix}|{origin}|{hashlib.sha1(text.encode()).hexdigest()[:6]}"


def parse_guard(path):
    rules, section = [], ""
    with open(path) as f:
        for raw in f:
            line = raw.strip()
            if line.startswith("#"):
                section = line.lstrip("# ").strip()
                continue
            origin = _origin_of(line)
            m = PREFIX_RE.match(line)
            if origin and m:
                rules.append({"id": rule_id(m.group(1), origin, line), "prefix": m.group(1), "origin": origin,
                              "section": section, "text": line})
    return rules


def write_guard_rules(guard_path, domains, out):
    data = {"at": datetime.datetime.now().replace(microsecond=0).isoformat(), "domains": sorted(domains),
            "rules": parse_guard(guard_path)}
    with open(out, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    return data


def load_guard_rules(feature_dir):
    path = os.path.join(feature_dir, "guard-rules.json") if feature_dir else None
    if not path or not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def unused(feature, feature_dir):
    data = load_guard_rules(feature_dir)
    if data is None:
        return {"error": "guard-rules.json ausente", "feature_dir": feature_dir}
    fired = set()
    for row in _read(os.path.join(home(), "ledger.jsonl")):
        if row.get("feature") != feature:
            continue
        origin = _origin_of(row.get("covered_rule") or "") or f"{row['agent']}/{slug(row.get('category', ''))}"
        fired.add(origin)
    never = [r for r in data["rules"] if r["origin"] not in fired]
    return {"feature": feature, "loaded": len(data["rules"]), "fired": len(data["rules"]) - len(never),
            "never_fired": never}


def append(findings, repo, feature, task, loaded, missing=None):
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
            "file": (item.get("location") or {}).get("file") or item.get("file"),
            "problem": (item.get("problem") or "")[:200], "evidence": (item.get("evidence") or "")[:300], "proof_level": item.get("proof_level"),
            "covered_rule": find_rule(agent, category), "domain_loaded": domain in loaded or domain in CORE_DOMAINS})
        if missing is not None and not (item.get("problem") and item.get("evidence")):
            missing.append(item.get("id") or f"{agent}/{category}")
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
            covered = find_rule(last["agent"], last["category"]) or last.get("covered_rule")
            # regra só de texto que volta a falhar sobe para checagem automática
            escalate = bool(covered) and ("impõe: texto" in covered or "impõe:" not in covered)
            out.append({"identity": ident, "agent": last["agent"], "category": last["category"], "occurrences": rows,
                        "covered_rule": covered, "domain_loaded": last.get("domain_loaded"), "escalate": escalate})
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
    a.add_argument("--feature-dir", default="")
    g = sub.add_parser("guard-rules")
    g.add_argument("--guard", required=True)
    g.add_argument("--domains", default="")
    g.add_argument("--out", default="")
    u = sub.add_parser("unused")
    u.add_argument("--feature", required=True)
    u.add_argument("--feature-dir", default="")
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
        recorded = load_guard_rules(args.feature_dir)
        loaded |= set((recorded or {}).get("domains", []))
        missing = []
        written = append(data, args.repo, args.feature, args.task, loaded, missing)
        if missing:
            print(f"aviso: {len(missing)} achado(s) sem problem/evidence: {missing}", file=sys.stderr)
        print(json.dumps({"written": written, "missing_text": missing, "guard_rules": recorded is not None}))
    elif args.cmd == "guard-rules":
        domains = {d.strip() for d in args.domains.split(",") if d.strip()}
        out = args.out or os.path.join(os.path.dirname(os.path.abspath(args.guard)), "guard-rules.json")
        print(json.dumps({"rules": len(write_guard_rules(args.guard, domains, out)["rules"]), "out": out}))
    elif args.cmd == "unused":
        fdir = args.feature_dir or os.path.expanduser(f"~/.claude/dev/features/{args.feature}")
        print(json.dumps(unused(args.feature, fdir), ensure_ascii=False))
    elif args.cmd == "triggers":
        print(json.dumps(triggers(args.threshold, args.min_tasks), ensure_ascii=False))
    else:
        mark_processed(args.identity, args.action)
        print(json.dumps({"ok": True}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
