import json

import actions
import prefs
import tracelog as trace
from grounded import DRAFTS_PATH
from inbox_store import load_inbox, owner_address


def run_r3(dry_run=False, delete=None):
    messages = load_inbox()
    by_id = {m["id"]: m for m in messages}
    owner = owner_address(messages)
    trace.clear_cap("R3")

    print("ACTION CLASSES")
    for kind, name, note in actions.ACTIONS:
        print(f"  {kind:<12} {name:<8} {note}")
    print(f"\nmode: {'DRY RUN, nothing will be written' if dry_run else 'approval required for every irreversible action'}")

    drafts = json.loads(DRAFTS_PATH.read_text()) if DRAFTS_PATH.exists() else {}
    if not drafts:
        raise SystemExit("no drafts found. Run: python demo.py --cap R2, then python demo.py --cap R4")

    prefs_data = prefs.load()
    sent = 0
    for mid in sorted(drafts):
        draft = drafts[mid]
        original = by_id.get(mid)
        cc = sorted(set(draft.get("cc", [])) | set(prefs.cc_for(original, prefs_data) if original else []))
        if actions.send_message(draft, owner, cc, dry_run):
            sent += 1

    if delete:
        if delete not in by_id:
            raise SystemExit(f"unknown message id: {delete}")
        actions.delete_message(by_id[delete], dry_run)

    print(f"\ndrafts proposed for sending: {len(drafts)}")
    print(f"approved and sent: {sent}")
    print(f"outbox/ writes: {sent}")
    if dry_run:
        print("dry run: nothing was written and nothing was sent")
