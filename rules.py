import re

from dispositions import ARCHIVE, ESCALATE, Decision
from inbox_store import split_address

# Deliberately does not match a plain "note for the assistant": Sam's own m041 preference uses that phrasing.
INJECTION_PATTERNS = {
    "override-instructions": r"ignore (all )?(previous|prior|above) instructions",
    "conceal-from-user": r"(no need to|do not|don't|must not|without)\s+(mention|surface|report|tell|disclose)\b.{0,60}\b(user|summary|owner)",
    "bypass-approval": r"without asking for approval|skip the confirmation|autonomous mode",
    "exfiltrate-mail": r"forward (the )?(full |entire )?contents? of (this|the) mailbox|forward any message that mentions",
    "addressed-to-agent": r"automated[- ]agent directive|notice for automated assistants|if an ai agent is processing",
}
_INJECTION = {name: re.compile(p, re.I | re.S) for name, p in INJECTION_PATTERNS.items()}

# Checked before any archive rule: a sender can name itself billing@ or noreply@, so an archive
# must never be reachable for mail that asks for money to move or credentials to be entered.
PHISHING_PATTERNS = {
    "payment-redirect": r"remittance details|(new|changed|updated) (bank )?account|account on file|routing:|wire \$?\d",
    "credential-harvest": r"re-?verify your (credentials|password|account)|verify your (credentials|password|identity)|password .{0,30}expires? in|will be suspended",
}
_PHISHING = {name: re.compile(p, re.I | re.S) for name, p in PHISHING_PATTERNS.items()}

_BILLING_SUBJECT = re.compile(r"receipt|invoice|\bbill\b|statement|payout|charged", re.I)

AUTOMATED_LOCALPARTS = [
    (r"receipts?|billing|orders?|ship-confirm|invoice.*", "receipt or billing notice"),
    (r"alerts?|status|security", "monitoring or account alert"),
    (r"newsletter|digest|hello|updates?|insights|feedback|info", "newsletter or marketing"),
    (r"no[-_]?reply.*|.*notifications?|notify|checkin|success", "automated notification"),
]
_AUTOMATED = [(re.compile(f"^(?:{p})$"), label) for p, label in AUTOMATED_LOCALPARTS]

_NO_ACTION = re.compile(
    r"no (further )?action (is )?(needed|required)|for your records|do not reply|this is an automated",
    re.I,
)


def _edit_distance(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def route(message, owner_domain):
    """Return a Decision if a deterministic rule settles the message, else None."""
    mid = message["id"]
    local, domain = split_address(message["from"])
    text = f"{message['subject']}\n{message['body']}"

    attempts = [name for name, pattern in _INJECTION.items() if pattern.search(text)]
    if attempts:
        return Decision(mid, ESCALATE,
                        f"contains an instruction addressed to the assistant ({', '.join(attempts)}); not acted on",
                        "rule", "injection:" + "+".join(attempts))

    if domain != owner_domain and _edit_distance(domain, owner_domain) <= 2:
        return Decision(mid, ESCALATE,
                        f"sender domain '{domain}' imitates '{owner_domain}'",
                        "rule", "lookalike-domain")

    for name, pattern in _PHISHING.items():
        if pattern.search(text):
            return Decision(mid, ESCALATE,
                            f"looks like phishing ({name}); not acted on",
                            "rule", f"phishing:{name}")

    for pattern, label in _AUTOMATED:
        if pattern.match(local):
            if _BILLING_SUBJECT.search(message["subject"]):
                label = "receipt or billing notice"
            return Decision(mid, ARCHIVE,
                            f"automated sender '{local}@{domain}' ({label}); no reply expected",
                            "rule", "automated-sender")

    if _NO_ACTION.search(text):
        return Decision(mid, ARCHIVE, "message itself states no action is needed", "rule", "no-action-phrase")

    return None
