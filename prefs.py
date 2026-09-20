import json
import re
import time
from pathlib import Path

from inbox_store import split_address

PREFS_PATH = Path(__file__).parent / "prefs.json"
TYPES = ("no_meetings_before", "cc_rule")
_CLOCK = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


class PreferenceRejected(Exception):
    pass


def load():
    if PREFS_PATH.exists():
        return json.loads(PREFS_PATH.read_text())
    return {"preferences": [], "rejected": []}


def save(data):
    PREFS_PATH.write_text(json.dumps(data, indent=2) + "\n")


def reset():
    PREFS_PATH.unlink(missing_ok=True)


def _address(message):
    local, domain = split_address(message["from"])
    return f"{local}@{domain}"


def validate(pref_type, params, message, owner_email):
    """Accept only the fixed schema, and only from a sender allowed to state it."""
    sender = _address(message)
    if pref_type == "no_meetings_before":
        if sender != owner_email:
            raise PreferenceRejected("only the owner can set a scheduling preference")
        clock = _CLOCK.match(str(params.get("time", "")))
        if not clock:
            raise PreferenceRejected(f"invalid time {params.get('time')!r}")
        return {"time": f"{int(clock.group(1)):02d}:{clock.group(2)}"}
    if pref_type == "cc_rule":
        cc = str(params.get("cc", "")).strip().lower()
        org = str(params.get("sender_org", "")).strip()
        if len(_norm(org)) < 4 or len(org) > 60:
            raise PreferenceRejected(f"invalid organisation name {org!r}")
        if cc.split("@")[-1] != owner_email.split("@")[-1]:
            raise PreferenceRejected("the copied address must be inside the owner's own domain")
        if sender not in (owner_email, cc):
            raise PreferenceRejected("a colleague may only ask to be copied themselves")
        return {"sender_org": org, "cc": cc}
    raise PreferenceRejected(f"unsupported preference type {pref_type!r}")


def add(data, pref_type, params, message):
    for existing in data["preferences"]:
        if existing["type"] == pref_type and existing["params"] == params:
            return existing
    pref = {"id": f"pref-{len(data['preferences']) + 1}", "type": pref_type, "params": params,
            "source_message": message["id"], "stated_by": message["from"],
            "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    data["preferences"].append(pref)
    return pref


def _norm(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


def to_minutes(clock):
    hours, minutes = clock.split(":")
    return int(hours) * 60 + int(minutes)


def pretty(clock):
    hours, minutes = (int(x) for x in clock.split(":"))
    return f"{hours % 12 or 12}:{minutes:02d}{'am' if hours < 12 else 'pm'}"


def describe(pref):
    if pref["type"] == "no_meetings_before":
        return f"no meetings before {pretty(pref['params']['time'])}"
    return f"CC {pref['params']['cc']} on mail from {pref['params']['sender_org']}"


def meeting_cutoff(data):
    """The strictest no-meetings-before preference as (minutes, preference), or (None, None)."""
    found = [(to_minutes(p["params"]["time"]), p) for p in data["preferences"] if p["type"] == "no_meetings_before"]
    return max(found, key=lambda pair: pair[0]) if found else (None, None)


def cc_for(message, data):
    domain = _norm(split_address(message["from"])[1])
    return [p["params"]["cc"] for p in data["preferences"]
            if p["type"] == "cc_rule" and _norm(p["params"]["sender_org"]) in domain]
