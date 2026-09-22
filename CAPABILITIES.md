# CAPABILITIES.md

**Student:** Shivdeep Nancherla, cert-aai-2026-06-0050
**Repository:** https://github.com/shivdeepnv/inboxhero

Run everything through one entry point:

```
python demo.py --cap R1
python demo.py --cap R2                          # or: --msg <id> for one message
python demo.py --cap R3 --dry-run                # then, without --dry-run, to actually gate a send
python demo.py --cap R4
python demo.py --cap R5
python demo.py --cap R6
python demo.py --cap X1
python demo.py --cap X2 --sender priya@paperjet.io
python demo.py --cap X3 --thread t-launch
```

R1 must run first; R2, R3, R4 and R6 read files it produces (`decisions.json`). R3 reads drafts that R2 and R4 produce (`drafts.json`).

---

## The system, in one paragraph

A Python pipeline built on CrewAI, using Claude (`claude-haiku-4-5-20251001`) for every model call. Messages are
loaded and run through a deterministic rule router first (`rules.py`); only messages the rules can't confidently
place reach a CrewAI agent. Retrieval (thread-walk, then a keyword fallback across other threads) grounds replies,
preference-application and commitment extraction in verbatim quotes checked against the actual mail store. Every
action that could send or delete a message is reachable through exactly one gated pair of functions
(`actions.py`), so nothing an email says — including four separate prompt-injection attempts planted in the
inbox — can cause an irreversible effect without a human's explicit approval. State that must outlive a process
(preferences, the trace log, decisions) lives in small JSON files on disk.

## Design choices

- **Framework: CrewAI.** Every model-backed capability (R1's model stage, R2, R4's preference extraction, R6's
  commitment extraction, X1, X3) runs through one shared `Agent`/`Task`/`Crew` wrapper in `crew_client.py`. The
  agents are given no tools, so nothing they read can reach `actions.py`. See Final Report Q4 for what CrewAI
  did and didn't buy us here.
