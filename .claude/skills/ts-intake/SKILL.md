---
name: ts-intake
description: Team Success Slack intake. Scan Hayden's Slack (mentions, DMs, Team Success group tags, #forum_teamsuccess), classify each ask as Team Success or Personal, and draft records into the Team Success Log Airtable base for Hayden's review. Also handles "show open rule changes". Use for the hourly intake run, a manual dry run, or any question about intake rules.
---

# Team Success Slack intake

This file is the single home for every intake and classification rule. Hayden edits it
(from Claude Code on his phone or anywhere else); each edit is a commit; the next run uses
the new version. If a rule is not written here, it is not a rule.

**Rules version:** 2026-10-21 · v1.1

## Hard rules (never break these)

1. **Drafts only.** Create new records. Never tick **Approved**. Never untick it.
2. **Approved records are Hayden's.** Never edit, re-classify, comment on, or delete an
   approved record without asking Hayden in the conversation first and getting a yes.
3. **Never touch existing drafts either.** A run only creates new records in Requests and
   new rows in Rule Changes. Hayden does all editing.
4. **Never delete anything.** Personal items are kept (they are Hayden's future to-do
   list). A message that is not an ask is skipped, never logged-then-deleted.
5. **Only these Slack sources.** Never scan all channels. See Sources.
6. **Fail loudly.** If Slack, Airtable or the Brain is unreachable, or a value doesn't fit
   the lists below, stop and report it. Never guess an ID, never invent a list value,
   never write a partial run silently.
7. **No Slack posting.** The run reads Slack. It never sends, reacts, or drafts messages.

## Sources (only these)

| Source | How to find it |
|---|---|
| @-mentions of Hayden | Messages containing `<@U07Q9KYU4MR>` in any channel Hayden can see |
| DMs to Hayden | 1:1 DMs where the author is not Hayden |
| Team Success group tags | Messages containing `<!subteam^S0AUZBR2VAL>` (the team_success group) in any channel |
| Team Success forum | Every message and thread reply in `#forum_teamsuccess` (`C0CA48ZUV16`) |

- Hayden's Slack user ID: `U07Q9KYU4MR`. Workspace: pelagicworkspace.slack.com.
- Skip: Hayden's own messages, bots, and messages Hayden only appears in as a cc with no
  ask of him or TS.
- Group DMs count only through the @-mention rule.
- **Not an ask → skip.** Thanks, emoji, social chatter, FYIs with nothing needed. If unsure
  whether it's an ask, draft it (Hayden can mark it "Not an ask").

## Scan window

- Normal run: from (latest **Message time** in Requests − 2 hours) to now. Overlap is safe
  because of dedupe.
- Cap: never look back more than 7 days. First run ever: 7 days.
- Dry run: whatever window Hayden names (default: last full Mon–Fri week).

## Dedupe (skip anything already logged)

Before drafting, load every **Slack link** and **Slack thread** value from Requests
(approved or not, any Type, any Status).
- Skip a message whose permalink is already a **Slack link**.
- Skip a thread reply whose thread is already a **Slack thread**, unless it's a clearly new
  and different ask; then draft it as its own record and fill **Related requests**.
- One ask = one record. Two asks in one message = two records with the same Slack link
  and a note saying "1 of 2" / "2 of 2" (dedupe treats the pair as logged).

## Classification

### Type: Team Success vs Personal

The test is whose work it is, not which client it names. Decide in this order. First
match wins.

1. **Tagged to Team Success** (the team_success group, or posted in
   `#forum_teamsuccess`) → **TS**, whatever the client. Example: a teammate's ask about
   their Fronen hours tracker, tagged to team_success, is TS.
2. **Hayden's own account work** (Hayden is the operator) → **Personal**. Hayden's own
   accounts: **DairyPill** (Dairy Pill), **Little Saints**, **Fronen**. An ask of Hayden
   about one of these, outside the TS sources above, is his own work.
3. **Anything asking Hayden as TS for a resource** → **TS**.
4. **Everything else that is an ask of Hayden** → **Personal**.

Never discard. When unsure between TS and Personal, pick the best fit and say why in
**Claude notes**.

### Filling the fields

Fill every field you can for both Types. Leave a field blank rather than guess when the
message gives nothing to go on, and say what's missing in **Claude notes**.

- **Summary:** one line, in the requester's words.
- **Request ID (TS only):** next number after the highest TS-#### in Requests and after
  `TS-0007` (the last row backfilled in the Google Sheet), whichever is higher. Never reuse
  a number, even if Hayden later changes the Type. Personal records get no Request ID.
