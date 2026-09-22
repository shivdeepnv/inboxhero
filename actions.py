"""The only module in the system that can cause an irreversible effect.

send_message and delete_message both call gate.require_approval before touching anything.
No model, agent or rule imports this module; only the R3 runner does.
"""
import json
import time
from pathlib import Path

import gate
import tracelog as trace
from inbox_store import DELETED_PATH

OUTBOX = Path(__file__).parent / "outbox"

ACTIONS = [
    ("reversible", "draft", "saved in drafts.json; can be rewritten or removed"),
    ("reversible", "label", "a note recorded beside the message; can be changed"),
    ("reversible", "archive", "a disposition in decisions.json; nothing is moved or removed"),
    ("reversible", "defer", "a disposition in decisions.json; can be changed"),
    ("irreversible", "send", "cannot be unsent; gated by per-action approval and by --dry-run"),
    ("irreversible", "delete", "the mock store has no trash; gated, and no capability proposes it on its own"),
]


def _log(action, message_id, proposed, approval, outcome):
    trace.log("R3", "gate", action=action, message_id=message_id, proposed=proposed,
              decision=approval.decision, outcome=outcome)
    print(f"  decision: {approval.decision}; {outcome}")


def send_message(draft, owner_email, cc, dry_run=False):
    mid = draft["message_id"]
    print(f"\nPROPOSED SEND (irreversible), replying to {mid}")
    print(f"  From:    {owner_email}\n  To:      {draft['to']}\n  CC:      {', '.join(cc) or '(none)'}")
    print(f"  Subject: {draft['subject']}\n  Cited:   {draft.get('cited', [])}\n---\n{draft['body']}\n---")

    approval = gate.require_approval("Send this message?", dry_run)
    if approval.granted:
        OUTBOX.mkdir(exist_ok=True)
        record = {"message_id": mid, "from": owner_email, "to": draft["to"], "cc": cc,
                  "subject": draft["subject"], "body": draft["body"], "cited": draft.get("cited", []),
                  "approved_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        (OUTBOX / f"{mid}.json").write_text(json.dumps(record, indent=2) + "\n")
        outcome = f"written to outbox/{mid}.json"
    else:
        outcome = "nothing written"
    _log("send", mid, {"to": draft["to"], "cc": cc, "subject": draft["subject"]}, approval, outcome)
    return approval.granted


def delete_message(message, dry_run=False):
    mid = message["id"]
    print(f"\nPROPOSED DELETE (irreversible): {mid} from {message['from']}: {message['subject']!r}")
    approval = gate.require_approval("Permanently delete this message?", dry_run)
    if approval.granted:
        with open(DELETED_PATH, "a") as f:
            f.write(json.dumps({"message_id": mid, "deleted_at": time.strftime("%Y-%m-%dT%H:%M:%S")}) + "\n")
        outcome = f"recorded in {DELETED_PATH.name}; the message no longer loads"
    else:
        outcome = "nothing deleted"
    _log("delete", mid, {"subject": message["subject"]}, approval, outcome)
    return approval.granted