- **Retrieval: thread-walk, with a keyword fallback.** `thread_id` already gives an inbox its own structure, so
  walking the thread (`retrieval.thread_walk`) is the primary method and is exact. Some grounding facts live in a
  different thread entirely (the board review date, in R2's m040 case) so a keyword search across other threads,
  weighted by how rare each shared term is (`retrieval.keyword_search`), is the documented fallback.
- **Reversible vs. irreversible.** `send` and `delete` are irreversible and gated; `draft`, `label`, `archive`
  and `defer` are reversible and run without a prompt. Deleting is treated as irreversible because the mock
  store has no trash — once `actions.delete_message` writes to `deleted.jsonl`, `inbox_store.load_inbox` never
  loads that message again.
- **Where the gate sits.** Exactly two functions in the whole codebase can cause an irreversible effect
  (`actions.send_message`, `actions.delete_message`), both defined in `actions.py`, both calling
  `gate.require_approval()` before doing anything. Only `outbound.py` (R3) imports `actions.py` — no
  CrewAI-facing module does. This is also the R5 defence: a hostile message can influence what a draft says, but
  it has no path to a send or a delete.
- **Escalation line.** Reversible dispositions (archive, defer, delegate) happen automatically. Anything that
  would send or delete needs an explicit approval per action, shown with the full message content and its cited
  ids, or an explicit `--dry-run`. The trade-off: a wrongly-archived message needs the owner to notice it in the
  digest or dashboard rather than being asked about it directly — we chose this because asking about all 71
  archived/deferred messages individually would train the owner to approve without reading, per the assignment's
  own warning.
- **Commitments vs. replies use different rules on purpose.** R2 forbids the model from computing a new date
  ("do not calculate... repeat them exactly"), because a reply must never assert something the inbox didn't say.
  R6's commitment extraction explicitly allows resolving "two days before the 18th" into "the 16th", because
  Part 7 asks for exactly that kind of cross-message resolution. Both are still checked against verbatim quotes
  from the source emails; only the arithmetic permission differs.
- **Weekday resolution is done in code, not by the model.** `commitments.weekday_table` computes the actual
  calendar date for every weekday name relative to when a message was sent, and hands that table to the model
  instead of asking it to compute a date itself. This specifically fixed a case where an email sent on a
  Wednesday proposed "the demo on Wednesday" (same day) and the model needed to be told that "Wednesday" most
  likely meant *today*, not next week.

## Capabilities

| id | name | tier | one-line claim |
|----|------|------|----------------|
| R1 | Zero the inbox | B | every message gets one disposition + reason; 64/100 never reached a model |
| R2 | Grounded reply | B | drafts cite the earlier message they used, or refuse and draft nothing |
| R3 | Gate the irreversible | C | no send/delete without approval or --dry-run; outbox/ only |
| R4 | Persistent preference | C | a preference survives a full process restart; rejects a spoofed one |
| R5 | Refuse embedded instructions | C | detects, refuses, flags, and reports 7 hostile messages |
| R6 | Dashboard | C | three panes; a two-message commitment; a surfaced time conflict |
| X1 | Daily digest | B | needs-you / can-wait / handled-automatically, from one completed run |
| X2 | Unread mail from a sender | A | one lookup, one output, no model call |
| X3 | Thread summary | B | summarizes a thread and names its one open question |

The exact command, observable outcome and evidence for each is in `capabilities.json`, which a marking script
reads; this file is for a person. Keep the two in step.

## Disposition vocabulary

- **reply** — a person expects an answer from the owner.
- **archive** — nothing to do; safe to close, nothing deleted.
- **defer** — a future commitment or deadline to track, no reply needed now.
- **delegate** — the action belongs to someone other than the owner.
- **escalate** — ambiguous, involves money/legal/credentials, or is phishing/an injection attempt; the system
  will not decide alone.

## Notes on scope

- Commitment extraction (R6) only scans the 36 messages that reached the model in R1, and only those matching a
  date/deadline pattern, on the theory that a Spotify receipt isn't a commitment worth tracking. This is a
  deliberate trade-off, not an oversight.
- R5's "hostile" scan covers both prompt-injection attempts addressed to the assistant (m017, m024, m039, m047)
  and phishing/impersonation attempts addressed to the owner (m021, m045, m023), since both need the same
  "don't act, flag, don't delete" handling, even though the PDF's Part 6 language focuses on the former.

## Final Report

**1. What did you refuse to automate?**
m012 ("the thing") asks the owner to confirm a task referenced only as "that thing we talked about after the
standup," and nothing else in the inbox says what it is. R2 refuses to draft anything for it rather than invent
a plausible-sounding reply, because a wrong guess here is worse than no reply at all. The same line is drawn for
m008, where Devika asks for the staging credentials to be resent: R2 finds the earlier message (m003) that has
them, but refuses to reproduce a credential in a reply under any circumstance, leaving that to the owner to
share through a proper channel.

**2. Where does untrusted text enter your system?**
Every email body and subject is wrapped in `<untrusted_email>` tags (`untrusted.format_message`) before it
reaches any prompt, and every prompt tells the model that content inside those tags is data, never
instructions. The property that actually enforces this is architectural, not the wording: the only two functions
capable of an irreversible effect, `actions.send_message` and `actions.delete_message`, are defined in one file
that no CrewAI-facing module imports, so no agent's output has a code path to either one without going through
`outbound.py`'s human approval gate. An attacker would have to both escape the untrusted-data framing *and* find
an import path into `actions.py` that bypasses `gate.require_approval`. Four messages tried the first half of
that (m017, m024, m039, m047); none got anywhere near the second.

**3. Who is accountable when it sends the wrong thing?**
The owner is accountable, because nothing is ever sent without their explicit approval: R3 shows the full To,
CC, subject, body and cited message ids before asking `Send this message? [y/N]`, and only writes to `outbox/`
on an explicit yes. `trace.jsonl` records the proposal, the decision, and the outcome for every gated action,
plus the exact `cited` ids behind every draft, so a bad send can be traced back to either a bad citation (an R2
or R6 grounding failure, checkable against the quoted facts) or a bad approval (a human error, visible in the
log's `approved_at` timestamp).

**4. Name your own machinery.**
CrewAI's `Agent` and `Task` are used directly, one agent per capability (triage analyst, reply drafter,
preference extractor, commitment extractor, digest writer, thread summarizer), all built through one shared
constructor in `crew_client.make_agent`. `Crew` is instantiated fresh per call inside `crew_client.ask`, since
none of this work needs multi-agent handoff. Everything else is ours: `rules.py`'s `route()` and `triage.py`'s
loop are the router that decides whether a message reaches CrewAI at all; `gate.py` and `actions.py` are the
approval boundary no framework gave us; `untrusted.py` is the data/instruction boundary. What a framework's
`Process`/task-dependency graph would have given us for free is declarative multi-step orchestration — we didn't
need it, since our pipeline is a two-stage rule-then-model decision per message, not a multi-agent handoff, and
writing it as plain Python made the approval gate and the untrusted-data boundary easier to verify by reading
the code than a task graph would have been.
