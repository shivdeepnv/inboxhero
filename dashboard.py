import html
import json
from pathlib import Path

from commitments import run_extraction
from grounded import DRAFTS_PATH
from hostile import ATTACK_DESCRIPTIONS, attempts_for, find_hostile
from inbox_store import load_inbox
from prefs import pretty as pretty_time

DECISIONS_PATH = Path(__file__).parent / "decisions.json"
OUTBOX = Path(__file__).parent / "outbox"
DASHBOARD_JSON = Path(__file__).parent / "dashboard.json"
DASHBOARD_HTML = Path(__file__).parent / "dashboard.html"

MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def pretty_date(iso):
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{MONTHS[m]} {d}, {y}"


def _pending(decisions, drafts):
    hostile_ids = {d["message_id"] for d in find_hostile(decisions)}
    rows = []
    for mid, draft in sorted(drafts.items()):
        if (OUTBOX / f"{mid}.json").exists():
            continue
        rows.append({"message_id": mid, "action": f"send reply to {draft['to']}: {draft['subject']!r}",
                    "why": "sending is irreversible and requires approval (R3)", "cited": draft.get("cited", [])})
    for d in decisions:
        mid = d["message_id"]
        if d["disposition"] == "escalate" and d["method"] == "llm" and mid not in hostile_ids and mid not in drafts:
            rows.append({"message_id": mid, "action": "owner decision needed; no draft can be grounded",
                        "why": d["reason"], "cited": [mid]})
    return rows


def _flagged(decisions, by_id):
    rows = []
    for d in find_hostile(decisions):
        mid = d["message_id"]
        m = by_id.get(mid)
        attempts = [ATTACK_DESCRIPTIONS.get(n, n) for n in attempts_for(d["rule"])]
        rows.append({"message_id": mid, "from": m["from"] if m else "?",
                    "subject": m["subject"] if m else "?", "attempted": attempts,
                    "outcome": "not complied with; flagged and left in place; not deleted"})
    return rows


def build(refresh_commitments=True):
    messages = load_inbox()
    by_id = {m["id"]: m for m in messages}
    if not DECISIONS_PATH.exists():
        raise SystemExit("decisions.json not found. Run: python demo.py --cap R1")
    decisions = json.loads(DECISIONS_PATH.read_text())["decisions"]
    drafts = json.loads(DRAFTS_PATH.read_text()) if DRAFTS_PATH.exists() else {}

    if refresh_commitments:
        commitments = run_extraction(messages, decisions)
    else:
        commitments = json.loads(Path("commitments.json").read_text())

    data = {"pending": _pending(decisions, drafts), "flagged": _flagged(decisions, by_id),
            "commitments": commitments}
    DASHBOARD_JSON.write_text(json.dumps(data, indent=2) + "\n")
    return data


def _esc(text):
    return html.escape(str(text))


def _render_pending(rows):
    if not rows:
        return "<p class='empty'>Nothing pending.</p>"
    items = "".join(f"""
      <li>
        <strong>{_esc(r['message_id'])}</strong>: {_esc(r['action'])}
        <div class="why">needs a human because: {_esc(r['why'])}</div>
        <div class="cited">cites: {', '.join(_esc(c) for c in r['cited'])}</div>
      </li>""" for r in rows)
    return f"<ul class='pending'>{items}\n    </ul>"


def _render_flagged(rows):
    if not rows:
        return "<p class='empty'>Nothing flagged.</p>"
    items = "".join(f"""
      <li>
        <strong>{_esc(r['message_id'])}</strong> from {_esc(r['from'])}: {_esc(r['subject'])}
        <ul class="attempts">{''.join(f"<li>attempted: {_esc(a)}</li>" for a in r['attempted'])}</ul>
        <div class="outcome">{_esc(r['outcome'])}</div>
      </li>""" for r in rows)
    return f"<ul class='flagged'>{items}\n    </ul>"


