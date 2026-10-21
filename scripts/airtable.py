"""What an intake run is allowed to do in Airtable, and nothing more.

    python3 scripts/airtable.py logged              # Slack links/threads already logged, latest message time, next TS ID
    python3 scripts/airtable.py create drafts.json  # create draft Requests (validated first; all or nothing)
    python3 scripts/airtable.py pending-changes     # records whose "Why I changed it" has no rule change yet
    python3 scripts/airtable.py propose change.json # create one Rule Changes row linked to its source records
    python3 scripts/airtable.py open-changes        # Rule Changes with status Open
    python3 scripts/airtable.py set-change recXXX Accepted [commit-url]   # only when Hayden says so

There is deliberately no command to edit or delete a request record.
"""

import json
import re
import sys

from airtable_api import AirtableError, Client
from lists import group_of, load_lists
from schema import REQUESTS, RULE_CHANGES, requests_fields

BACKFILL_LAST_ID = 7  # TS-0007 is the last row backfilled into the Google Sheet request log
TS_ID = re.compile(r"^TS-(\d{4,})$")
SLACK_LINK = re.compile(r"^https://[a-z0-9-]+\.slack\.com/archives/[A-Z0-9]+/p\d+")
REQUIRED = ["Summary", "Type", "Slack link", "Slack thread", "Message time", "Claude notes", "Original draft"]


def next_ts_number(ids):
    highest = BACKFILL_LAST_ID
    for value in ids:
        m = TS_ID.match(value or "")
        if m:
            highest = max(highest, int(m.group(1)))
    return highest + 1


def validate_draft(draft, lists, known_links):
    """Returns a list of problems. An empty list means the draft may be written."""
    problems = []
    fields = {f["name"]: f for f in requests_fields(lists)}
    for name in draft:
        if name not in fields:
            problems.append(f"unknown field {name!r}")
    for name in REQUIRED:
        if not draft.get(name):
            problems.append(f"missing {name}")
    if "Approved" in draft:
        problems.append("drafts must not set Approved")
    for name, value in draft.items():
        spec = fields.get(name)
        if not spec or value in (None, "", []):
            continue
        if spec["type"] == "singleSelect":
            allowed = [c["name"] for c in spec["options"]["choices"]]
            if value not in allowed:
                problems.append(f"{name}={value!r} is not in the list")
        if spec["type"] == "multipleSelects":
            allowed = [c["name"] for c in spec["options"]["choices"]]
            if not isinstance(value, list):
                problems.append(f"{name} must be a list")
            else:
                problems += [f"{name}={v!r} is not in the list" for v in value if v not in allowed]
    if draft.get("Resource required"):
        try:
            if draft.get("Resource group") != group_of(lists, draft["Resource required"]):
                problems.append("Resource group does not match Resource required")
        except ValueError as e:
            problems.append(str(e))
    if bool(draft.get("Needs help")) != bool(draft.get("Needs help party")):
        problems.append("Needs help and Needs help party must both be filled or both blank")
    if draft.get("Type") == "TS" and not TS_ID.match(draft.get("Request ID") or ""):
        problems.append("TS draft needs a Request ID like TS-0008")
    if draft.get("Type") == "Personal":
        problems.append("Personal asks are not logged in this base; list them in the run summary")
    for key in ("Slack link", "Slack thread"):
        if draft.get(key) and not SLACK_LINK.match(draft[key]):
            problems.append(f"{key} is not a Slack permalink")
    if draft.get("Slack link") in known_links:
        problems.append("already logged (Slack link)")
    return problems


def cmd_logged(client):
    rows = client.list_records(REQUESTS, fields=["Slack link", "Slack thread", "Message time", "Request ID"])
    f = [r["fields"] for r in rows]
    times = sorted(x["Message time"] for x in f if x.get("Message time"))
    print(json.dumps({
        "slack_links": sorted({x["Slack link"] for x in f if x.get("Slack link")}),
        "slack_threads": sorted({x["Slack thread"] for x in f if x.get("Slack thread")}),
        "latest_message_time": times[-1] if times else None,
        "next_request_id": f"TS-{next_ts_number(x.get('Request ID') for x in f):04d}",
    }, indent=2))


def cmd_create(client, path):
    lists = load_lists()
    drafts = json.load(open(path, encoding="utf-8"))
    rows = client.list_records(REQUESTS, fields=["Slack link", "Request ID"])
    known = {r["fields"].get("Slack link") for r in rows}
    used_ids = {r["fields"].get("Request ID") for r in rows}
    batch_links, batch_ids, errors = set(), set(), []
    for i, d in enumerate(drafts):
        problems = validate_draft(d, lists, known)
        # Two asks in one message share a Slack link; the note "n of m" makes that explicit.
        if d.get("Slack link") in batch_links and not re.search(r"\b\d of \d\b", d.get("Claude notes", "")):
            problems.append("duplicate Slack link in this batch")
        rid = d.get("Request ID")
        if rid and (rid in used_ids or rid in batch_ids):
            problems.append(f"Request ID {rid} already used")
        batch_links.add(d.get("Slack link"))
        if rid:
            batch_ids.add(rid)
        if problems:
            errors.append(f"draft {i + 1} ({d.get('Summary', '?')[:50]}): " + "; ".join(problems))
    if errors:
        print("Nothing written. Fix these first:\n" + "\n".join(errors), file=sys.stderr)
        return 1
    for d in drafts:
        d.setdefault("Status", "Open")
    created = client.create_records(REQUESTS, drafts)
    print(f"created {len(created)} draft(s)")
    return 0


def cmd_pending_changes(client):
    rows = client.list_records(REQUESTS, formula="AND({Why I changed it}, NOT({Rule changes}))")
    print(json.dumps([{"id": r["id"], **r["fields"]} for r in rows], indent=2, default=str))


def cmd_propose(client, path):
    lists = load_lists()
    change = json.load(open(path, encoding="utf-8"))
    for key in ("Proposed rule", "Reason", "Skill section", "Source records"):
        if not change.get(key):
            raise AirtableError(f"rule change is missing {key}")
    change["Status"] = "Open"
    if change["Status"] not in lists["rule_change_status"]:
        raise AirtableError("bad status")
    client.create_records(RULE_CHANGES, [change])
    print("logged 1 rule change")


def cmd_open_changes(client):
    rows = client.list_records(RULE_CHANGES, formula="{Status}='Open'")
    print(json.dumps([{"id": r["id"], **r["fields"]} for r in rows], indent=2, default=str))


def cmd_set_change(client, record_id, status, commit=None):
    if status not in ("Accepted", "Rejected"):
        raise AirtableError("status must be Accepted or Rejected")
    if status == "Accepted" and not commit:
        raise AirtableError("an accepted rule change needs the commit link")
    fields = {"Status": status}
    if commit:
        fields["Commit"] = commit
    client.update_records(RULE_CHANGES, [(record_id, fields)])
    print(f"{record_id} set to {status}")


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    cmd, args = argv[0], argv[1:]
    try:
        client = Client()
        if cmd == "logged":
            cmd_logged(client)
        elif cmd == "create" and len(args) == 1:
            return cmd_create(client, args[0])
        elif cmd == "pending-changes":
            cmd_pending_changes(client)
        elif cmd == "propose" and len(args) == 1:
            cmd_propose(client, args[0])
        elif cmd == "open-changes":
            cmd_open_changes(client)
        elif cmd == "set-change" and len(args) in (2, 3):
            cmd_set_change(client, *args)
        else:
            print(__doc__)
            return 2
    except AirtableError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
