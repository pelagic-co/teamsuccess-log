# Team Success Log

Every hour on weekdays, 9am–5pm Eastern, Claude reads Hayden's Slack (mentions, DMs,
Team Success group tags, and #forum_teamsuccess), sorts each ask into Team Success or Personal, and drafts the Team Success ones into
the Team Success Log Airtable base. Personal asks are listed in the run summary, not logged
(where they should live is undecided). Nothing reaches the shared Team Log until Hayden
ticks Approved.

## Where things live

| What | Where |
|---|---|
| All intake and classification rules | `.claude/skills/ts-intake/SKILL.md` (edit this to change behaviour) |
| Airtable tables and fields | `scripts/schema.py`, built by `scripts/build_base.py` |
| What a run may do in Airtable | `scripts/airtable.py` (create drafts, log rule changes; no edit or delete) |
| Checks | `python3 -m unittest discover -s tests` |

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
     - **Hayden Review**: personal view, filter Approved is unchecked.
     - **Team Log**: filter Approved is checked AND Type is TS; share this one.
