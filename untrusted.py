import re

SECRET = re.compile(r"(?<=://)[^\s:@/]+:[^\s@/]+(?=@)")
REDACTED = "[REDACTED-CREDENTIAL]"


def redact(text):
    return SECRET.sub(REDACTED, text)


def sanitize(text):
    return re.sub(r"</\s*untrusted_email", "[/untrusted_email", text, flags=re.I)


def format_message(message, limit=1500):
    body = sanitize(redact(message["body"])[:limit])
    return (f"Id: {message['id']}\nFrom: {message['from']}\nTo: {message['to']}\n"
            f"Date: {message['timestamp']}\nSubject: {sanitize(message['subject'])}\n\n{body}")
