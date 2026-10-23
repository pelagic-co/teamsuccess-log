---
name: ts-intake
description: Team Success Slack intake. Scan Hayden's Slack (mentions, DMs, Team Success group tags, #forum_teamsuccess), classify each ask as Team Success or Personal, and draft the Team Success ones into the Team Success Log Airtable base for Hayden's review (Personal asks are listed in the run summary, not logged). Also handles "show open rule changes". Use for the nightly intake run, a manual dry run, or any question about intake rules.
---

# Team Success Slack intake

This file is the single home for every intake and classification rule. Hayden edits it
(from Claude Code on his phone or anywhere else); each edit is a commit; the next run uses
the new version. If a rule is not written here, it is not a rule.

**Rules version:** 2026-10-23 · v1.8

## Hard rules (never break these)

1. **Drafts only.** Create new records. Never tick **Approved**. Never untick it.
2. **Approved records are Hayden's.** Never edit, re-classify, comment on, or delete an
   approved record without asking Hayden in the conversation first and getting a yes.
3. **Never touch existing drafts either.** A run only creates new records in Requests and
   new rows in Rule Changes. Hayden does all editing.
4. **Never delete anything.** A message that is not an ask, or is a Personal ask, is
   skipped, never logged-then-deleted.
5. **Personal asks are not logged in this base.** List each one in the run summary
   instead. Where Personal asks should live is undecided (Hayden, 2026-10-21); until he
   decides, never write them to Airtable or anywhere else.
6. **Only these Slack sources.** Never scan all channels. See Sources.
7. **Fail loudly.** If Slack, Airtable or the Brain is unreachable, or a value doesn't fit
   the lists below, stop and report it. Never guess an ID, never invent a list value,
   never write a partial run silently.
8. **No Slack posting.** The run reads Slack. It never sends, reacts, or drafts messages.

## Sources (only these)

| Source | How to find it |
|---|---|
| @-mentions of Hayden | Messages containing `<@U07Q9KYU4MR>` in any channel Hayden can see |
| DMs to Hayden | 1:1 DMs where the author is not Hayden |
| Team Success group tags | New messages and thread replies in `#01_team-support` (`C0B00JQJLHZ`) that contain `<!subteam^S0AUZBR2VAL>` (the team_success group) |
| Team Success forum | New messages and thread replies in `#forum_teamsuccess` (`C0CA48ZUV16`) |

Slack search can't find group tags, so the group tag is caught by reading those two
channels' new messages directly. A team_success tag anywhere else is caught only if it
also @-mentions Hayden. Hayden decided that's enough (2026-10-21).

- Hayden's Slack user ID: `U07Q9KYU4MR`. Workspace: pelagicworkspace.slack.com.
- Skip: Hayden's own messages, bots, and messages Hayden only appears in as a cc with no
  ask of him or TS.
- Group DMs count only through the @-mention rule.
- **Not an ask → skip.** Thanks, emoji, social chatter, FYIs with nothing needed. If unsure
  whether it's an ask, draft it (Hayden can mark it "Not an ask").

## Scan window

- **Whole past days, one working day behind.** The run reads asks posted on whole Eastern
  days, from the day after the last run's last day up to the day before yesterday. The
  12am Wednesday run reads Monday, so every ask has had at least one full working day
  for a reply or fix to show up.
- `python3 scripts/airtable.py logged` gives the days to read (`read_slack_from` /
  `read_slack_to`). Use exactly those; never work them out yourself. They come from the
  **Runs** table, so a missed day is picked up as backlog automatically, with no limit on
  how far back.
- `nothing_due: true` means the days are already covered (e.g. a second run the same day):
  stop and say so.
- Read each ask's whole thread (or DM conversation) up to the moment of the run, not just
  up to the end of the day, to see what happened since.
- Dry run: whatever days Hayden names (default: last full Mon–Fri week). A dry run never
  logs a run.

## Dedupe (skip anything already logged)

Before drafting, load every **Slack link** and **Slack thread** value from Requests
(approved or not, any Type, any Status).
- Skip a message whose permalink is already a **Slack link**.
- Skip a thread reply whose thread is already a **Slack thread**, unless it's a clearly new
  and different ask; then draft it as its own record and fill **Related requests**.
- One ask = one record. Two asks in one message = two records with the same Slack link
  and a note saying "1 of 2" / "2 of 2" (dedupe treats the pair as logged).
- **Personal asks are never logged**, so dedupe can't skip them. Runs read separate days,
  so each Personal ask appears in one run summary only.
- **Same ask, new place** (e.g. reposted in another channel): draft it as its own record
  and fill **Related requests** with the earlier record's ID.

## Classification

### Type: Team Success vs Personal

The test is whose work it is, not which client it names. Decide in this order. First
match wins.

1. **Tagged to Team Success** (the team_success group, or posted in
   `#forum_teamsuccess`) → **TS**, whatever the client. Example: a teammate's ask about
   their Fronen hours tracker, tagged to team_success, is TS.