- **Intake type:** "Reactive request" for everything this run finds. ("Proactive finding"
  is Hayden's to log by hand.)
- **Source:** map the Slack location:
  - `#01_team-support` → Team Support Slack
  - `#forum_teamsuccess` → Team Support Slack (closest value; note it in Claude notes)
  - Service Team channel → Service Team Slack
  - 1:1 DM → DM
  - a client's internal channel → Internal client channel
  - anywhere else → the closest value; explain in Claude notes
- **Requester:** the Slack author's full name. **Requester party:** from the routing map
  (tactical operator / senior operator / CML → Account team; etc.). Unknown → blank + note.
- **Needs help / Needs help party:** only when the ask is on someone else's behalf. Both
  filled or both blank.
- **Client:** the client brand, or "Internal".
- **Urgency:** Blocking client work · Blocking internal work · Not blocking.
- **Resource group + Resource required:** must match (see Lists). Pick the group first.
  Key distinctions:
  - Documented how-to = **Information**, not Process.
  - Time taken alone = **Tool**, not Workflow.
  - Ad-hoc "someone who has done it" = **Information**, not Advisor.
  - Capacity = more hours from same people; Staffing = a different person.
- **Root cause:** one of the four. "DK referral" is never a root cause (use Needs help).
- **Response:** what TS has done *so far* as seen in Slack (often blank on a fresh ask).
  Fill only from evidence in the thread.
- **Routed to:** the route from the routing map for this Resource required, by role. Hard
  stop: Training → Training & Education. Access → People Ops. Direction → CML, then
  services exec. Capacity / Staffing / Leadership / Advisor → leave blank (route TBD).
- **Unblocked date:** only if the thread shows it was resolved. A workaround counts as the
  unblock.
- **Lasting fix / status, Resource link, Workflow maturity, Related requests, TS time
  spent:** only from evidence. Fill **Related requests** when you see a repeat of an
  existing record (same problem, same tool, same client).
- **Status:** "Open" unless the thread shows it's done.
- **Message time:** the Slack message timestamp.
- **Slack link:** the message permalink. **Slack thread:** the thread root permalink
  (same as Slack link if it's not in a thread).
- **Claude notes:** one to three short lines: why this Type, why these labels, and
  anything assumed or missing.
- **Original draft:** a copy of every label you set, as `Field: value` lines. Never shown
  to the team; it's how a later run sees what Hayden changed.
- **Approved:** never set.

## Rule-change loop

At the end of every run (and whenever Hayden asks):
1. Find Requests where **Why I changed it** is filled and **Rule changes** is empty.
2. For each, compare the record to its **Original draft**, read Hayden's note, and write
   one Rule Changes row: the proposed rule (one sentence, written as it would appear in
   this file), the reason, the section of this file it changes, status **Open**, and a
   link back to the record(s). Group records that point to the same rule into one row.
3. Never edit this file because of a rule change on your own. Hayden accepts it.

**"Show open rule changes":** list Rule Changes with status Open, newest first, each with
its proposed rule, reason and source records. For each one Hayden accepts: edit this file,
bump the rules version, add a Changelog line, commit and push, then set the row to
**Accepted** and fill **Commit**. For each he rejects: set **Rejected**. Accept/reject only
when Hayden says so for that row.

## Keeping lists in step with the Brain

The value lists below are copied from the Team Success space in the Pelagic Brain (owner:
Hayden). Versions copied: request model v1.4, resource required v1.2, root causes v1,
responses v1.1, routing map v0.
- At the start of each run, check those pages' versions. If any changed, finish the run on
  the current lists and log one Rule Changes row: "Brain list X changed (vA → vB); update
  the intake lists and the Airtable choices."
- A list change needs two edits together: the Brain page and the block below. Airtable
  picks up a new choice the first time a draft uses it; `python3 scripts/build_base.py`
  reports any list value Airtable doesn't have yet. A renamed or removed value also needs
  a by-hand edit of that field's choices in Airtable.

## Lists

The block below is read by the base builder and the tests. Keep it valid JSON.

```json ts-lists
{
  "type": ["TS", "Personal"],
  "intake_type": ["Reactive request", "Proactive finding"],
  "source": [
    "Team Support Slack",
    "Service Team Slack",
    "DM",
    "Internal client channel",
    "Meeting",
    "Request-log pattern",
    "Scheduled review",
    "Partner signal"
  ],
  "party": [
    "Team Success",
    "Client Success",
    "Systems",
    "Training & Education",
    "People Ops",
    "Network Success",
    "Industry Success",
    "People managers",
    "Account team",
    "Services exec",
    "Internal exec"
  ],
  "urgency": ["Blocking client work", "Blocking internal work", "Not blocking"],
  "resource_group": ["Thing", "Person"],
  "resource_required": {
    "Thing": ["Tool", "Training", "Information", "Process", "Workflow", "Access"],
    "Person": ["Capacity / hours", "Staffing", "Leadership", "Advisor", "Direction / clarity"]
  },
  "root_cause": ["Technically complex", "Poor visibility", "Insufficient resource", "Compliance"],
  "response": ["Answered", "Fixed directly", "Routed", "Created resource", "Mapped resource", "No action"],
  "lasting_fix": ["Needed", "Not needed", "Already existed"],
  "lasting_fix_status": ["Backlog", "In progress", "Done"],
  "workflow_maturity": ["W0", "W1", "W2", "W3", "W4", "W5"],
  "status": ["Open", "In progress", "Done", "Not an ask"],
  "rule_change_status": ["Open", "Accepted", "Rejected"],
  "personal_clients": ["DairyPill", "Little Saints", "Fronen"]
}
```

## Running

- **Hourly run (scheduled):** follow Sources → Scan window → Dedupe → Classification →
  write drafts with `python3 scripts/airtable.py create` → Rule-change loop. End with a
  three-line summary: drafts created (TS / Personal), skipped as already logged, rule
  changes logged. Nothing else.
- **Dry run:** same, but write nothing to Airtable. Put the drafts in a review file for
  Hayden instead.
- Airtable access needs `AIRTABLE_TOKEN` and `AIRTABLE_BASE_ID` set in the environment.
  If either is missing, stop and say so.

## Changelog

- 2026-10-21 · v1 created from Hayden's build brief and the Team Success request model.
- 2026-10-21 · v1.1: team_success group confirmed (S0AUZBR2VAL). Added #forum_teamsuccess
  as a source. Type rule is now "whose work is it": tags to TS are TS even for DairyPill,
  Little Saints or Fronen; Hayden's own work on those accounts is Personal.
