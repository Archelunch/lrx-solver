"""Self-contained HTML report for one campaign run or a comparison of runs.

Style lives in report_head.html. Everything is read from run directories via
trace.py; nothing is computed that the evaluator did not log.
"""

import html
import json
import time
from pathlib import Path

from .trace import best_so_far, candidate_trace, children, load_run, overview

HEAD = Path(__file__).with_name("report_head.html")
SERIES = [
    "var(--dg-blue)",
    "var(--dg-amber)",
    "var(--dg-green)",
    "var(--dg-red)",
    "var(--st-park)",
    "var(--muted)",
]
STATUS_FLAP = {
    "keep": "st-done",
    "discard": "st-idle",
    "invalid": "st-fail",
    "duplicate": "st-park",
}
FAIL_FLOOR = -1100.0  # scores below this are sanity failures; clip for the chart
MAX_LINEAGE = 600


def esc(x):
    return html.escape("" if x is None else str(x))


def fmt(x, digits=2):
    if x is None:
        return "–"
    if isinstance(x, float):
        return f"{x:,.{digits}f}"
    return esc(x)


def page(title, body):
    head = HEAD.read_text().replace("{{TITLE}}", esc(title))
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"{head}\n</head>\n<body>\n{body}\n{SCRIPT}\n</body>\n</html>\n"
    )


def masthead(title, sub, meta):
    spans = "".join(f"<span>{esc(m)}</span>" for m in meta if m)
    return (
        '<header class="signage masthead"><div class="wrap"><div class="row"><div>'
        f'<h1>{esc(title)}</h1><p class="sub">{sub}</p></div>'
        f'<div class="meta">{spans}</div></div></div></header>'
    )


def nav(items):
    links = "".join(f'<a href="#{a}">{esc(b)}</a>' for a, b in items)
    return f'<nav class="gates" aria-label="Sections"><div class="wrap">{links}</div></nav>'


def section(sid, title, lede, inner):
    return (
        f'<section id="{sid}"><div class="wrap"><div class="section-head"><div>'
        f'<h2>{esc(title)}</h2></div><p class="lede">{lede}</p></div>{inner}</div></section>'
    )


def board(title, clock, headers, rows):
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join(f'<tr class="row">{r}</tr>' for r in rows)
    return (
        f'<div class="board"><div class="board-title"><h3>{esc(title)}</h3>'
        f'<span class="clock">{esc(clock)}</span></div><div class="scroll"><table>'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div></div>"
    )


def flap(text, cls):
    return f'<span class="flap {cls}">{esc(text)}</span>'


