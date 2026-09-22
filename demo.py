import argparse

from grounded import run_r2
from hostile import run_r5
from outbound import run_r3
from standing import run_r4
from triage import run_r1

CAPABILITIES = {"R1": run_r1, "R2": run_r2, "R3": run_r3, "R4": run_r4, "R5": run_r5}


def main():
    parser = argparse.ArgumentParser(description="inboxHero capability runner")
    parser.add_argument("--cap", help="capability id, e.g. R1")
    parser.add_argument("--all", action="store_true", help="run every capability in order")
    parser.add_argument("--rules-only", action="store_true", help="R1: stop after the rule stage")
    parser.add_argument("--msg", help="R2: a single message id to draft a reply for")
    parser.add_argument("--stage", choices=["record", "apply"], help="R4: run one stage in this process")
    parser.add_argument("--dry-run", action="store_true", help="R3: show what would be sent, write nothing")
    parser.add_argument("--delete", help="R3: propose deleting this message id through the gate")
    args = parser.parse_args()

    if args.all:
        targets = list(CAPABILITIES)
    elif args.cap in CAPABILITIES:
        targets = [args.cap]
    else:
        parser.error(f"pass --cap with one of {sorted(CAPABILITIES)}, or --all")

    options = {"R1": {"rules_only": args.rules_only}, "R2": {"msg_id": args.msg},
               "R3": {"dry_run": args.dry_run, "delete": args.delete}, "R4": {"stage": args.stage}}
    for cap in targets:
        CAPABILITIES[cap](**options.get(cap, {}))


if __name__ == "__main__":
    main()
