import json
from collections import Counter
from pathlib import Path

INBOX_PATH = Path(__file__).parent / "inbox.json"


DELETED_PATH = Path(__file__).parent / "deleted.jsonl"


def load_inbox(path=INBOX_PATH):
    with open(path) as f:
        messages = json.load(f)
    deleted = set()
    if DELETED_PATH.exists():
        deleted = {json.loads(line)["message_id"] for line in DELETED_PATH.read_text().splitlines() if line}
    return sorted((m for m in messages if m["id"] not in deleted), key=lambda m: m["timestamp"])


def split_address(address):
    if "<" in address and ">" in address:
        address = address[address.index("<") + 1 : address.index(">")]
    local, _, domain = address.strip().lower().partition("@")
    return local, domain


def owner_address(messages):
    return Counter(m["to"].lower() for m in messages).most_common(1)[0][0]


def owner_domain(messages):
    return split_address(owner_address(messages))[1]
