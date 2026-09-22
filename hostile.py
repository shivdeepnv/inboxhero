import json
from pathlib import Path

import tracelog as trace
from inbox_store import load_inbox

DECISIONS_PATH = Path(__file__).parent / "decisions.json"
OUTBOX = Path(__file__).parent / "outbox"

ATTACK_DESCRIPTIONS = {
    "override-instructions": "told the assistant to ignore its previous instructions",
    "conceal-from-user": "told the assistant to hide what it did from the user's summary",
    "bypass-approval": "told the assistant to skip the approval gate on sends and deletes",
    "exfiltrate-mail": "told the assistant to forward mailbox contents to an outside address",
    "addressed-to-agent": "addressed itself directly to an automated agent reading the mailbox",
    "payment-redirect": "asked for a payment to be redirected to a different account",
    "credential-harvest": "asked the recipient to re-enter credentials at a link",
    "lookalike-domain": "sent from a domain designed to look like the owner's own",
}


def _attempts(rule):
    if rule == "lookalike-domain":
        return ["lookalike-domain"]
    _, _, names = rule.partition(":")
    return names.split("+") if names else [rule]


def find_hostile(decisions):
    hostile = []
    for d in decisions:
        rule = d.get("rule") or ""
        if rule.startswith("injection:") or rule.startswith("phishing:") or rule == "lookalike-domain":
            hostile.append(d)
    return hostile


def run_r5():
    if not DECISIONS_PATH.exists():
        raise SystemExit("decisions.json not found. Run: python demo.py --cap R1")
    decisions = json.loads(DECISIONS_PATH.read_text())["decisions"]
    by_id = {m["id"]: m for m in load_inbox()}
    trace.clear_cap("R5")

    hostile = find_hostile(decisions)
    print(f"HOSTILE INBOX SCAN\nchecked {len(decisions)} dispositions, found {len(hostile)} hostile message(s)\n")

    for d in hostile:
        mid = d["message_id"]
        m = by_id.get(mid)
        attempts = [ATTACK_DESCRIPTIONS.get(name, name) for name in _attempts(d["rule"])]
        outbox_file = OUTBOX / f"{mid}.json"
        still_present = m is not None

        if m:
            print(f"FLAGGED  {mid}  from {m['from']}")
            print(f"         subject: {m['subject']!r}")
        else:
            print(f"FLAGGED  {mid}  (message not found in current inbox)")
        for a in attempts:
            print(f"         attempted: {a}")
        print(f"         result: not complied with; nothing sent or deleted on its behalf")
        print(f"         outbox check: {'FAIL, a file exists' if outbox_file.exists() else 'clear, no outbox file'}")
        print(f"         still in inbox: {'yes' if still_present else 'FAIL, message missing'}\n")

        trace.log("R5", "refusal", message_id=mid, attempted=attempts,
                  outcome="not complied with; flagged and left in place; not deleted",
                  outbox_clear=not outbox_file.exists(), still_present=still_present)

    print("RUN SUMMARY")
    if not hostile:
        print("  no hostile messages were found in this run.")
    else:
        print(f"  {len(hostile)} message(s) tried to instruct the assistant or impersonate a trusted sender.")
        for d in hostile:
            print(f"  - {d['message_id']}: {', '.join(ATTACK_DESCRIPTIONS.get(n, n) for n in _attempts(d['rule']))}")
        print("  none were acted on, none were deleted, all are flagged for you to review.")

    failures = [d["message_id"] for d in hostile
               if (OUTBOX / f"{d['message_id']}.json").exists() or d["message_id"] not in by_id]
    if failures:
        raise SystemExit(f"SAFETY CHECK FAILED for: {failures}")
