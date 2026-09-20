import json
from collections import Counter
from pathlib import Path

import rules
import tracelog as trace
from inbox_store import load_inbox, owner_address, owner_domain

DECISIONS_PATH = Path(__file__).parent / "decisions.json"


def _print_decisions(decisions, by_id):
    for d in decisions:
        m = by_id[d.message_id]
        print(f"  {d.message_id}  {d.disposition:<9} [{d.method}] {m['from']:<36} {m['subject'][:40]}")
        print(f"        reason: {d.reason}")


def run_r1(rules_only=False):
    messages = load_inbox()
    by_id = {m["id"]: m for m in messages}
    owner = owner_domain(messages)
    trace.clear_cap("R1")

    decisions = {}
    remaining = []
    for m in messages:
        d = rules.route(m, owner)
        if d:
            decisions[m["id"]] = d
            trace.log("R1", "decision", message_id=d.message_id, disposition=d.disposition,
                      reason=d.reason, method=d.method, rule=d.rule)
        else:
            remaining.append(m)

    print(f"owner domain: {owner}\n")

    if rules_only:
        print("RULE-HANDLED (no model call)")
        _print_decisions(decisions.values(), by_id)
        print(f"\nrule-handled: {len(decisions)} of {len(messages)}")
        print(f"left for the model: {len(remaining)}")
        for m in remaining:
            print(f"  {m['id']}  {m['from']:<38} {m['subject'][:44]}")
        return

    print(f"rule stage: {len(decisions)} of {len(messages)} settled; sending {len(remaining)} to the model\n")
    from llm_triage import triage_remaining
    decisions.update(triage_remaining(remaining, messages, owner_address(messages)))

    ordered = [decisions[m["id"]] for m in messages if m["id"] in decisions]
    print("\nALL DISPOSITIONS")
    _print_decisions(ordered, by_id)

    methods = Counter(d.method for d in ordered)
    by_disposition = Counter(d.disposition for d in ordered)
    undecided = [m["id"] for m in messages if m["id"] not in decisions]

    print(f"\nmessages: {len(messages)}")
    print(f"settled by rules, no model call: {methods['rule']}")
    print(f"settled by the model: {methods['llm']}")
    print(f"model failed, escalated for the owner: {methods['fallback']}")
    print("by disposition: " + ", ".join(f"{k}={v}" for k, v in sorted(by_disposition.items())))
    print(f"undecided: {len(undecided)}")

    summary = {"messages_processed": len(messages), "rule_handled": methods["rule"],
               "model_handled": methods["llm"], "fallback": methods["fallback"],
               "undecided": len(undecided), "by_disposition": dict(by_disposition)}
    DECISIONS_PATH.write_text(json.dumps(
        {"summary": summary, "decisions": [vars(d) for d in ordered]}, indent=2) + "\n")
    print(f"wrote {DECISIONS_PATH.name}")
