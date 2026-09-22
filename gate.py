import sys


class Approval:
    def __init__(self, granted, decision):
        self.granted = granted
        self.decision = decision


def require_approval(question, dry_run=False):
    """Ask the human. Anything other than an explicit yes at a terminal is a no."""
    if dry_run:
        return Approval(False, "dry-run")
    if not sys.stdin.isatty():
        return Approval(False, "denied: no interactive terminal")
    answer = input(f"{question} [y/N]: ").strip().lower()
    if answer in ("y", "yes"):
        return Approval(True, "approved")
    return Approval(False, "denied")
