# Team Success Log

Every night at 12am Eastern, in the cloud (no computer needs to be on), Claude reads
Hayden's Slack (mentions, DMs, Team Success group tags, and #forum_teamsuccess) for the
day before yesterday, plus any days not yet read. Staying a working day behind means Claude
can see whether an ask was already resolved. It sorts each ask into Team Success or Personal and drafts the Team Success ones
into the Team Success Log Airtable base. Personal asks are listed in the run summary, not
logged (where they should live is undecided). Nothing reaches the shared Team Log until
Hayden ticks Approved.

## Where things live

| What | Where |
|---|---|
| All intake and classification rules | `.claude/skills/ts-intake/SKILL.md` (edit this to change behaviour) |
| Airtable tables and fields | `scripts/schema.py`, built by `scripts/build_base.py` |
| What a run may do in Airtable | `scripts/airtable.py` (create drafts, log rule changes and runs; no edit or delete) |
| Role on a client (CML / Senior / Tactical operator), read from PelOS | `scripts/pelos.py` |
| Review sessions with Hayden: running log of edits and his by-hand list | `reviews/` (record backups stay local, not in git) |
| Checks | `python3 -m unittest discover -s tests` |
| How Claude works in this repo (main branch only) | `CLAUDE.md` |

## One-time Airtable setup (Hayden, about 10 minutes)

1. In Airtable, create an empty base named **Team Success Log**. Copy its ID from the
   address bar (starts with `app`).
2. Create a personal access token at airtable.com/create/tokens, limited to that one base,
   with these scopes: `data.records:read`, `data.records:write`, `schema.bases:read`,
   `schema.bases:write`.
3. Add both to this cloud environment's secrets as `AIRTABLE_TOKEN` and `AIRTABLE_BASE_ID`,
   and add `api.airtable.com` to its allowed network domains.
4. Claude runs `python3 scripts/build_base.py` to build the tables.
5. Finish by hand (Airtable doesn't let Claude make these):
   - **Checks** formula field on Requests (the builder prints the formula to paste).
   - Views on Requests:
     - **Hayden**: personal view (not collaborative), filter Approved is unchecked AND
       Scrap is unchecked.
     - **Scrap**: personal view, filter Scrap is checked.
     - **Team Log**: filter Approved is checked AND Type is TS AND Scrap is unchecked; share
       this one.
