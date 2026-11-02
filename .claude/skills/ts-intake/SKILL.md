---
name: ts-intake
description: Team Success Slack intake. Scan Hayden's Slack (mentions, DMs, Team Success group tags, #forum_teamsuccess), classify each ask as Team Success or Personal, and draft the Team Success ones into the Team Success Log Airtable base for Hayden's review (Personal asks are listed in the run summary, not logged). Also handles "show open rule changes". Use for the nightly intake run, a manual dry run, or any question about intake rules.
---

# Team Success Slack intake

This file is the single home for every intake and classification rule. Hayden edits it
(from Claude Code on his phone or anywhere else); each edit is a commit; the next run uses
the new version. If a rule is not written here, it is not a rule.

**Rules version:** 2026-11-02 · v1.13

## Hard rules (never break these)

1. **Never tick Approved. Never untick it.** Never fill **Rule changes** on a request;
   the rule-change loop links it from the Rule Changes side.
2. **The nightly run creates and follows up, nothing else.** It creates new records and
   Rule Changes rows, and follows up open requests (see Follow-up), which may change only
   the follow-up fields and add dated lines to **Notes**. It never changes how a request
   was classified.
3. **Overwriting is fine when Hayden asks.** In a conversation, when Hayden asks, Claude
   may overwrite any other field on existing requests, drafts or approved (e.g.
   back-filling a new field), with `python3 scripts/airtable.py update`. Say in the
   Changelog what was overwritten. When the overwrite fills a classification field, add
   it to that record's **Original draft** too, so the rule-change loop doesn't read it as
   Hayden's change.
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
  draft nothing and log no run, but still do the Follow-up, then say so.
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
(Type TS, Request ID, every field), but tick **Scrap** and add a line to **Claude notes**
reading `Scrap reason: <reason>`. Scrapped records show only in the Scrap view, never in
Hayden's view or the Team Log. Reasons:

- **Hours tracking / client add / milestone error:** someone asks to be added to a
  client or project in their hours tracker or capacity dashboard (in Airtable), asks a
  question about hours tracking, or reports hours or milestones not counting or showing
  under the wrong client. Not this: "Capacity" the 3PL and its portal (VAS, kitting,
  relabeling orders), which is client work.

When unsure, don't scrap; say in **Claude notes** that it might be scrap.

### Filling the fields

Fill every field you can on each TS draft. Leave a field blank rather than guess when the
message gives nothing to go on, and say what's missing in **Claude notes**. Exceptions:
**Requester party**, **Root cause** and **Topic** are never blank; when unsure, pick the
best fit and say in **Claude notes** that it's a best guess and why.

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
- **Topic:** every subject the ask is about, so Hayden can count asks by topic. Usually
  one; add more only when the ask is clearly about more than one. Topic is the subject,
  not the kind of help (that's **Resource required**): access to a forecast sheet is
  Forecasting, not Accounts & AI Tools.
  - **Ops Hub:** work inside a client's Ops Hub (inventory log, WOH, BOM, getting data in).
  - **Forecasting:** demand planners, forecast files, S&OP, MRP, WOH targets, projections.
    Forecast work built inside an Ops Hub gets both Ops Hub and Forecasting.
  - **COGS:** cost of goods, landed cost, unit cost, margin.
  - **Vendor Search:** 3PL, co-packer, CM and lab searches: RFQs, quotes, eval matrices,
    vendor contacts.
  - **Client Ops Execution:** one-off client operations: PO status, 3PL portal how-tos,
    inventory mismatches between systems, packaging and materials.
  - **Templates & SOPs:** internal templates, SOPs, checklists, one-pagers, reusable tools
    (RACI, EOW report, offboarding).
  - **Hours & Capacity:** hours tracker, capacity dashboard, operator UI, SOW and
    milestone assignment.
  - **Accounts & AI Tools:** Claude, 1Password, Notion, Gemini, 2FA, AI agent builds.
  - **GS1:** UPCs, GTINs, barcodes, GS1 company prefix and membership, product data
    registered with GS1. A barcode ask about packaging artwork gets GS1 too.
  - **Other:** none of the above fits. Only on its own. Add a line to **Claude notes**
    reading `Suggested topic: <name>`, naming the topic you'd have picked (a short, general
    name like "Packaging", not a client or one-off). Reuse an earlier suggestion's exact
    name when it fits, so repeats count together. See Rule-change loop step 4.
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
- **Requester:** the Slack author's full name.
- **Requester party:** never blank. Run
  `python3 scripts/airtable.py party "<Requester>" "<Client>" <message date>` and use the
  party it prints; put its `why` in **Claude notes** when it says "best guess". In order
  (Hayden, 2026-10-23 and 2026-11-02):
  1. No client (internal ask) → **Services team**.
  2. The person's role on that client in PelOS on the message date: **CML**, **Senior
     operator** or **Tactical operator** (several roles → most senior).
  3. Not found in PelOS → best guess: the party the person has most often on earlier
     requests.
  4. Still nothing → best guess: their most senior active PelOS role.
  5. Still nothing (e.g. not an operator) → pick the closest party yourself from the
     routing map (e.g. Client Success, People Ops, Services exec) and say why.
  The command needs `PELOS_TOKEN` for steps 2 and 4; without it, it skips them and says so.
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
- **Root cause:** never blank; one of the four (Brain: Team Success root causes):
  - **Technically complex:** the task is hard to do with what exists.
  - **Poor visibility:** the resource exists, but the person couldn't find it.
  - **Insufficient resource:** the resource doesn't exist, or isn't good enough. Routine
    adds (hours tracker, PelOS, vault access) are this: there's no way to do it yourself.
  - **Compliance:** the resource or check exists and was visible, but isn't followed.
  "DK referral" is never a root cause (use Needs help). When the message gives nothing to
  go on, pick the most likely and say it's a best guess.
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
- **Resource link, Related requests:** only from evidence. **Resource link** is the
  doc, tool or file that answered or fixed it. Fill **Related requests** when you see a
  repeat of an existing record (same problem, same tool, same client).