# ---------------------------------------------------------------- chart
def progress_chart(runs, width=1100, height=320):
    """Best-so-far score per proposal for each run, plus candidate dots."""
    pad_l, pad_r, pad_t, pad_b = 64, 16, 16, 34
    series = [best_so_far(r) for r in runs]
    xs = max((len(s) for s in series), default=1)
    ys = [
        c.get("score")
        for r in runs
        for c in r["candidates"]
        if c.get("valid") and c.get("score") is not None
    ]
    if not ys:
        return '<p class="muted">No valid candidates yet.</p>'
    ymin = max(FAIL_FLOOR, min(ys))
    ymax = max(ys)
    if ymax - ymin < 1:
        ymin, ymax = ymin - 1, ymax + 1
    span = ymax - ymin
    ymin -= span * 0.05
    ymax += span * 0.05

    def X(i):
        return pad_l + (width - pad_l - pad_r) * (i / max(1, xs - 1))

    def Y(v):
        v = max(ymin, min(ymax, v))
        return pad_t + (height - pad_t - pad_b) * (1 - (v - ymin) / (ymax - ymin))

    parts = [
        f'<svg class="chart wide" viewBox="0 0 {width} {height}" role="img" '
        'aria-label="Best score so far by proposal">'
    ]
    for k in range(5):
        v = ymin + (ymax - ymin) * k / 4
        y = Y(v)
        parts.append(
            f'<line class="grid" x1="{pad_l}" x2="{width - pad_r}" y1="{y:.1f}" y2="{y:.1f}"/>'
        )
        parts.append(
            f'<text x="{pad_l - 6}" y="{y + 4:.1f}" text-anchor="end">{v:,.0f}</text>'
        )
    parts.append(
        f'<line class="axis" x1="{pad_l}" x2="{width - pad_r}" y1="{height - pad_b}" y2="{height - pad_b}"/>'
    )
    for k in range(0, xs, max(1, xs // 10)):
        parts.append(
            f'<text x="{X(k):.1f}" y="{height - pad_b + 16}" text-anchor="middle">{k}</text>'
        )
    parts.append(
        f'<text class="lbl" x="{width - pad_r}" y="{height - 4}" text-anchor="end">PROPOSAL</text>'
    )
    for idx, (run, s) in enumerate(zip(runs, series)):
        color = SERIES[idx % len(SERIES)]
        for i, c in enumerate(run["candidates"]):
            if c.get("score") is None or not c.get("valid"):
                y, fill = Y(ymin), "var(--dg-red)"
            else:
                y = Y(c["score"])
                fill = color if c.get("status") in ("keep", None) else "var(--muted)"
            parts.append(
                f'<circle cx="{X(i):.1f}" cy="{y:.1f}" r="{3.2 if c.get("status") == "keep" else 2.2}" '
                f'fill="{fill}" opacity="{0.95 if c.get("status") == "keep" else 0.45}">'
                f"<title>#{c['id']} {esc(c.get('status'))} {fmt(c.get('score'))}</title></circle>"
            )
        pts = [(X(i), Y(v)) for i, v in s if v is not None]
        if pts:
            d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            parts.append(
                f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2.5"/>'
            )
    parts.append("</svg>")
    legend = "".join(
        f'<span><i style="background:{SERIES[i % len(SERIES)]}"></i>{esc(r["name"])}</span>'
        for i, r in enumerate(runs)
    )
    legend += (
        '<span><i class="dot" style="background:var(--muted)"></i>discarded</span>'
        '<span><i class="dot" style="background:var(--dg-red)"></i>invalid (plotted at floor)</span>'
    )
    note = (
        f"Scores below {FAIL_FLOOR:,.0f} (sanity failures) are clipped to the floor."
        if min(ys) < FAIL_FLOOR
        else ""
    )
    return (
        f'<figure class="panel">{"".join(parts)}<div class="legend">{legend}</div>'
        f"<figcaption>Line: best train score so far. Dots: every candidate in log order. {note}</figcaption></figure>"
    )


# ---------------------------------------------------------------- sections
def outcome_rows(run):
    o = overview(run)
    improved = (
        o["best"] is not None
        and o["seed_best"] is not None
        and o["best"] > o["seed_best"]
    )
    st = o["statuses"]
    usage = o["usage"]
    rows = [
        (
            "Best train score",
            f"{fmt(o['seed_best'])} → {fmt(o['best'])}",
            flap(
                "improved" if improved else "flat", "st-done" if improved else "st-idle"
            ),
            f"candidate #{o['best_id']}",
        ),
        (
            "Feasible on train probes",
            fmt(o["feasible"]),
            flap(
                "yes" if o["feasible"] else "no",
                "st-done" if o["feasible"] else "st-fail",
            ),
            "no failures and no excess over T on probes",
        ),
        (
            "Proposals",
            fmt(o["proposals"]),
            flap(
                o["stop_reason"] or ("running" if not run["complete"] else "done"),
                "st-run" if not run["complete"] else "st-plain",
            ),
            " · ".join(f"{k} {v}" for k, v in st.items()),
        ),
        (
            "Spend",
            f"${usage.get('estimated_usd', 0) or 0:.4f}",
            flap(o["provider"], "st-park"),
            f"{usage.get('requests', 0)} requests · {usage.get('input_tokens', 0)} in / "
            f"{usage.get('output_tokens', 0)} out tokens · estimate, not a bill",
        ),
        (
            "Wall time",
            f"{fmt(o['wall_seconds'], 1)} s",
            flap(o["engine"], "st-plain"),
            f"{o['batches']} batches · {o['reflections']} reflections",
        ),
    ]
    return [
        f'<td class="step">{esc(a)}</td><td class="num">{b}</td><td>{c}</td>'
        f'<td class="note">{esc(d)}</td>'
        for a, b, c, d in rows
    ]


def graph_table(graphs, title):
    if not graphs:
        return ""
    rows = []
    for g in graphs:
        fail = (g.get("failures") or 0) + (g.get("incomplete") or 0)
        excess = g.get("excess_T")
        cls_f = "heat-ok" if fail == 0 else "heat-bad"
        cls_e = (
            ""
            if excess is None
            else "heat-ok"
            if excess <= 0
            else "heat-warn"
            if excess <= 10
            else "heat-bad"
        )
        rows.append(
            f'<tr><td class="mono">{esc(g.get("graph"))}</td><td>{esc(g.get("role"))}</td>'
            f'<td class="num {cls_f}">{fail}</td><td class="num">{fmt(g.get("value_max"))}</td>'
            f'<td class="num">{fmt(g.get("T"))}</td><td class="num {cls_e}">{fmt(excess)}</td>'
            f'<td class="num">{fmt(g.get("radius"))}</td><td class="num">{fmt(g.get("gap_mean"))}</td>'
            f'<td class="num">{fmt(g.get("score"))}</td></tr>'
        )
    return (
        f'<h3 style="margin:18px 0 8px">{esc(title)}</h3><div class="panel scroll"><table class="plain">'
        "<thead><tr><th>Graph</th><th>Role</th><th>Failures</th><th>Max value</th><th>T</th>"
        "<th>Excess over T</th><th>Radius</th><th>Mean gap</th><th>Score</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def lineage(run):
    kids = children(run)
    depth = {}
    order = []

    def walk(pid, d):
        for c in kids.get(pid, []):
            depth[c["id"]] = d
            order.append(c)
            walk(c["id"], d + 1)

    walk(None, 0)
    rows = []
    for c in order[:MAX_LINEAGE]:
        tr = candidate_trace(run, c["id"])
        status = "seed" if c.get("mode") == "seed" else c.get("status", "?")
        parents = c.get("parents") or []
        name = (c.get("spec") or {}).get("name", "")
        meta = (
            f"{c.get('mode')} · island {fmt(c.get('island'))} · parents "
            f"{', '.join('#' + str(p) for p in parents) or '–'} · "
            f"${c.get('cost_usd') or 0:.4f} · llm {fmt(c.get('llm_seconds'))} s · "
            f"eval {fmt(c.get('seconds'))} s"
        )
        detail = [
            f"<p><b>Score</b> {fmt(c.get('score'))} · <b>hash</b> "
            f"<code>{esc(c.get('hash'))}</code> · <b>error</b> "
            f"{esc(c.get('proposer_error') or (tr.get('eval') or {}).get('error') or '–')}</p>"
        ]
        if c.get("spec") is not None:
            detail.append(_pre("Candidate", pretty_spec(c["spec"])))
        if tr.get("eval"):
            detail.append(
                graph_table(
                    [
                        dict(g, score=g.get("score"))
                        for g in tr["eval"].get("graphs", [])
                    ],
                    "Evaluation",
                )
            )
        elif c.get("graphs"):
            detail.append(graph_table(c["graphs"], "Evaluation"))
        if c.get("feedback"):
            detail.append(
                _pre(
                    "Feedback shown to the proposer next",
                    json.dumps(c["feedback"], indent=1),
                )
            )
        if c.get("prompt_messages"):
            sys_note = (
                f"system prompt: prompts/system-{c.get('prompt_system_sha')}.txt\n\n"
                if c.get("prompt_system_sha")
                else ""
            )
            user = "\n\n".join(m.get("content", "") for m in c["prompt_messages"])
            detail.append(_pre("Prompt (user part)", sys_note + user))
        if c.get("model_reasoning"):
            detail.append(
                _pre(
                    f"Model reasoning ({fmt(c.get('reasoning_tokens'))} tokens)",
                    c["model_reasoning"],
                )
            )
        if c.get("model_text"):
            detail.append(_pre("Model reply", c["model_text"]))
        indent = "&nbsp;&nbsp;" * min(depth.get(c["id"], 0), 12) + (
            "└ " if depth.get(c["id"]) else ""
        )
        rows.append(
            f'<details class="tt-row" id="c-{c["id"]}"><summary><span class="idx">#{c["id"]}</span>'
            f'<span><div class="what"><span class="indent">{indent}</span>{fmt(c.get("score"))} '
            f'<span class="muted">{esc(name)}</span></div><div class="files">{esc(meta)}</div></span>'
            f'<span class="risk {esc(status)}">{esc(status)}</span></summary>'
            f'<div class="detail">{"".join(detail)}</div></details>'
        )
    more = (
        f'<p class="muted">Showing {MAX_LINEAGE} of {len(order)} candidates.</p>'
        if len(order) > MAX_LINEAGE
        else ""
    )
    return (
        '<div class="board-controls light" style="margin-bottom:10px">'
        '<button class="btn" id="tt-open">Expand all</button>'
        '<button class="btn" id="tt-close">Collapse all</button></div>'
        f'<div class="timetable">{"".join(rows)}</div>{more}'
    )


def pretty_spec(spec):
    """One line per top-level key; one line per rule. Expressions stay compact."""
    if not isinstance(spec, dict):
        return json.dumps(spec)
    lines = []
    for key, value in spec.items():
        if key == "rules" and isinstance(value, list):
            lines.append('  "rules": [')
            lines += [f"    {json.dumps(rule)}," for rule in value]
            lines.append("  ],")
        else:
            lines.append(f"  {json.dumps(key)}: {json.dumps(value)},")
    return "{\n" + "\n".join(lines).rstrip(",") + "\n}"


def _pre(label, text):
    return f'<div><div class="ba"><div><div class="lab">{esc(label)}</div></div></div><pre><code>{esc(text)}</code></pre></div>'


def islands_section(run):
    if not run["batches"]:
        return '<p class="muted">No batches logged.</p>'
    last = run["batches"][-1]
    out = []
    if last.get("islands"):
        rows = [
            f'<td class="step">Island {i}</td><td class="num">{fmt(s.get("best"))}</td>'
            f'<td class="num">{s.get("visits")}</td><td class="num">{fmt(s.get("G"), 4)}</td>'
            f'<td class="num">{fmt(s.get("reward"), 3)}</td>'
            f'<td class="note">{", ".join("#" + str(m) for m in s.get("members", []))}</td>'
            for i, s in enumerate(last["islands"])
        ]
        out.append(
            board(
                "Islands",
                f"after batch {last['batch']}",
                ["Island", "Best", "Visits", "G (signal)", "Reward", "Members"],
                rows,
            )
        )
    if last.get("front"):
        rows = [
            f'<td class="step">#{k}</td><td class="num">{v}</td>'
            for k, v in sorted(last["front"].items(), key=lambda kv: -kv[1])
        ]
        out.append(
            board(
                "Pareto front",
                f"after batch {last['batch']}",
                ["Candidate", "Graphs won"],
                rows,
            )
        )
    rows = []
    for b in run["batches"]:
        usage = b.get("usage") or {}
        modes = ", ".join(r.get("mode", "") for r in b.get("requests", []))
        rows.append(
            f'<tr><td class="num">{b["batch"]}</td><td class="num">{b["proposals"]}</td>'
            f'<td class="num">{fmt(b.get("best_score"))}</td><td class="num">{b.get("since_improvement")}</td>'
            f'<td class="num">{fmt(b.get("propose_seconds"))}</td><td class="num">{fmt(b.get("eval_seconds"))}</td>'
            f'<td class="num">${usage.get("estimated_usd", 0) or 0:.4f}</td><td>{esc(modes)}</td></tr>'
        )
    out.append(
        '<h3 style="margin:18px 0 8px">Batches</h3><div class="panel scroll"><table class="plain">'
        "<thead><tr><th>Batch</th><th>Proposals</th><th>Best</th><th>Since improvement</th>"
        "<th>Propose s</th><th>Eval s</th><th>Spend</th><th>Modes</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )
    return "".join(out)


def reflections_section(run):
    if not run["reflections"]:
        return (
            '<p class="muted">No reflections (none triggered or offline stub only).</p>'
        )
    items = []
    for r in run["reflections"]:
        status = "st-fail" if r.get("error") else "st-done"
        items.append(
            f'<div class="dec">{flap("tactics", status)}<div><h3>After {fmt(r.get("proposals"))} proposals</h3>'
            f"<pre><code>{esc(r.get('text') or r.get('error'))}</code></pre></div></div>"
        )
    return f'<div class="decs">{"".join(items)}</div>'


def heldout_section(run):
    if not run["heldout"]:
        return '<p class="muted">No held-out evaluation logged (run incomplete?).</p>'
    out = []
    for h in run["heldout"]:
        out.append(
            graph_table(
                h.get("graphs", []),
                f"Candidate #{h['id']} · train {fmt(h.get('train_score'))} · "
                f"feasible on all graphs: {h.get('feasible_all')}",
            )
        )
    return "".join(out)


def single_report(run):
    o = overview(run)
    cfg = run["config"] or {}
    start = run["start"] or {}
    best = {"id": o["best_id"]}
    best_graphs = []
    if best["id"] is not None:
        tr = candidate_trace(run, best["id"])
        best_graphs = (tr.get("eval") or {}).get("graphs") or tr.get("graphs") or []
    sub = (
        f"{esc(o['engine'])} over {esc(', '.join(o['kinds'] or []))} candidates, "
        f"proposer {esc(o['provider'])}. Best train score {fmt(o['seed_best'])} → "
        f"{fmt(o['best'])} after {o['proposals']} proposals."
    )
    meta = [
        time.strftime(
            "%Y-%m-%d %H:%M",
            time.localtime(Path(run["dir"], "events.jsonl").stat().st_mtime),
        ),
        f"git {str(start.get('git_commit') or '?')[:10]}",
        f"evaluator {start.get('evaluator_sha256', '?')}",
        "run complete" if run["complete"] else "RUN INCOMPLETE",
    ]
    body = [
        masthead(f"Campaign {run['name']}", sub, meta),
        nav(
            [
                ("outcome", "Outcome"),
                ("progress", "Progress"),
                ("graphs", "Graphs"),
                ("search", "Search state"),
                ("lineage", "Lineage"),
                ("reflections", "Reflections"),
                ("heldout", "Held-out"),
                ("config", "Config"),
            ]
        ),
        "<main>",
        section(
            "outcome",
            "Outcome",
            "Train split only. Held-out numbers are in their own section and were never shown to the proposer.",
            board(
                "Outcomes",
                "measured from events.jsonl",
                ["Metric", "Value", "Status", "Detail"],
                outcome_rows(run),
            ),
        ),
        section(
            "progress",
            "Progress",
            "Does the search move? The line should step up; flat means no candidate beat the best so far.",
            progress_chart([run]),
        ),
        section(
            "graphs",
            "Best candidate by graph",
            "Failures must be 0 everywhere. Excess over T matters only for m ≥ 8. Mean gap is the distance to the exact optimum.",
            graph_table(best_graphs, f"Candidate #{best.get('id')}"),
        ),
        section(
            "search",
            "Search state",
            "Islands (AdaEvolve) or Pareto front (GEPA) after the last batch, and per-batch timing and spend.",
            islands_section(run),
        ),
        section(
            "lineage",
            "Lineage",
            "Every candidate, nested under its first parent. Open a row for the candidate JSON, evaluation, feedback, prompt and model reply.",
            lineage(run),
        ),
        section(
            "reflections",
            "Reflections",
            "Tactics produced on stagnation and injected into later prompts.",
            reflections_section(run),
        ),
        section(
            "heldout",
            "Held-out",
            "Final check of the top candidates. Not used as feedback.",
            heldout_section(run),
        ),
        section(
            "config",
            "Config",
            "Exact campaign configuration.",
            f"<pre><code>{esc(json.dumps(cfg, indent=2))}</code></pre>",
        ),
        "</main>",
        footer(run),
    ]
    return page(f"LRX {run['name']}", "".join(body))


def compare_report(runs):
    rows = []
    for r in runs:
        o = overview(r)
        usage = o["usage"]
        improved = (
            o["best"] is not None
            and o["seed_best"] is not None
            and o["best"] > o["seed_best"]
        )
        rows.append(
            f'<td class="step">{esc(o["engine"])}</td><td class="note">{esc(r["name"])}</td>'
            f'<td class="num">{o["proposals"]}</td><td class="num">{fmt(o["seed_best"])} → {fmt(o["best"])}</td>'
            f"<td>{flap('improved' if improved else 'flat', 'st-done' if improved else 'st-idle')}</td>"
            f'<td class="num">${usage.get("estimated_usd", 0) or 0:.4f}</td><td class="num">{fmt(o["wall_seconds"], 1)} s</td>'
        )
    sub = (
        f"{len(runs)} runs. Compare at equal proposal and dollar budgets, with at least three seeds, "
        "before calling a winner."
    )
    body = [
        masthead("Campaign comparison", sub, [time.strftime("%Y-%m-%d %H:%M")]),
        nav([("runs", "Runs"), ("progress", "Progress")]),
        "<main>",
        section(
            "runs",
            "Runs",
            "Train scores; held-out is per run.",
            board(
                "Runs",
                "measured",
                [
                    "Engine",
                    "Run",
                    "Proposals",
                    "Seed → best",
                    "Status",
                    "Spend",
                    "Wall",
                ],
                rows,
            ),
        ),
        section(
            "progress",
            "Progress",
            "Best-so-far per proposal for each run.",
            progress_chart(runs),
        ),
        "</main>",
        '<footer><div class="wrap"><p><b>Unverified.</b> Probe scores are finite evidence; '
        "nothing here is a proof.</p></div></footer>",
    ]
    return page("LRX campaign comparison", "".join(body))


def footer(run):
    return (
        '<footer><div class="wrap">'
        f"<p><b>Evidence.</b> <code>{esc(run['dir'])}</code>: events.jsonl, evals/, prompts/, summary.json.</p>"
        "<p><b>Unverified.</b> Scores are finite probe evidence on the registry graphs. A feasible "
        "candidate is a lead, not a proof. Spend is an estimate from configured rates.</p>"
        "</div></footer>"
    )


SCRIPT = """<script>
(function(){
  const $=s=>document.querySelector(s), $$=s=>Array.from(document.querySelectorAll(s));
  const o=$('#tt-open'), c=$('#tt-close');
  if(o) o.onclick=()=>$$('.tt-row').forEach(d=>d.open=true);
  if(c) c.onclick=()=>$$('.tt-row').forEach(d=>d.open=false);
  const links=$$('nav.gates a'); const secs=links.map(a=>$(a.getAttribute('href')));
  if('IntersectionObserver' in window){
    const io=new IntersectionObserver(es=>{es.forEach(e=>{if(e.isIntersecting){links.forEach(l=>l.classList.toggle('on',l.getAttribute('href')==='#'+e.target.id));}})},{rootMargin:'-40% 0px -55% 0px'});
    secs.forEach(s=>s&&io.observe(s));
  }
  if(location.hash){const d=document.getElementById(location.hash.slice(1));if(d&&d.tagName==='DETAILS')d.open=true;}
})();
</script>"""


def write_report(run_dirs, out=None):
    runs = [load_run(d) for d in run_dirs]
    if len(runs) == 1:
        doc = single_report(runs[0])
        out = Path(out) if out else Path(runs[0]["dir"]) / "report.html"
    else:
        doc = compare_report(runs)
        out = (
            Path(out)
            if out
            else Path(runs[0]["dir"]).parent
            / f"compare-{time.strftime('%y%m%d-%H%M%S')}.html"
        )
    out.write_text(doc)
    return str(out), len(doc.encode())
