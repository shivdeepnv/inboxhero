import argparse

from triage import run_r1

CAPABILITIES = {"R1": run_r1}


def main():
    parser = argparse.ArgumentParser(description="inboxHero capability runner")
    parser.add_argument("--cap", help="capability id, e.g. R1")
    parser.add_argument("--all", action="store_true", help="run every capability in order")
    parser.add_argument("--rules-only", action="store_true", help="R1: stop after the rule stage")
    args = parser.parse_args()

    if args.all:
        targets = list(CAPABILITIES)
    elif args.cap in CAPABILITIES:
        targets = [args.cap]
    else:
        parser.error(f"pass --cap with one of {sorted(CAPABILITIES)}, or --all")

    for cap in targets:
        if cap == "R1":
            CAPABILITIES[cap](rules_only=args.rules_only)
        else:
            CAPABILITIES[cap]()


if __name__ == "__main__":
    main()