- **Notes:** a running log of what happened, one dated line per event
  (`2026-11-03: Javier fixed the WOH formula; SD4 now shows correctly.`): who did what,
  what fixed it, workarounds, and anything still outstanding. A new draft starts with a
  line for what the thread already shows, if anything. Lines are only ever added, never
  edited or removed (Hayden may type here too).
- **Status:** "Done" if the thread shows it was resolved by the time of the run, "In
  progress" if someone is visibly working on it, otherwise "Open".
- **Message time:** the Slack message timestamp.
- **Slack link:** the message permalink. **Slack thread:** the thread root permalink
  (same as Slack link if it's not in a thread).
- **Claude notes:** one to three short lines: why this Type, why these labels, and
  anything assumed or missing.
- **Original draft:** a copy of every label you set, as `Field: value` lines (several
  values separated by commas). Never shown to the team; it's how a later run sees what
  Hayden changed.
- **Scrap:** ticked only with a `Scrap reason:` line in Claude notes. See Scrap.
- **Approved:** never set.

## Follow-up (every run, after new drafts)

Every request that isn't closed gets checked again each night until it is. **Closed** =
Status **Done** or **Not an ask**. Approved and scrapped requests are followed up too.

1. `python3 scripts/airtable.py open-requests` lists them, with their Slack thread,
   requester, Status, Response, Unblocked date and Notes.
2. For each, read its Slack thread up to now, plus any messages between Hayden and the
   requester since the ask was posted. Only act on evidence; no evidence of change → leave
   it alone (no note).
3. When something happened, write it with `python3 scripts/airtable.py follow-up
   followups.json`. Each entry gives the Request ID, a `note` (one line saying what
   happened; the command dates it and adds it to **Notes**), and any of these fields:
   **Status**, **Unblocked date**, **Response**, **Routed to**, **Resource link**,
   **Related requests**. Nothing else can change.
4. **Closing:** set Status **Done** yourself when the thread shows it was resolved
   (answered, fixed, or a workaround that unblocks them). Done needs an **Unblocked date**
   and a note saying what resolved it. Set **Not an ask** only when it clearly wasn't one.
5. A closed request is never reopened. If the same problem comes back, it's a new
   request (a new draft) with **Related requests** pointing to the old one.

**"Flag ones that need my review":** when Hayden asks, list open requests where the
thread has gone quiet, the next step is his, or you're unsure whether to close, one line
each with why.

## Rule-change loop

At the end of every run (and whenever Hayden asks):
1. Run `python3 scripts/airtable.py pending-changes`. It lists requests (drafted on or
   after 2026-11-03, with no Rule changes link yet) where a classification label differs
   from **Original draft**, i.e. Hayden changed Claude's call. Follow-up fields don't count.
2. For each, work out the most likely reason from the record, its message and what Hayden
   changed, and write one Rule Changes row: the proposed rule (one sentence, written as it
   would appear in this file), the reason (start it with "Best guess at why:"), the section
   of this file it changes, status **Open**, and a link back to the record(s). Group
   records that point to the same rule into one row.
3. Never edit this file because of a rule change on your own. Hayden accepts it.
4. **New topics.** Run `python3 scripts/airtable.py topic-suggestions`. For each suggested
   topic it lists (3 or more Other requests share it, and no Rule Changes row has proposed
   it before), write one Rule Changes row: proposed rule `Add topic "<name>" to the Topic
   list.`, the reason (how many asks and what they were about), skill section "Filling the
   fields (Topic) and Lists (topic)", status **Open**, linked to those requests.
   Use the name exactly as the command prints it. A rejected topic is never proposed again.

**Accepting a new topic:** add it to the `topic` list (before "Other") and give it a
definition under **Topic**, then run `python3 scripts/build_base.py` (it reports the new
choice; Airtable adds it on first use), then re-tag the linked requests with `update`,
replacing Other with the new topic.

**"Show open rule changes":** list Rule Changes with status Open, newest first, each with
its proposed rule, reason and source records. For each one Hayden accepts: edit this file,
bump the rules version, add a Changelog line, commit and push to `claude/serene-dirac-5z23ay` (the only branch;
see `CLAUDE.md`), then set the row to **Accepted** and fill **Commit**. For each he
rejects: set **Rejected**. Accept/reject only when Hayden says so for that row.

## Keeping lists in step with the Brain

The value lists below are copied from the Team Success space in the Pelagic Brain (owner:
Hayden). **Topic** is the exception: its list lives only in this file (Hayden,
2026-11-02). Versions copied: request model v1.6, resource required v1.3, root causes v1,
responses v1.1, routing map v0 (last changed 2026-11-02). The Brain pages match these
rules as of 2026-11-02.
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
    "CML",
    "Senior operator",
    "Tactical operator",
    "Services team",
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
  "status": ["Open", "In progress", "Done", "Not an ask"],
  "rule_change_status": ["Open", "Accepted", "Rejected"],
  "personal_clients": ["DairyPill", "Little Saints", "Fronen"],
  "topic": [
    "Ops Hub",
    "Forecasting",
    "COGS",
    "Vendor Search",
    "Client Ops Execution",
    "Templates & SOPs",
    "Hours & Capacity",
    "Accounts & AI Tools",
    "GS1",
    "Other"
  ]
}
```

## Running

- **Daily run (scheduled every night at 12am Eastern, including weekends):** follow Sources → Scan window →
  Dedupe → Classification → write drafts with `python3 scripts/airtable.py create` →
  Follow-up → Rule-change loop → log the run with `python3 scripts/airtable.py finish-run
  run.json` (the days read and the counts; never any Personal details). Log the run only
  after the drafts are written; if anything fails, don't log it, so the next run reads
  those days again. End with a short summary:
  the Slack days read, drafts created (and how many already resolved), skipped as already
  logged, requests followed up and closed (one line each for the closed ones), rule
  changes logged, then "Personal (not logged):" with one line per Personal ask (or
  "none"). Nothing else.
- **Dry run:** same, but write nothing to Airtable. Put the drafts and the Personal list
  in a review file for Hayden instead.
- Airtable access needs `AIRTABLE_TOKEN` and `AIRTABLE_BASE_ID` set in the environment.
  If either is missing, stop and say so. `PELOS_TOKEN` (read-only, PelOS base) is needed
  for the PelOS role lookup; if it's missing, carry on with the fallbacks and say so in
  the summary.

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
- 2026-11-02 · v1.9: new **Topic** multi-select (Ops Hub, Forecasting, COGS, Vendor
  Search, Client Ops Execution, Templates & SOPs, Hours & Capacity, Accounts & AI Tools,
  Other). Required on every draft; Other only on its own. The list lives only here, not in
  the Brain. TS-0008 to TS-0076 were back-filled.
- 2026-11-02 · v1.10: Claude may overwrite existing requests (drafts or approved) when
  Hayden asks in a conversation, via the new `update` command; never Approved, Why I
  changed it or Rule changes. The nightly run still only creates. Used first to back-fill
  Topic on TS-0008 to TS-0076.
- 2026-11-02 · v1.11: an Other topic needs a `Suggested topic:` line in Claude notes. Once
  3 Other requests share a suggestion, the run proposes adding it as a Rule Changes row;
  Hayden accepts or rejects as usual. New `topic-suggestions` command.
- 2026-11-02 · v1.12: new topic **GS1** (UPCs, GTINs, barcodes), added by Hayden. TS-0062
  re-tagged from Other to GS1.
- 2026-11-02 · v1.13:
  - **Requester party** and **Root cause** are never blank (best guess + note). Party
    follows Hayden's 2026-10-23 rule (PelOS role on the client: CML / Senior operator /
    Tactical operator; no client → Services team), now with fallbacks, via the new
    `party` command. "Account team" retired. Missing party and root cause back-filled.
  - Removed **TS time spent**, **Lasting fix**, **Lasting fix status**, **Workflow
    maturity**, **Why I changed it** and **Scrap reason**. Scrap reasons now go in Claude
    notes; existing Lasting fix and Why I changed it values were copied into Notes first.
  - New **Follow-up**: every run re-checks open requests, adds dated lines to Notes,
    updates the follow-up fields and closes them when resolved. Runs log how many.
  - Rule-change loop now spots Hayden's changes by comparing labels to Original draft
    (requests drafted from 2026-11-03), since Why I changed it is gone.
