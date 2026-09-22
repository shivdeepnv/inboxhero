import json
from pathlib import Path

import tracelog as trace
from crew_client import LLMFailure, ask, make_agent

DECISIONS_PATH = Path(__file__).parent / "decisions.json"


def _bucket(decisions):
    needs_you = [d for d in decisions if d["disposition"] in ("reply", "escalate")]
    can_wait = [d for d in decisions if d["disposition"] == "defer"]
    handled = [d for d in decisions if d["disposition"] in ("archive", "delegate")]
    return needs_you, can_wait, handled


def _bullets(rows, limit=8):
    return "\n".join(f"- {r['message_id']}: {r['reason']}" for r in rows[:limit]) or "(none)"


def _narrative(agent, needs_you, can_wait, handled, total):
    description = f"""Write a short daily digest paragraph (3-4 sentences, plain prose, no headers or markdown)
for an inbox owner, using only the counts and reasons below. Never invent any message content beyond what is listed.

Total messages processed: {total}

Archived or delegated automatically ({len(handled)}), representative reasons:
{_bullets(handled)}

Needs the owner ({len(needs_you)}):
{_bullets(needs_you)}

Can wait ({len(can_wait)}):
{_bullets(can_wait)}

Reply with plain text only."""
    try:
        return ask(agent, description, "A short paragraph.", lambda raw: raw.strip(), "X1", "digest")
    except LLMFailure as e:
        return f"(narrative unavailable: {e})"


def run_x1():
    if not DECISIONS_PATH.exists():
        raise SystemExit("decisions.json not found. Run: python demo.py --cap R1")
    decisions = json.loads(DECISIONS_PATH.read_text())["decisions"]
    needs_you, can_wait, handled = _bucket(decisions)
    trace.clear_cap("X1")

    agent = make_agent(
        role="Digest writer",
        goal="Summarize inbox triage results into a short daily digest.",
        backstory="You write a short factual digest paragraph from counts and reasons you're given. "
                 "You never invent message content.",
        max_tokens=200,
    )
    narrative = _narrative(agent, needs_you, can_wait, handled, len(decisions))
    trace.log("X1", "digest", total=len(decisions), needs_you=len(needs_you),
              can_wait=len(can_wait), handled=len(handled), narrative=narrative)

    print("DAILY DIGEST\n" + "=" * 60)
    print(narrative)
    print(f"\nNEEDS YOU ({len(needs_you)})")
    for d in needs_you:
        print(f"  {d['message_id']}: {d['reason']}")
    print(f"\nCAN WAIT ({len(can_wait)})")
    for d in can_wait:
        print(f"  {d['message_id']}: {d['reason']}")
    print(f"\nHANDLED AUTOMATICALLY ({len(handled)})")
    print(f"  archived or delegated without your attention; see decisions.json for the full list")
