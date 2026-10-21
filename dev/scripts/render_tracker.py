#!/usr/bin/env python3
"""Gera o tracker.html da feature a partir de plan.json, state.json e dos logs, sem gastar token."""
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import devgraph  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
STEP_NAMES = {1: ("escopo", "Opus"), 2: ("leitura", "Haiku medium"), 3: ("avaliação", "Opus"),
              4: ("testes", "Sonnet medium"), 5: ("implementação", "Sonnet medium"), 6: ("review lean", "master-review")}
PHASES = {"requirements": "requisitos", "planning": "planejamento", "execution": "em andamento",
          "paused": "pausada", "done": "concluída"}
GATE_STATUS = {"pending": "pendente", "running": "rodando", "passed": "passou", "blocked": "bloqueado"}
CLUSTER_COLORS = ["--ca", "--cb", "--cc"]
NODE_W, NODE_H, ROW_H = 100, 64, 100
COLUMNS = {1: [120], 2: [10, 230], 3: [10, 120, 230]}

e = html.escape


def _read_jsonl(path):
    if not os.path.exists(path):
        return []
    rows = []
    with open(path) as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue  # linha corrompida (escrita interrompida) não derruba o tracker
    return rows


def _cluster_color(label, labels):
    return f"var({CLUSTER_COLORS[labels.index(label) % len(CLUSTER_COLORS)]})" if label in labels else "var(--muted)"


def _busy(state):
    busy = {}
    for w in state.get("workers", []):
        a = w.get("assignment") or {}
        for tid in [a.get("task")] + list(a.get("tasks", [])):
            if tid:
                busy[tid] = a
    return busy


def _task_label(tid, ts, busy, cluster):
    status = ts.get("status", "pending")
    if status == "done":
        return "concluída", "p-done", "n-done"
    if status == "blocked":
        return f"bloqueada: {ts.get('block_reason') or '?'}", "p-blocked", "n-blocked"
    if status == "implemented":
        if tid in busy and busy[tid].get("kind") == "review_lean":
            return "em review", "p-active", "n-active"
        return f"aguarda review do cluster {cluster}", "p-wait", "n-wait"
    running = ts.get("step_running")
    if running is not None or tid in busy:
        step = running or busy.get(tid, {}).get("from_step") or (busy.get(tid, {}).get("steps") or [1])[0]
        if busy.get(tid, {}).get("kind") == "pre_read":
            return "leitura antecipada", "p-blocked", "n-blocked"
        return f"passo {step}", "p-active", "n-active"
    return "pendente", "p-blocked", "n-blocked"


def _wrap(title, width=14):
    words, lines, cur = title.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    lines.append(cur)
    if len(lines) > 2:
        lines = [lines[0], " ".join(lines[1:])[: width + 2]]
    return lines


def _layout(plan):
    deps = devgraph._deps(plan)
    depth = {}

    def walk(n):
        if n not in depth:
            depth[n] = 0 if not deps[n] else 1 + max(walk(d) for d in deps[n] if d in deps)
        return depth[n]

    for n in deps:
        walk(n)
    cluster = (plan.get("analysis") or {}).get("task_cluster", {})
    rows = []
    for level in range(max(depth.values(), default=-1) + 1):
        nodes = sorted([n for n in deps if depth[n] == level], key=lambda n: (cluster.get(n, "~"), n))
        for i in range(0, len(nodes), 3):
            rows.append(nodes[i:i + 3])
    pos = {}
    for r, row in enumerate(rows):
        for c, node in enumerate(row):
            pos[node] = (COLUMNS[len(row)][c], 20 + r * ROW_H)
    return pos, len(rows)


