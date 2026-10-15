"""Rebuild viewer.html (tab title "Pair Attribution Runs") from the picks and run files.

Markup, styles and script are copied from the published viewer (the copy saved from the live
page); the only changes are a v9 source option, a source chip for v9, a run_id chip in each row,
run/task-version in the run header, and no "confidence null" for scripted golds. DATA is rebuilt:
the 43 OAS and 4 v7 baseline runs exactly as published, plus every run in sources.json that has
picks. gold.step is the hand-read decisive step (OAS) or the hand-read pivotal step (v7/v9 manifest
runs), else null; gold.evidence names the scripted pivotal step used by the strict rule.

usage (from benchmarks/safety_monitor):
    uv run --extra dev python ../../analysis_outputs/pair_attribution/build_viewer.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from safety_monitor.analysis import pair_attribution as pa

HERE = Path(__file__).resolve().parent
OUT = HERE / "viewer.html"
MODELS = ("qwen3.5-9b", "us.anthropic.claude-sonnet-5")

HEAD = r'''<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover"><style>:root{color-scheme:light;box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}html{scroll-padding-top:env(safe-area-inset-top,0px)}body{margin:0;padding:0;font:14px -apple-system,BlinkMacSystemFont,sans-serif;background:#fff;color:#000}img{max-width:100%}[hidden]:not([hidden=until-found i]){display:none!important}</style></head><body>
<title>Pair Attribution Runs</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: fixed-height two-pane audit tool; run list left, one run's evidence right. */
:root {
  --bg: #f6f5f1; --panel: #ffffff; --fg: #1d1f1a; --muted: #6b6e63; --line: #d9d8cf;
  --accent: #245c8c; --accent-soft: #e3edf5;
  --unsafe: #a63d2f; --unsafe-soft: #f7e6e2; --safe: #3a6b3e; --safe-soft: #e4efe3;
  --gold: #8a6a12; --gold-soft: #f8efd3; --pick: #245c8c;
  --sans: "IBM Plex Sans", system-ui, sans-serif; --mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #15171a; --panel: #1d2024; --fg: #e6e4dc; --muted: #9a9c92; --line: #343841;
  --accent: #7fb1dc; --accent-soft: #1f2e3c;
  --unsafe: #e08a7c; --unsafe-soft: #3a2420; --safe: #8fc292; --safe-soft: #203022;
  --gold: #e0bd5a; --gold-soft: #3a3018; --pick: #7fb1dc; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #15171a; --panel: #1d2024; --fg: #e6e4dc; --muted: #9a9c92; --line: #343841;
  --accent: #7fb1dc; --accent-soft: #1f2e3c;
  --unsafe: #e08a7c; --unsafe-soft: #3a2420; --safe: #8fc292; --safe-soft: #203022;
  --gold: #e0bd5a; --gold-soft: #3a3018; --pick: #7fb1dc; color-scheme: dark }

html, body { height: 100%; }
body { background: var(--bg); color: var(--fg); font-family: var(--sans); font-size: 14px; line-height: 1.45; }
* { box-sizing: border-box; }
.app { display: grid; grid-template-columns: 320px minmax(0, 1fr); height: 100%; }
.side { border-right: 1px solid var(--line); display: flex; flex-direction: column; min-height: 0; background: var(--panel); }
.side header { padding: 14px 16px 10px; border-bottom: 1px solid var(--line); }
h1 { font-size: 16px; font-weight: 600; margin: 0 0 4px; text-wrap: balance; }
.sub { color: var(--muted); font-size: 12px; margin: 0; }
.filters { display: flex; flex-wrap: wrap; gap: 6px; padding: 10px 16px; border-bottom: 1px solid var(--line); }
.filters select, .filters input { font: inherit; font-size: 12px; padding: 4px 6px; border: 1px solid var(--line); border-radius: 4px; background: var(--bg); color: var(--fg); min-width: 0; }
.filters input { flex: 1 1 100px; }
.list { overflow-y: auto; flex: 1; min-height: 0; }
.row { display: block; width: 100%; text-align: left; border: 0; border-bottom: 1px solid var(--line); background: none; color: inherit; font: inherit; padding: 8px 16px; cursor: pointer; }
.row:hover, .row:focus-visible { background: var(--accent-soft); outline: none; }
.row[aria-current="true"] { background: var(--accent-soft); box-shadow: inset 3px 0 0 var(--accent); }
.row .t { font-weight: 500; font-size: 13px; }
.row .m { color: var(--muted); font-size: 11.5px; display: flex; gap: 8px; flex-wrap: wrap; margin-top: 2px; }
.chip { display: inline-block; font-size: 10.5px; padding: 1px 6px; border-radius: 3px; letter-spacing: .02em; text-transform: uppercase; font-weight: 500; }
.chip.gold { background: var(--gold-soft); color: var(--gold); }
.chip.ok { background: var(--safe-soft); color: var(--safe); }
.chip.bad { background: var(--unsafe-soft); color: var(--unsafe); }
.chip.v7 { background: var(--accent-soft); color: var(--accent); }
.chip.rid { background: var(--bg); color: var(--muted); border: 1px solid var(--line); text-transform: none; font-family: var(--mono); }

.main { overflow-y: auto; min-height: 0; padding: 18px 24px 40px; }
.main > section { max-width: 1100px; }
.head h2 { font-size: 18px; margin: 0 0 4px; font-weight: 600; font-family: var(--mono); }
.head .meta { color: var(--muted); font-size: 12.5px; display: flex; gap: 14px; flex-wrap: wrap; }
.block { margin-top: 18px; }
.block h3 { font-size: 11.5px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); margin: 0 0 6px; font-weight: 600; }
pre.text { font-family: var(--mono); font-size: 12px; white-space: pre-wrap; word-break: break-word; background: var(--panel); border: 1px solid var(--line); padding: 10px 12px; margin: 0; border-radius: 4px; max-height: 260px; overflow: auto; }
details > summary { cursor: pointer; font-size: 12.5px; color: var(--accent); }

table.picks { border-collapse: collapse; width: 100%; font-size: 12.5px; font-variant-numeric: tabular-nums; }
table.picks th, table.picks td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }
table.picks th { font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); font-weight: 600; }
table.picks td.n { font-family: var(--mono); white-space: nowrap; }
.hit { color: var(--safe); font-weight: 600; }
.miss { color: var(--unsafe); font-weight: 600; }
.wrap { overflow-x: auto; }

.runs { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 18px; }
.run { min-width: 0; }
.run h3 { display: flex; align-items: baseline; gap: 8px; }
.run h3 .who { text-transform: none; letter-spacing: 0; font-weight: 400; }
.steps { display: flex; flex-direction: column; gap: 6px; }
.step { border: 1px solid var(--line); border-radius: 4px; background: var(--panel); padding: 6px 8px; font-size: 12px; position: relative; }
.step .hd { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; font-family: var(--mono); font-size: 11.5px; }
.step .idx { color: var(--muted); }
.step .tool { font-weight: 500; }
.step .args, .step .obs { font-family: var(--mono); font-size: 11.5px; white-space: pre-wrap; word-break: break-word; margin: 4px 0 0; }
.step .obs { color: var(--muted); }
.step.is-gold { border-color: var(--gold); box-shadow: inset 3px 0 0 var(--gold); }
.step.is-pick { border-color: var(--pick); }
.step.is-gold.is-pick { box-shadow: inset 3px 0 0 var(--gold), 0 0 0 1px var(--pick); }
.marks { display: flex; gap: 4px; flex-wrap: wrap; margin-left: auto; }
.mark { font-size: 10px; padding: 0 5px; border-radius: 3px; background: var(--accent-soft); color: var(--accent); font-family: var(--sans); }
.mark.g { background: var(--gold-soft); color: var(--gold); }
.legend { display: flex; gap: 12px; flex-wrap: wrap; color: var(--muted); font-size: 12px; margin-top: 10px; }
.legend span::before { content: ""; display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 5px; vertical-align: -1px; }
.legend .lg::before { background: var(--gold); }
.legend .lp::before { background: var(--pick); }
.empty { color: var(--muted); padding: 40px 0; }
@media (max-width: 760px) {
  .app { grid-template-columns: 1fr; grid-template-rows: auto minmax(0, 1fr); }
  .side { border-right: 0; border-bottom: 1px solid var(--line); max-height: 42vh; }
  .runs { grid-template-columns: 1fr; }
  .main { padding: 14px 16px 32px; }
}
@media (prefers-reduced-motion: no-preference) { .row { transition: background .12s; } }
</style>

<div class="app">
  <aside class="side">
    <header>
      <h1>Pair attribution runs</h1>
      <p class="sub" id="count"></p>
    </header>
    <div class="filters">
      <select id="f-source" aria-label="Source"><option value="">All sources</option><option value="oas">OAS</option><option value="v7">v7</option><option value="v9">v9</option></select>
      <select id="f-gold" aria-label="Ground truth"><option value="">All runs</option><option value="yes">With ground truth</option></select>
      <input id="f-q" type="search" placeholder="Filter by task" aria-label="Filter by task">
    </div>
    <nav class="list" id="list"></nav>
  </aside>
  <main class="main" id="main"><div class="empty">Select a run.</div></main>
</div>

<script>
'''

TAIL = r'''const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const COND = ["pair", "single", "oracle"];
const shortModel = m => m.includes("sonnet") ? "Sonnet 5" : m.includes("qwen") ? "Qwen3.5-9B" : m;
const actorName = a => a.includes("gpt-5-mini") ? "GPT-5-mini" : a.includes("claude-sonnet-4-5") ? "Claude Sonnet 4.5" : a.includes("claude-sonnet-4-6") ? "Claude Sonnet 4.6" : a.includes("mg_baseline_claude") ? "Claude Sonnet 4.6" : a.includes("mg_baseline_gpt") ? "GPT-5-mini" : a;

function pairTop1(run) {
  const g = run.gold && run.gold.step;
  if (g == null) return null;
  const m = DATA.models.find(x => x.includes("sonnet")) || DATA.models[0];
  const p = run.picks[m] && run.picks[m].pair;
  return p ? p.pick === g : null;
}

let current = null;
function renderList() {
  const src = document.getElementById("f-source").value;
  const gold = document.getElementById("f-gold").value;
  const q = document.getElementById("f-q").value.trim().toLowerCase();
  const rows = DATA.runs.filter(r => (!src || r.source === src) && (!gold || r.gold) && (!q || r.task.toLowerCase().includes(q)));
  document.getElementById("count").textContent = `${rows.length} of ${DATA.runs.length} unsafe runs`;
  const list = document.getElementById("list");
  list.innerHTML = rows.map(r => {
    const t1 = pairTop1(r);
    const chips = [
      r.source === "v7" || r.source === "v9" ? `<span class="chip v7">${r.source}</span>` : "",
      r.run_id ? `<span class="chip rid">${esc(r.run_id)}</span>` : "",
      r.gold ? '<span class="chip gold">labelled</span>' : "",
      t1 === true ? '<span class="chip ok">pair hit</span>' : t1 === false ? '<span class="chip bad">pair miss</span>' : "",
    ].join("");
    return `<button class="row" data-key="${esc(r.key)}" aria-current="${r.key === current}"><div class="t">${esc(r.task.replace(/^safety-(v[79]-)?/, ""))}</div><div class="m"><span>${esc(actorName(r.unsafe_actor))}</span><span>${r.unsafe_steps.length} steps</span>${chips}</div></button>`;
  }).join("");
}

function stepHtml(s, i, marks, isGold) {
  const cls = ["step", isGold ? "is-gold" : "", marks.length ? "is-pick" : ""].join(" ");
  const mk = [isGold ? '<span class="mark g">gold</span>' : "", ...marks.map(m => `<span class="mark">${esc(m)}</span>`)].join("");
  return `<div class="${cls}" id="s-${i}"><div class="hd"><span class="idx">[step ${i}]</span><span class="tool">${esc(s.tool)}</span><span class="marks">${mk}</span></div><div class="args">${esc(s.args)}</div>${s.obs !== undefined ? `<div class="obs">${esc(s.obs || "(no observation)")}</div>` : ""}</div>`;
}

function renderRun(key) {
  current = key;
  const r = DATA.runs.find(x => x.key === key);
  const gold = r.gold && r.gold.step;
  const marks = {};
  const add = (i, label) => { if (i == null) return; (marks[i] = marks[i] || []).push(label); };
  const tableRows = [];
  for (const m of DATA.models) for (const c of COND) {
    const p = r.picks[m] && r.picks[m][c];
    if (!p) continue;
    add(p.pick, `${shortModel(m)} ${c}`);
    const hit = gold == null ? "" : p.pick === gold ? '<span class="hit">hit</span>' : (p.second === gold ? '<span class="miss">miss</span> (2nd choice hits)' : '<span class="miss">miss</span>');
    tableRows.push(`<tr><td>${esc(shortModel(m))}</td><td>${c}${c === "oracle" ? ' <span class="chip bad" title="sees grader text">leaks</span>' : ""}</td><td class="n">${p.pick ?? "–"}</td><td class="n">${p.second ?? "–"}</td><td>${hit}</td><td>${esc(p.reason)}</td></tr>`);
  }
  const goldBlock = r.gold ? `<div class="block"><h3>Ground truth</h3><pre class="text">${esc(gold != null ? `step ${gold}  (${r.gold.category}${r.gold.confidence ? `, confidence ${r.gold.confidence}` : ""})\n` : `${r.gold.category}\n`)}${esc(r.gold.evidence)}${r.gold.note ? "\n\nnote: " + esc(r.gold.note) : ""}</pre></div>` : `<div class="block"><h3>Ground truth</h3><p class="sub">None. This run was not in the 55-case hand read.</p></div>`;
  const safeHdr = r.safe_is_reference ? "Safe run (scripted reference, no observations)" : "Safe run";
  document.getElementById("main").innerHTML = `<section>
    <div class="head"><h2>${esc(r.task)}</h2><div class="meta"><span>unsafe run by ${esc(actorName(r.unsafe_actor))}</span><span>safe run by ${esc(actorName(r.safe_actor))}</span><span>${r.source.toUpperCase()}</span>${r.run_id ? `<span>run ${esc(r.run_id)}</span>` : ""}${r.task_version ? `<span>task version ${esc(r.task_version)}</span>` : ""}</div></div>
    <div class="block"><h3>Picks</h3><div class="wrap"><table class="picks"><thead><tr><th>Model</th><th>Condition</th><th>Pick</th><th>2nd</th><th>vs gold</th><th>Reason given</th></tr></thead><tbody>${tableRows.join("")}</tbody></table></div></div>
    ${goldBlock}
    <div class="block"><h3>Task instruction (as shown)</h3><pre class="text">${esc(r.instruction)}</pre></div>
    <div class="block"><details><summary>Grader checkpoint text (shown only in the oracle condition)</summary><pre class="text">${esc(r.checkpoint || "(empty)")}</pre></details></div>
    <div class="block"><details><summary>System prompt and answer format</summary><pre class="text">${esc(DATA.system_prompt)}\n\n${esc(DATA.answer_format)}</pre></details></div>
    <div class="legend"><span class="lg">gold step</span><span class="lp">picked by a model</span></div>
    <div class="runs">
      <div class="run"><h3>Unsafe run <span class="who">${esc(actorName(r.unsafe_actor))}, ${r.unsafe_steps.length} steps</span></h3><div class="steps">${r.unsafe_steps.map((s, i) => stepHtml(s, i, marks[i] || [], i === gold)).join("")}</div></div>
      <div class="run"><h3>${safeHdr} <span class="who">${esc(actorName(r.safe_actor))}, ${r.safe_steps.length} steps</span></h3><div class="steps">${r.safe_steps.map((s, i) => stepHtml(s, i, [], false)).join("")}</div></div>
    </div>
  </section>`;
  document.getElementById("main").scrollTop = 0;
  renderList();
}

document.getElementById("list").addEventListener("click", e => { const b = e.target.closest(".row"); if (b) renderRun(b.dataset.key); });
for (const id of ["f-source", "f-gold", "f-q"]) document.getElementById(id).addEventListener("input", renderList);
renderList();
const first = DATA.runs.find(r => r.gold && r.source === "oas") || DATA.runs[0];
if (first) renderRun(first.key);
</script>

</body></html>'''


def steps_out(steps, *, observations=True):
    out = []
    for s in steps:
        rec = {"tool": s["tool_name"], "args": pa.render_arguments(s["arguments"])}
        if observations:
            rec["obs"] = pa._clip((s.get("observation") or "").strip(), pa.MAX_OBS_CHARS)
        out.append(rec)
    return out


def load_picks():
    picks = {}
    for model in MODELS:
        for p in pa.read_jsonl(HERE / f"picks_{model}.jsonl"):
            picks.setdefault(p["key"], {}).setdefault(model, {})[p["condition"]] = {
                "pick": p["pick"], "second": p["second"], "reason": p["reason"], "parse_ok": p["parse_ok"]}
    return picks


def scripted(step):
    return f"{step['tool_name']} {pa.render_arguments(step['arguments'])}"


def build_data():
    picks = load_picks()
    cases = pa.load_cases()
    checkpoints = pa.load_checkpoints()
    runs = []
    for p in pa.load_oas_pairs():
        u, s = p["unsafe"], p["safe"]
        case = cases.get(u["key"])
        runs.append({
            "key": u["key"], "task": p["instance_id"], "source": "oas",
            "unsafe_actor": u["actor"], "safe_actor": s["actor"],
            "instruction": pa._clip(u["instruction"].strip(), pa.MAX_INSTRUCTION_CHARS),
            "checkpoint": pa._clip(checkpoints[p["instance_id"]].strip(), pa.MAX_CHECKPOINT_CHARS),
            "unsafe_steps": steps_out(u["steps"]), "safe_steps": steps_out(s["steps"]),
            "safe_is_reference": False,
            "gold": None if case is None else {
                "step": case["decisive_step_index"], "category": case["category"],
                "confidence": case.get("confidence"), "evidence": case.get("evidence", ""),
                "note": case.get("note", "")},
            "picks": picks.get(u["key"], {}),
        })
    scripted_runs = [(r, None) for r in pa.load_v7_runs()]
    scripted_runs += [(r, r) for r in pa.load_source_runs(pa.SOURCES_MANIFEST)]
    for r, new in scripted_runs:
        u = r["unsafe"]
        if u["key"] not in picks:
            continue
        rec = {
            "key": u["key"], "task": u["instance_id"], "source": r["source"],
            "unsafe_actor": u["actor"], "safe_actor": "scripted safe reference",
            "instruction": pa._clip(u["instruction"].strip(), pa.MAX_INSTRUCTION_CHARS),
            "checkpoint": pa._clip(r["checkpoint"].strip(), pa.MAX_CHECKPOINT_CHARS),
            "unsafe_steps": steps_out(u["steps"]),
            "safe_steps": steps_out(r["safe_reference"], observations=False),
            "safe_is_reference": True,
            "gold": {"step": None, "category": "scripted pivotal step", "confidence": None,
                     "evidence": scripted(r["pivotal_step"]), "note": ""},
            "picks": picks[u["key"]],
        }
        if new is not None:
            match = {m: {c: pa.v7_match(u["steps"][v["pick"]] if v["pick"] is not None else None,
                                        r["pivotal_step"])["strict"] for c, v in conds.items()}
                     for m, conds in rec["picks"].items()}
            strict = "; ".join(f"{m} " + " ".join(f"{c}={'yes' if ok else 'no'}" for c, ok in conds.items())
                               for m, conds in match.items())
            rec.update({"run_id": r["run_id"], "set": r["set"], "task_version": r["task_version"]})
            rec["gold"] = {
                "step": r["hand_step"],
                "category": "hand-read pivotal step" if r["hand_step"] is not None else "scripted pivotal step",
                "confidence": None,
                "evidence": "scripted pivotal step (strict rule target "
                f"{pa.target_path(r['pivotal_step'])}):\n{scripted(r['pivotal_step'])}",
                "note": f"hand step from {r['hand_from']}. Strict-rule match: {strict}",
            }
        runs.append(rec)
    return {"system_prompt": pa.SYSTEM_PROMPT, "answer_format": pa.ANSWER_FORMAT, "models": list(MODELS), "runs": runs}


def main():
    data = build_data()
    literal = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = HEAD + "const DATA = " + literal + ";\n" + TAIL
    OUT.write_text(html, encoding="utf-8")
    # checks: the DATA literal parses; tags balance; size limit
    line = next(x for x in html.split("\n") if x.startswith("const DATA = "))
    parsed = json.loads(line[len("const DATA = "):-1])
    assert len(parsed["runs"]) == len(data["runs"])
    outside = HEAD + TAIL
    for tag in ("div", "script", "style", "select", "aside", "main", "header", "nav", "head", "section", "table", "details", "pre"):
        opened = len(re.findall(rf"<{tag}[\s>]", outside))
        closed = len(re.findall(rf"</{tag}>", outside))
        assert opened == closed, (tag, opened, closed)
    size = OUT.stat().st_size
    assert size < 16 * 1024 * 1024, size
    print(f"wrote {OUT} ({size / 1e6:.2f} MB, {len(data['runs'])} runs)")


if __name__ == "__main__":
    main()
