import tracelog as trace
from inbox_store import load_inbox, split_address


def run_x2(sender=None):
    if not sender:
        raise SystemExit("X2 needs --sender <email>. Example: python demo.py --cap X2 --sender priya@paperjet.io")
    target = sender.strip().lower()
    messages = load_inbox()
    matches = [m for m in messages if m["unread"]
              and "@".join(split_address(m["from"])) == target]

    trace.clear_cap("X2", sender=target)
    trace.log("X2", "lookup", sender=target, matched=[m["id"] for m in matches])

    print(f"UNREAD MAIL FROM {target}\n" + "=" * 60)
    if not matches:
        print("(none)")
    for m in matches:
        print(f"{m['id']}  {m['timestamp']}  {m['subject']}")
    print(f"\ntotal: {len(matches)}")
