import json
from collections import Counter
from pathlib import Path

INBOX_PATH = Path(__file__).parent / "inbox.json"


def load_inbox(path=INBOX_PATH):
    with open(path) as f:
        messages = json.load(f)
    return sorted(messages, key=lambda m: m["timestamp"])


def split_address(address):
    if "<" in address and ">" in address:
        address = address[address.index("<") + 1 : address.index(">")]
    local, _, domain = address.strip().lower().partition("@")
    return local, domain


def owner_address(messages):
    return Counter(m["to"].lower() for m in messages).most_common(1)[0][0]


def owner_domain(messages):
    return split_address(owner_address(messages))[1]