2. **Hayden's own account work on his three accounts** → **Personal**. These are the only
   Personal accounts: **DairyPill** (Dairy Pill), **Little Saints**, **Fronen**.
3. **Everything else** → **TS**. That includes work Hayden does himself on any other
   account (e.g. Nemah, SunPowder, Rosy Soil, Roostys, Lineage cover).

When unsure between TS and Personal, pick **TS** and say why in **Claude notes**. A wrong
TS draft is in front of Hayden to fix; a wrong Personal call never reaches Airtable.

**Personal → skip.** Don't draft it. Add it to the run summary as one line: the ask in a
few words, the client, and the Slack link.

### Scrap

Some TS asks are routine and don't belong in Hayden's review. Still draft them in full
(Type TS, Request ID, every field), but tick **Scrap** and set **Scrap reason**. Scrapped
records show only in the Scrap view, never in Hayden's view or the Team Log. Reasons:

- **Hours tracking / client add / milestone error:** someone asks to be added to a
  client or project in their hours tracker or capacity dashboard (in Airtable), asks a
  question about hours tracking, or reports hours or milestones not counting or showing
  under the wrong client. Not this: "Capacity" the 3PL and its portal (VAS, kitting,
  relabeling orders), which is client work.

When unsure, don't scrap; say in **Claude notes** that it might be scrap.

### Filling the fields

Fill every field you can on each TS draft. Leave a field blank rather than guess when the
message gives nothing to go on, and say what's missing in **Claude notes**.

- **Summary:** one line in your own words saying what is being asked for, so Hayden and
  the team can scan the log without opening Slack. Start with the action, name the
  client or tool, and leave out greetings and the requester's name (that's in
  **Requester**). Example: "Add Manukora to the hours tracker." Two asks in one message
  get one Summary each.
- **Message:** the Slack message text, word for word. Don't trim, fix or paraphrase it;
  only turn Slack's codes into readable text: people → names (`<@U07Q9KYU4MR>` →
  `@Hayden`), the group tag → `@team_success`, `<!here>` → `@here`, and links → `label
  (url)`. A message that only shares another message: use the shared message's text. A thread
  reply is the reply's own text, not the whole thread. Two asks in one message: both
  records carry the full message.
- **Type:** always **TS** on a draft. Hayden changes it to Personal by hand when a draft
  isn't TS work (and says why in **Why I changed it**, which feeds the rule-change loop).
- **Request ID:** next number after the highest TS-#### in Requests and after
  `TS-0007` (the last row backfilled in the Google Sheet), whichever is higher. Never reuse
  a number, even if Hayden later changes the Type.
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
- **Resource required:** every resource the ask genuinely needs (usually one; add more
  only when the ask clearly needs more than one kind of help). **Resource group:**
  exactly the groups of those resources (see Lists): Information + Capacity / hours →
  Thing + Person. Key distinctions:
  - Documented how-to = **Information**, not Process.
  - Time taken alone = **Tool**, not Workflow.
  - Ad-hoc "someone who has done it" = **Information**, not Advisor.
  - Capacity = more hours from same people; Staffing = a different person.
- **Root cause:** one of the four. "DK referral" is never a root cause (use Needs help).
  Leave it blank on routine adds (hours tracker, PelOS, vault access) where none of the
  four fits.
- **Response:** what TS has done so far, as seen in the thread up to the moment of the
  run. Fill only from evidence in the thread.
- **Routed to:** the route from the routing map for each Resource required, by role,
  separated by commas when there are several (skip the ones whose route is TBD). Hard
  stop: Training → Training & Education. Direction → CML, then services exec. Capacity /
  Staffing / Leadership / Advisor / Analysis → leave blank (route TBD).
  - Access: hours tracker, capacity dashboard and PelOS adds → **Systems**. 1Password
    vaults and other account access → **People Ops**.
- **Analysis** (Resource required, Person group): "investigate this for me" / "confirm
  these numbers" asks, where someone needs TS to do the digging rather than point to a
  resource.
- **Unblocked date:** the day the thread shows it was resolved, if it was resolved by the
  time of the run. A workaround counts as the unblock.
- **Lasting fix / status, Resource link, Workflow maturity, Related requests, TS time
  spent:** only from evidence. Fill **Related requests** when you see a repeat of an
  existing record (same problem, same tool, same client).
- **Status:** "Done" if the thread shows it was resolved by the time of the run, "In
  progress" if someone is visibly working on it, otherwise "Open".
