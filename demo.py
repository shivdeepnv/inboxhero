import argparse

from grounded import run_r2
from triage import run_r1

CAPABILITIES = {"R1": run_r1, "R2": run_r2}


def main():
    parser = argparse.ArgumentParser(description="inboxHero capability runner")
    parser.add_argument("--cap", help="capability id, e.g. R1")
    parser.add_argument("--all", action="store_true", help="run every capability in order")
    parser.add_argument("--rules-only", action="store_true", help="R1: stop after the rule stage")
    parser.add_argument("--msg", help="R2: a single message id to draft a reply for")
    args = parser.parse_args()

    if args.all:
        targets = list(CAPABILITIES)
    elif args.cap in CAPABILITIES:
        targets = [args.cap]
    else:
        parser.error(f"pass --cap with one of {sorted(CAPABILITIES)}, or --all")

    options = {"R1": {"rules_only": args.rules_only}, "R2": {"msg_id": args.msg}}
    for cap in targets:
        CAPABILITIES[cap](**options.get(cap, {}))


if __name__ == "__main__":
    main()
