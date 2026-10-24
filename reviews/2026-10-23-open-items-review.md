# Open items review — 2026-10-23

Running log for Hayden's walkthrough of open records in the Team Success Log.
Backup of every record before any edit: scratchpad `requests_snapshot_before.json`
(29 records, taken at session start).

## Hayden to-do (by hand in Airtable, at the end)

_Things Claude can't do through the API. Added as they come up._

- [ ] **Source**: rename the option "Service Team Slack" → "Services Team Slack"
      (Customize field → edit the option). Renames it on every record at once.
      Claude updates the rules/code to match in the same session.
- [ ] _Waiting on decision_: once the party list is final, **Routed to** → change field
      type to Multiple select (Customize field). Do it the same day Claude pushes the
      matching code, or the nightly run will refuse to write drafts until both match.
- [ ] **PelOS read-only token** for the nightly run's role lookup: airtable.com/create/tokens
      → new token, scope `data.records:read` only, access: the **PelOS** base only. Add it
      to this cloud environment's secrets as `PELOS_TOKEN`.
- [ ] **Delete the "Account team" option** from Requester party and Needs help party
      (Customize field → trash icon on the option). No record uses it any more.
- [ ] **GitHub branches** (github.com/haydenpelagic/teamsuccess-log/branches): delete
      `main`, `claude/amazing-mendel-wc65nw` and `claude/clever-planck-4nm6n3`. Keep
      `claude/serene-dirac-5z23ay`: it's the default and now the only branch.

## Field changes Claude made

_Schema changes: new fields, renames, descriptions._

- Field order: Date received moved to sit right before Unblocked date in the Hayden,
  Team Log and Scrap views (2026-10-23).

## Record edits Claude made

_One line per record: what changed and why. Before/after copies in backups/edits-2026-10-23.jsonl._

- TS-0011 (approved by Hayden): Needs help → Training, Needs help party → Training &
  Education; Why I changed it filled (Services exec, no client for internal work,
  training need). Hayden had already set Requester party = Services exec and cleared Client.
- TS-0012 (approved by Hayden): Unblocked date → 2026-10-22, Lasting fix → Already
  existed, Notes += Jackson meeting summary. Kept Hayden's Response (Mapped resource) and
  Lasting fix status (Done).
- Internal → Services team (TS-0010, 0023, 0024, 0027, 0030, 0031): Client cleared,
  Needs help = Services team, Needs help party = Services team (new option). TS-0031's
  old Needs help party (Client Success, no name) replaced.
- TS-0033 Client → Sunrise Organics (Daniel → Tactical operator); TS-0017 Client → Zoid
  (Ciara → CML); TS-0008 Requester party blank + Claude note (Brian not staffed on Toon
  in PelOS yet).
- Requester party → Services team on internal no-client asks: TS-0010, 0023, 0024,
  0027, 0031. TS-0023 stays scrapped.
- Account team → PelOS role on that client, 18 fields across 17 records: TS-0009 Sr op,
  0012 Tactical, 0013 Sr op, 0014 CML, 0015 Sr op, 0016 CML, 0018 CML, 0019 Tactical,
  0020 Sr op, 0021 CML, 0025 CML, 0026 Sr op, 0028 CML, 0029 (Lina) Tactical, 0032
  (Alfonso) Tactical, 0034 Tactical, 0035 CML + (Daniel) Tactical.

## Decisions and proposals

- **Services team** is a new party, separate from Services exec (Hayden, 2026-10-23).
- Internal / services-team asks have **no client** (Client blank, not "Internal").
- **Training & Education** is the party for training needs (no separate "Training").
- Internal records: Needs help = Services team (name and party).
- **Account team is split** into CML / Senior operator / Tactical operator (accepted).
  Rule: look up the person's role **on that client** in PelOS → Engagements (Client
  Management Lead / Senior Operator / Tactical Operator(s)), using the engagement that
  covers the message date. Code: `scripts/pelos.py`. Fallbacks (Hayden, 2026-10-23):
  internal ask with no client → Services team; not staffed on that client in PelOS →
  leave blank and say so in Claude notes; several roles on one client → most senior
  (CML > Senior operator > Tactical operator).
- **One branch only:** `claude/serene-dirac-5z23ay` (GitHub default; Hayden can't change
  the default without admin). `main` to be deleted by Hayden. CLAUDE.md, skill, README
  and the nightly run point at the new branch.
- **Routed to** becomes multi-select using the same party list (accepted).

## Follow-ups for the intake rules / code (end of session)

- ~~Repo schema behind live base~~: false alarm, `main` already has these (v1.8).
- Build the `ts-review` playbook + safe edit tool; CLAUDE.md pointer.
- Rules: Source option rename, Services team party, Internal → no client, plus the two
  proposals once decided. Update the Brain party list to match.

## Issues spotted before the walkthrough

- `recppIGJvxbNKwUuo`: completely blank record with **Approved ticked**. Likely shows
  in Team Log as an empty row. Needs a decision (delete?).
- TS-0031: Needs help party = Client Success but Needs help is blank → Checks error.
