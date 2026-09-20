import math
import re
from collections import Counter

STOPWORDS = set("""
about above after again ahead also been before being could does doing done each else from have here
into just kind like made make more most much need only other over please really said same should some
such than thank thanks that their them then there these they this those very want were what when where
which while will with would your
""".split())


def _terms(text):
    return {w for w in re.findall(r"[a-z]+", text.lower()) if len(w) >= 4 and w not in STOPWORDS}


def thread_walk(message, all_messages):
    return [m for m in all_messages
            if m["thread_id"] == message["thread_id"] and m["timestamp"] < message["timestamp"]]


def keyword_search(message, all_messages, exclude_ids, k=3, min_shared=2):
    """Earlier messages from other threads sharing at least `min_shared` rare terms with `message`."""
    docs = {m["id"]: _terms(m["subject"] + " " + m["body"]) for m in all_messages}
    df = Counter(t for terms in docs.values() for t in terms)
    query = _terms(message["subject"] + " " + message["body"])
    scored = []
    for m in all_messages:
        if m["id"] == message["id"] or m["id"] in exclude_ids or m["timestamp"] >= message["timestamp"]:
            continue
        shared = query & docs[m["id"]]
        if len(shared) >= min_shared:
            scored.append((sum(math.log(len(all_messages) / df[t]) for t in shared), m))
    scored.sort(key=lambda pair: -pair[0])
    return [m for _, m in scored[:k]]


def retrieve(message, all_messages):
    """Thread-walk first, then keyword search across other threads. Returns [(message, via)]."""
    walked = thread_walk(message, all_messages)
    found = keyword_search(message, all_messages, {m["id"] for m in walked})
    return [(m, "thread-walk") for m in walked] + [(m, "keyword") for m in found]
