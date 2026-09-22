# inboxHero

Repository: https://github.com/shivdeepnv/inboxhero

An agentic system that takes a 100-message mock inbox from unread to zero: every message gets exactly one
disposition, decided by rules where possible and by Claude (via CrewAI) where it isn't. Full capability details,
design justifications and the required Final Report answers are in [CAPABILITIES.md](CAPABILITIES.md); this file
covers setup and a short architecture summary.

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then put your Anthropic key in .env
```

## Running

```bash
python demo.py --cap R1                                    # zero the inbox
python demo.py --cap R2                                    # grounded replies (3 demo cases)
python demo.py --cap R3 --dry-run                           # show what would send, write nothing
python demo.py --cap R3                                     # gate real sends interactively (y/N per message)
python demo.py --cap R4                                     # standing preference, two-process demo
python demo.py --cap R5                                     # hostile inbox scan
python demo.py --cap R6                                     # dashboard
python demo.py --cap X1                                     # daily digest
python demo.py --cap X2 --sender priya@paperjet.io          # unread mail from a sender
python demo.py --cap X3 --thread t-launch                   # thread summary
```

Run R1 before anything else; several later capabilities read `decisions.json`, which R1 produces.

## Architecture

A plain Python pipeline, not a multi-agent graph. Every message goes through a deterministic rule router
(`rules.py`) first; only messages the rules can't confidently place reach a CrewAI agent (`crew_client.py`
wraps one shared `Agent`/`Task`/`Crew` pattern used by every model-backed capability). Retrieval is thread-walk
first, keyword search across other threads as a fallback (`retrieval.py`), and every model output that claims a
fact is checked against verbatim quotes from the actual mail store before it's trusted. Exactly one pair of
functions in the whole codebase (`actions.send_message`, `actions.delete_message`) can cause an irreversible
effect, and both are gated by explicit approval or `--dry-run`; no CrewAI-facing code imports them.

**Disposition vocabulary:** reply, archive, defer, delegate, escalate — defined in `dispositions.py`.

**Reversible / irreversible:** `draft`, `label`, `archive`, `defer` are reversible and run automatically;
`send` and `delete` are irreversible and gated (the mock store has no trash, so delete is treated as
irreversible too).

**Framework:** CrewAI, chosen and justified in [CAPABILITIES.md](CAPABILITIES.md); model: Claude
`claude-haiku-4-5-20251001` throughout.

**Retrieval:** thread-walk, with a keyword-search fallback across other threads (see CAPABILITIES.md for why).

The Final Report (what was refused, the untrusted-data boundary, accountability, and what CrewAI did/didn't
give us) is answered in full at the bottom of [CAPABILITIES.md](CAPABILITIES.md).