- **Message time:** the Slack message timestamp.
- **Slack link:** the message permalink. **Slack thread:** the thread root permalink
  (same as Slack link if it's not in a thread).
- **Claude notes:** one to three short lines: why this Type, why these labels, and
  anything assumed or missing.
- **Original draft:** a copy of every label you set, as `Field: value` lines. Never shown
  to the team; it's how a later run sees what Hayden changed.
- **Scrap / Scrap reason:** both set or both blank. See Scrap.
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
bump the rules version, add a Changelog line, commit and push to `main` (the only branch;
see `CLAUDE.md`), then set the row to **Accepted** and fill **Commit**. For each he
rejects: set **Rejected**. Accept/reject only when Hayden says so for that row.

## Keeping lists in step with the Brain

The value lists below are copied from the Team Success space in the Pelagic Brain (owner:
Hayden). Versions copied: request model v1.4, resource required v1.2, root causes v1,
responses v1.1, routing map v0.
- **Ahead of the Brain (update the Brain pages to match):** "Analysis" added to Resource
  required (Person group); hours-tracker / PelOS access routes to Systems (2026-10-21).
  Resource required and Resource group are multi-select (2026-10-23).
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
    "Person": ["Capacity / hours", "Staffing", "Leadership", "Advisor", "Direction / clarity", "Analysis"]
  },
  "root_cause": ["Technically complex", "Poor visibility", "Insufficient resource", "Compliance"],
  "response": ["Answered", "Fixed directly", "Routed", "Created resource", "Mapped resource", "No action"],
  "lasting_fix": ["Needed", "Not needed", "Already existed"],
  "lasting_fix_status": ["Backlog", "In progress", "Done"],
  "workflow_maturity": ["W0", "W1", "W2", "W3", "W4", "W5"],
  "status": ["Open", "In progress", "Done", "Not an ask"],
  "rule_change_status": ["Open", "Accepted", "Rejected"],
  "personal_clients": ["DairyPill", "Little Saints", "Fronen"],
  "scrap_reason": ["Hours tracking / client add / milestone error"]
}
```

## Running

- **Daily run (scheduled every night at 12am Eastern, including weekends):** follow Sources → Scan window →
  Dedupe → Classification → write drafts with `python3 scripts/airtable.py create` →
  Rule-change loop → log the run with `python3 scripts/airtable.py finish-run run.json`
  (the days read and the counts; never any Personal details). Log the run only after the
  drafts are written; if anything fails, don't log it, so the next run reads those days
  again. End with a short summary: the Slack days read, drafts created (and how many
  already resolved), skipped as already logged, rule changes logged, then "Personal (not
  logged):" with one line per Personal ask (or "none"). Nothing else.
- **Dry run:** same, but write nothing to Airtable. Put the drafts and the Personal list
  in a review file for Hayden instead.
- Airtable access needs `AIRTABLE_TOKEN` and `AIRTABLE_BASE_ID` set in the environment.
  If either is missing, stop and say so.

## Changelog

- 2026-10-21 · v1 created from Hayden's build brief and the Team Success request model.
- 2026-10-21 · v1.1: team_success group confirmed (S0AUZBR2VAL). Added #forum_teamsuccess
  as a source. Type rule is now "whose work is it": tags to TS are TS even for DairyPill,
  Little Saints or Fronen; Hayden's own work on those accounts is Personal.
- 2026-10-21 · v1.2 from the first dry run (Oct 12–16): only DairyPill, Little Saints and
  Fronen are Personal, everything else TS. Group tags read from #01_team-support and
  #forum_teamsuccess, new messages only. Personal DMs grouped per conversation per day.
  Hours-tracker / PelOS access → Systems, vaults → People Ops. Added "Analysis" to
  Resource required. Root cause blank on Personal and routine adds. Same ask in a new
  place → its own record, linked via Related requests.
- 2026-10-21 · v1.3: Personal asks are no longer logged in this base; each run lists them
  in its summary. Where they should live is undecided. Drafts are always Type TS (Hayden
  sets Personal by hand); when unsure, pick TS. Personal DM grouping removed.
- 2026-10-23 · v1.4: **Summary** is now Claude's one-line summary of the ask, not the
  requester's words. New **Message** field holds the Slack message text word for word.
- 2026-10-23 · v1.5: one run a day (weekdays, about 5pm Eastern) instead of hourly. Each
  run reads whole past days up to yesterday, plus any backlog, so a reply or fix has had
  time to show up; Response, Unblocked date and Status use the thread as of the run. New
  **Runs** table records the days each run read.
- 2026-10-23 · v1.6: the run moves to every night at 12am Eastern and reads up to the day
  before yesterday, so each ask still gets a full working day to be resolved. Message
  rule now covers group tags, @here, links and shared messages.
- 2026-10-23 · v1.7: new **Scrap** checkbox and **Scrap reason** dropdown. Hours-tracker
  and capacity-dashboard adds, hours-tracking questions and milestone errors are drafted
  with Scrap ticked, so they show only in the Scrap view. Existing ones were back-filled.
- 2026-10-23 · v1.8: **Resource required** and **Resource group** are multi-select. Pick
  every resource the ask needs; Resource group holds exactly their groups. Routed to lists
  one route per resource.
