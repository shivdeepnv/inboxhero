import json
import time
from pathlib import Path

TRACE_PATH = Path(__file__).parent / "trace.jsonl"


def log(cap, event, **fields):
    record = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "cap": cap, "event": event, **fields}
    with open(TRACE_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")


def clear_cap(cap):
    if not TRACE_PATH.exists():
        return
    kept = [line for line in TRACE_PATH.read_text().splitlines() if json.loads(line).get("cap") != cap]
    TRACE_PATH.write_text("".join(line + "\n" for line in kept))