def _render_commitments(rows):
    if not rows:
        return "<p class='empty'>No commitments extracted.</p>"
    dated = sorted((c for c in rows if c["date"]), key=lambda c: (c["date"], c["time"] or ""))
    undated = [c for c in rows if not c["date"]]
    items = ""
    for c in dated:
        when = pretty_date(c["date"]) + (f" at {pretty_time(c['time'])}" if c["time"] else "")
        conflict = (f"<div class='conflict'>CONFLICT: also booked for {', '.join(c['conflict_with'])} "
                   f"at this same time</div>" if c["conflict_with"] else "")
        items += f"""
      <li class="{'has-conflict' if c['conflict_with'] else ''}">
        <strong>{_esc(when)}</strong> &mdash; {_esc(c['what'])}
        <div class="cited">cited: {', '.join(_esc(i) for i in c['cited'])}</div>
        {conflict}
      </li>"""
    for c in undated:
        items += f"""
      <li>
        <strong>(no fixed date)</strong> &mdash; {_esc(c['what'])}
        <div class="cited">cited: {', '.join(_esc(i) for i in c['cited'])}</div>
      </li>"""
    return f"<ul class='commitments'>{items}\n    </ul>"


CSS = """
body { font-family: -apple-system, Helvetica, Arial, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; }
h1 { margin-bottom: 0; }
.generated { color: #666; font-size: 0.85rem; margin-top: 0; }
.pane { border: 1px solid #ddd; border-radius: 8px; padding: 1rem 1.5rem; margin: 1.5rem 0; }
.pane h2 { margin-top: 0; }
ul { list-style: none; padding-left: 0; }
li { padding: 0.6rem 0; border-bottom: 1px solid #eee; }
li:last-child { border-bottom: none; }
.why, .cited, .outcome { color: #555; font-size: 0.85rem; margin-top: 0.2rem; }
.attempts { margin: 0.3rem 0 0 1rem; }
.conflict { color: #b00020; font-weight: bold; margin-top: 0.3rem; }
li.has-conflict { background: #fff3f3; }
.empty { color: #888; font-style: italic; }
"""


def render_html(data, generated_note):
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>inboxHero dashboard</title><style>{CSS}</style></head>
<body>
  <h1>inboxHero dashboard</h1>
  <p class="generated">{_esc(generated_note)}</p>

  <div class="pane">
    <h2>Pending actions ({len(data['pending'])})</h2>
    {_render_pending(data['pending'])}
  </div>

  <div class="pane">
    <h2>Flagged ({len(data['flagged'])})</h2>
    {_render_flagged(data['flagged'])}
  </div>

  <div class="pane">
    <h2>Commitments ({len(data['commitments'])})</h2>
    {_render_commitments(data['commitments'])}
  </div>
</body></html>
"""


def run_r6(refresh_commitments=True):
    import time
    data = build(refresh_commitments)
    note = f"generated by python demo.py --cap R6, {time.strftime('%Y-%m-%d %H:%M:%S')}"
    DASHBOARD_HTML.write_text(render_html(data, note))

    print(f"\nPENDING ACTIONS: {len(data['pending'])}")
    for r in data["pending"]:
        print(f"  {r['message_id']}: {r['action']}\n      why: {r['why']}")

    print(f"\nFLAGGED: {len(data['flagged'])}")
    for r in data["flagged"]:
        print(f"  {r['message_id']} from {r['from']}: {', '.join(r['attempted'])}")

    print(f"\nCOMMITMENTS: {len(data['commitments'])}")
    for c in data["commitments"]:
        when = f"{c['date']} {c['time']}".strip() or "(no fixed date)"
        flag = f"  CONFLICT with {c['conflict_with']}" if c["conflict_with"] else ""
        print(f"  {c['id']} [{when}] {c['what']} -- cited {c['cited']}{flag}")

    print(f"\nwrote {DASHBOARD_JSON.name} and {DASHBOARD_HTML.name}")