def _graph_svg(plan, state, busy):
    analysis = plan.get("analysis") or {}
    cluster, labels = analysis.get("task_cluster", {}), list(analysis.get("clusters", {}))
    critical = analysis.get("critical_path", [])
    crit_edges = set(zip(critical, critical[1:]))
    pos, nrows = _layout(plan)
    tasks, gates, deps = devgraph._tasks(plan), devgraph._gates(plan), devgraph._deps(plan)
    height = 20 + nrows * ROW_H
    parts = [f'<svg class="dag" viewBox="0 0 340 {height}" role="img" aria-label="Grafo de dependências das tasks">',
             '<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" '
             'orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="var(--muted)"/></marker>'
             '<marker id="arc" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" '
             'orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="var(--crit)"/></marker></defs>']
    for node, ds in deps.items():
        for d in ds:
            if d not in pos or node not in pos:
                continue
            (x1, y1), (x2, y2) = pos[d], pos[node]
            sx, sy, tx, ty = x1 + NODE_W / 2, y1 + NODE_H, x2 + NODE_W / 2, y2 - 2
            mid = (sy + ty) / 2
            is_crit = (d, node) in crit_edges
            parts.append(f'<path class="e{" c" if is_crit else ""}" d="M{sx} {sy} C{sx} {mid},{tx} {mid},{tx} {ty}" '
                         f'marker-end="url(#{"arc" if is_crit else "ar"})"/>')
    for node, (x, y) in pos.items():
        if node in gates:
            status = state.get("gates", {}).get(node, {}).get("status", "pending")
            cls = "n-done" if status == "passed" else "n-gate"
            lines = _wrap(gates[node].get("title", ""))
            parts.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{NODE_W}" height="{NODE_H}" rx="22"/>')
            parts.append(f'<text x="{x + 10}" y="{y + 16}" class="sub" style="fill:var(--gate)">{e(node)} · gate</text>')
        else:
            t = tasks[node]
            label = cluster.get(node, "")
            _, _, cls = _task_label(node, state.get("tasks", {}).get(node, {}), busy, label)
            lines = _wrap(t["title"])
            parts.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{NODE_W}" height="{NODE_H}" rx="8"/>')
            parts.append(f'<text x="{x + 10}" y="{y + 16}" class="sub">{e(node)} · '
                         f'<tspan style="fill:{_cluster_color(label, labels)}">{e(label)}</tspan> · risco {t["risk"]}</text>')
        for i, line in enumerate(lines):
            parts.append(f'<text x="{x + 10}" y="{y + 34 + i * 16}" class="ttl">{e(line)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _workers(state, tasks):
    cards = []
    for w in state.get("workers", []):
        a = w.get("assignment")
        if not a:
            cards.append(f'<div class="worker"><span class="slot">W{w["slot"]}</span><b>livre</b>'
                         f'<span class="step">sem trabalho disponível</span></div>')
            continue
        kind = a.get("kind")
        if kind in ("task", "pre_read"):
            tid = a["task"]
            ts = state.get("tasks", {}).get(tid, {})
            step = ts.get("step_running") or a.get("from_step") or (a.get("steps") or [1])[0]
            effort = tasks.get(tid, {}).get("opus_effort", "medium")

            def model_of(n):
                model = STEP_NAMES.get(n, ("?", "?"))[1]
                return f"{model} {effort}" if model == "Opus" else model

            name, model = STEP_NAMES.get(step, ("?", "?"))[0], model_of(step)
            if kind == "pre_read":
                steps = a.get("steps") or [1, 2]
                step = steps[-1]
                name, model = "leitura antecipada", " + ".join(model_of(n) for n in steps)
            title = f"{tid} · {tasks.get(tid, {}).get('title', '')}"
            done = set(ts.get("steps_done", []))
            bars = "".join(f'<i class="{"d" if n in done else "a" if n == step else ""}"></i>' for n in range(1, 7))
            label = "passos " + "–".join(str(n) for n in a["steps"]) if kind == "pre_read" else f"passo {step}"
            detail = f"{label} · {name} · {model}"
        elif kind == "review_lean":
            title, detail, bars = "Review lean", ", ".join(a.get("tasks", [])) + (" · roast" if a.get("roast") else ""), ""
        else:
            title, detail, bars = f"Gate {a.get('gate')}", "/master-review full", ""
        cards.append(f'<div class="worker"><span class="slot">W{w["slot"]}</span><b>{e(title)}</b>'
                     f'<span class="step">{e(detail)}</span>' + (f'<div class="steps">{bars}</div>' if bars else "") + "</div>")
    return "".join(cards)


def _task_rows(plan, state, busy):
    analysis = plan.get("analysis") or {}
    cluster, labels, ahead = analysis.get("task_cluster", {}), list(analysis.get("clusters", {})), analysis.get("path_ahead", {})
    rows = []
    order = sorted(plan.get("tasks", []), key=lambda t: (-ahead.get(t["id"], 0), t["id"]))
    for t in order:
        label = cluster.get(t["id"], "")
        text, pill, _ = _task_label(t["id"], state.get("tasks", {}).get(t["id"], {}), busy, label)
        cells = [("Cluster", f'<span class="cl" style="color:{_cluster_color(label, labels)}">{e(label)}</span>'),
                 ("Compl.", t["complexity"]), ("Risco", t["risk"]), ("Custo", devgraph.task_cost(t)),
                 ("Caminho à frente", ahead.get(t["id"], "")), ("Depende de", ", ".join(t.get("depends_on", [])) or "—"),
                 ("Status", f'<span class="pill {pill}">{e(text)}</span>')]
        tds = "".join(f'<td data-l="{k}"{" class=n" if k in ("Compl.", "Risco", "Custo", "Caminho à frente") else ""}>{v}</td>'
                      for k, v in cells)
        rows.append(f'<tr><td class="first">{e(t["id"])} · {e(t["title"])}</td>{tds}</tr>')
    return "".join(rows)


def _list(items, empty):
    if not items:
        return f'<p class="src">{e(empty)}</p>'
    return '<ul class="plain">' + "".join(items) + "</ul>"


def render(plan, state, decisions, costs, learned, heavy=None, situation=None):
    with open(os.path.join(HERE, "tracker_template.html")) as f:
        template = f.read()
    feature = state.get("title") or state.get("feature", "feature")
    phase = state.get("phase", "requirements")
    pill = {"paused": "p-wait", "done": "p-done"}.get(phase, "p-active")
    checkpoint = state.get("checkpoint") or {}
    branches = sorted({r.get("feature_branch", "") for r in state.get("repos", {}).values() if r.get("feature_branch")})
    body = [f'<h1>{e(feature)}</h1><div class="meta"><span><span class="pill {pill}">{e(PHASES.get(phase, phase))}</span></span>'
            f'<span>branch <code>{e(", ".join(branches) or "—")}</code></span>'
            f'<span>repos: {e(", ".join(state.get("repos", {})) or "—")}</span>'
            f'<span>checkpoint {e(checkpoint.get("at", "")[11:16])} · {e(checkpoint.get("note", ""))}</span>'
            f'<span>pausar: <code>/dev stop</code></span></div>']
    if situation and situation.get("lines"):
        items = "".join(f"<li>{e(line)}</li>" for line in situation["lines"])
        body.append(f'<section class="card"><h2>Situação agora</h2><ul class="plain">{items}</ul>'
                    f'<p class="src" style="margin:8px 0 0">atualizado {e(str(situation.get("at", ""))[11:16])}</p></section>')
    decision_items = [f'<li>{e(d.get("id", ""))} · {e(d.get("text", ""))}<br><span class="src">origem: {e(d.get("origin", ""))}</span></li>'
                      for d in decisions]
    if not plan or not plan.get("tasks"):
        body.append('<section class="card"><h2>Requisitos</h2><p class="src">Fase de requisitos e planejamento. '
                    'O grafo aparece quando o plano for gravado.</p></section>')
        body.append(f'<section class="card"><h2>Decisões</h2>{_list(decision_items, "Nenhuma decisão ainda.")}</section>')
        return template.replace("{{FEATURE}}", e(state.get("feature", ""))).replace("{{TITLE}}", e(feature)).replace("{{BODY}}", "\n".join(body))

    tasks = devgraph._tasks(plan)
    busy = _busy(state)
    tstate = state.get("tasks", {})
    done = sum(1 for t in tasks if tstate.get(t, {}).get("status") == "done")
    occupied = sum(1 for w in state.get("workers", []) if w.get("assignment"))
    gates = plan.get("gates", [])
    passed = sum(1 for g in gates if state.get("gates", {}).get(g["id"], {}).get("status") == "passed")
    pct = round(100 * done / len(tasks), 1) if tasks else 0
    heavy_text = f"{heavy[0]} / {heavy[1]}" if heavy is not None else "—"
    body.append('<div class="kpis">'
                f'<div class="kpi"><div class="v">{done} / {len(tasks)}</div><div class="l">tasks concluídas</div>'
                f'<div class="bar"><i style="width:{pct}%"></i></div></div>'
                f'<div class="kpi"><div class="v">{occupied} / {len(state.get("workers", [])) or 4}</div><div class="l">workers ativos</div></div>'
                f'<div class="kpi"><div class="v">{heavy_text}</div><div class="l">processos pesados</div></div>'
                f'<div class="kpi"><div class="v">{passed} / {len(gates)}</div><div class="l">gates passados</div></div></div>')
    body.append(f'<section class="card"><h2>Workers agora</h2><div class="workers">{_workers(state, tasks)}</div>'
                '<p class="src" style="margin:10px 0 0">Passos: 1 escopo · 2 leitura · 3 avaliação · 4 testes · '
                '5 implementação · 6 review lean</p></section>')
    analysis = plan.get("analysis") or {}
    crit = analysis.get("critical_path", [])
    crit_cost = analysis.get("path_ahead", {}).get(crit[0], 0) if crit else 0
    labels = list(analysis.get("clusters", {}))
    cluster_items = [f'<li><span class="cl" style="color:{_cluster_color(lb, labels)}">{e(lb)}</span> — {e(", ".join(m))}</li>'
                     for lb, m in analysis.get("clusters", {}).items()]
    body.append('<section class="card"><h2>Grafo</h2><div class="graph-wrap"><div>' + _graph_svg(plan, state, busy) +
                '</div><div><div class="legend">'
                '<span><i class="sw" style="border-color:var(--done);background:var(--done-bg)"></i>concluída</span>'
                '<span><i class="sw" style="border-color:var(--active);background:var(--active-bg)"></i>em andamento</span>'
                '<span><i class="sw" style="border-color:var(--wait);background:var(--wait-bg)"></i>aguarda review do cluster</span>'
                '<span><i class="sw" style="border-color:var(--blocked);background:var(--blocked-bg);border-style:dashed"></i>pendente</span>'
                f'<span><i class="line"></i>caminho crítico (custo {crit_cost})</span></div>'
                f'<h2 style="margin-top:16px">Clusters de afinidade (MST)</h2>{_list(cluster_items, "Sem clusters.")}</div></div></section>')
    body.append('<section class="card"><h2>Tasks</h2><table class="resp"><thead><tr><th>Task</th><th>Cluster</th>'
                '<th>Compl.</th><th>Risco</th><th>Custo</th><th>Caminho à frente</th><th>Depende de</th><th>Status</th>'
                f'</tr></thead><tbody>{_task_rows(plan, state, busy)}</tbody></table>'
                '<p class="src" style="margin:10px 0 0">Custo = complexidade × risco. Caminho à frente = custo da task + a '
                'cadeia mais cara depois dela. Entre as prontas, o maior caminho pega worker primeiro.</p></section>')
    gate_items = []
    for g in gates:
        status = state.get("gates", {}).get(g["id"], {}).get("status", "pending")
        gate_items.append(f'<li><span class="pill p-gate">{e(g["id"])}</span> <b>{e(g.get("title", ""))}</b> — espera '
                          f'{e(", ".join(g.get("waits_for", [])))}<br><span class="src">status: {e(GATE_STATUS.get(status, status))}</span></li>')
    body.append(f'<section class="card"><h2>Gates</h2>{_list(gate_items, "Sem gates.")}</section>')
    learned_items = [f'<li><b>{e(x.get("identity", ""))}</b><br><span class="src">{e(x.get("problem", ""))} · {e(x.get("task", ""))}</span></li>'
                     for x in learned]
    by_model = {}
    for c in costs:
        by_model[c.get("model", "?")] = by_model.get(c.get("model", "?"), 0) + (c.get("tokens") or 0)
    cost_rows = "".join(f'<tr><td>{e(m)}</td><td class="n" style="text-align:right">{v:,}</td></tr>' for m, v in by_model.items())
    review_rows = ""
    for r in state.get("reviews", []):
        tokens = f"{r['tokens']:,}" if r.get("tokens") is not None else "—"
        review_rows += (f'<tr><td>Review {e(r.get("kind", ""))} {e(", ".join(r.get("tasks", [])))}</td>'
                        f'<td class="n" style="text-align:right">{tokens}</td></tr>')
    body.append(f'<div class="two"><section class="card"><h2>Decisões</h2>{_list(decision_items, "Nenhuma decisão ainda.")}</section>'
                f'<section class="card"><h2>Aprendizado (/code-guard)</h2>{_list(learned_items, "Nenhum achado registrado nesta feature.")}'
                '<h2 style="margin-top:14px">Custo até agora</h2><table><thead><tr><th>Item</th><th style="text-align:right">Tokens</th>'
                f'</tr></thead><tbody>{cost_rows}{review_rows}</tbody></table></section></div>')
    return template.replace("{{FEATURE}}", e(state.get("feature", ""))).replace("{{TITLE}}", e(feature)).replace("{{BODY}}", "\n".join(body))


def _pid_alive(pid):
    try:
        os.kill(int(pid), 0)
    except (ValueError, ProcessLookupError):
        return False
    except PermissionError:
        return True
    return True


def heavy_status():
    folder = os.environ.get("DEV_HEAVY_DIR", os.path.expanduser("~/.claude/dev/heavy"))
    slots = int(os.environ.get("DEV_HEAVY_SLOTS", "2"))
    live = 0
    if os.path.isdir(folder):
        for name in os.listdir(folder):
            pid_file = os.path.join(folder, name, "pid")
            if name.startswith("slot-") and os.path.isfile(pid_file):
                with open(pid_file) as f:
                    live += any(_pid_alive(p) for p in f.read().split())
    return live, slots


def render_dir(feature_dir):
    def load(name):
        path = os.path.join(feature_dir, name)
        if not os.path.exists(path):
            return None
        with open(path) as f:
            return json.load(f)

    plan, state = load("plan.json"), load("state.json") or {}
    ledger = _read_jsonl(os.path.join(os.environ.get("CODE_GUARD_HOME", os.path.expanduser("~/.claude/code-guard")), "ledger.jsonl"))
    learned = [x for x in ledger if x.get("feature") == state.get("feature")]
    page = render(plan, state, _read_jsonl(os.path.join(feature_dir, "decisions.jsonl")),
                  _read_jsonl(os.path.join(feature_dir, "costs.jsonl")), learned, heavy=heavy_status(),
                  situation=load("situation.json"))
    out = os.path.join(feature_dir, "tracker.html")
    tmp = out + ".tmp"
    with open(tmp, "w") as f:
        f.write(page)
    os.replace(tmp, out)
    return out


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("uso: render_tracker.py <feature_dir>", file=sys.stderr)
        sys.exit(2)
    print(render_dir(sys.argv[1]))
