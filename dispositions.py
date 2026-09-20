from dataclasses import dataclass
from typing import Optional

REPLY = "reply"
ARCHIVE = "archive"
DEFER = "defer"
DELEGATE = "delegate"
ESCALATE = "escalate"

DISPOSITIONS = {
    REPLY: "Sam owes a response. The system drafts one (grounded in the inbox) or leaves it for Sam.",
    ARCHIVE: "No action or response needed. Safe to close; nothing is deleted.",
    DEFER: "Holds a future commitment or deadline. Tracked for later, not answered now.",
    DELEGATE: "The action belongs to someone other than Sam. Sam only needs to pass it on.",
    ESCALATE: "Needs a human decision the system will not make alone: ambiguous asks, money, legal, phishing, or instructions aimed at the assistant.",
}


@dataclass
class Decision:
    message_id: str
    disposition: str
    reason: str
    method: str  # "rule" or "llm"
    rule: Optional[str] = None
