"""What an intake run is allowed to do in Airtable, and nothing more.

    python3 scripts/airtable.py logged              # Slack days to read, Slack links/threads already logged, next TS ID
    python3 scripts/airtable.py create drafts.json  # create draft Requests (validated first; all or nothing)
    python3 scripts/airtable.py finish-run run.json # log the run in Runs (only after its drafts are written)
    python3 scripts/airtable.py pending-changes     # records whose "Why I changed it" has no rule change yet
    python3 scripts/airtable.py propose change.json # create one Rule Changes row linked to its source records
    python3 scripts/airtable.py open-changes        # Rule Changes with status Open
    python3 scripts/airtable.py set-change recXXX Accepted [commit-url]   # only when Hayden says so

There is deliberately no command to edit or delete a request record.
"""

import json
import re
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from airtable_api import AirtableError, Client
from lists import group_of, load_lists
from schema import REQUESTS, RULE_CHANGES, RUNS, requests_fields

BACKFILL_LAST_ID = 7  # TS-0007 is the last row backfilled into the Google Sheet request log
TS_ID = re.compile(r"^TS-(\d{4,})$")
SLACK_LINK = re.compile(r"^https://[a-z0-9-]+\.slack\.com/archives/[A-Z0-9]+/p\d+")
EASTERN = ZoneInfo("America/New_York")
FIRST_RUN_DAYS = 7  # nothing logged at all: read the last week
WAIT_DAYS = 2  # the newest day a run reads is the day before yesterday
REQUIRED = ["Summary", "Message", "Type", "Slack link", "Slack thread", "Message time", "Claude notes", "Original draft"]


def next_ts_number(ids):
    highest = BACKFILL_LAST_ID
    for value in ids:
        m = TS_ID.match(value or "")
        if m:
            highest = max(highest, int(m.group(1)))
    return highest + 1


def eastern_day(timestamp):
    """The Eastern calendar day of an Airtable timestamp like 2026-10-21T23:56:22.000Z."""
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(EASTERN).date()


def scan_window(today, last_covered_to=None, latest_message_time=None):
    """The Slack days a run reads: whole Eastern days, from the day after the last run's
    last day up to the day before yesterday. The nightly run fires just after midnight, so
    every ask has had at least one full working day for a reply or fix to show up in its
    thread. Returns (from, to), or None if nothing is due.

    Before any run is logged, start on the day of the latest logged message (re-reading
    that day is safe because of dedupe), or a week back if nothing is logged at all."""
    to = today - timedelta(days=WAIT_DAYS)
    if last_covered_to:
        start = last_covered_to + timedelta(days=1)
    elif latest_message_time:
        start = eastern_day(latest_message_time)
    else:
        start = today - timedelta(days=FIRST_RUN_DAYS)
    return (start, to) if start <= to else None


RUN_COUNTS = ("Drafts created", "Already logged", "Personal skipped", "Rule changes logged")


def validate_run(run, window):
    """Returns a list of problems. A run may only log exactly the Slack days that were due."""
    if window is None:
        return ["no Slack days were due, so there is no run to log"]
    problems = []
    for key, day in (("Covered from", window[0]), ("Covered to", window[1])):
        if run.get(key) != day.isoformat():
            problems.append(f"{key} must be {day.isoformat()}")
    for key in RUN_COUNTS:
        value = run.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            problems.append(f"{key} must be a whole number")
    problems += [f"unknown field {k!r}" for k in sorted(set(run) - {"Covered from", "Covered to", *RUN_COUNTS})]
    return problems


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
    if "Scrap" in draft and not isinstance(draft["Scrap"], bool):
        problems.append("Scrap must be true or false")
    if bool(draft.get("Scrap")) != bool(draft.get("Scrap reason")):
        problems.append("Scrap and Scrap reason must both be filled or both blank")
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


def today_eastern():
    return datetime.now(EASTERN).date()


def latest_message_before(rows, today):
    """Latest Message time among records created before today, so a first run's own drafts
    can't move its window between `logged` and `finish-run`."""
    times = [r["fields"]["Message time"] for r in rows
             if r["fields"].get("Message time") and eastern_day(r["createdTime"]) < today]
    return max(times) if times else None


def current_window(client, today):
    runs = client.list_records(RUNS, fields=["Covered to"])
    covered = sorted(r["fields"]["Covered to"] for r in runs if r["fields"].get("Covered to"))
    last = date.fromisoformat(covered[-1]) if covered else None
    rows = client.list_records(REQUESTS, fields=["Message time"])
    return scan_window(today, last, latest_message_before(rows, today))


def cmd_logged(client):
    rows = client.list_records(REQUESTS, fields=["Slack link", "Slack thread", "Request ID"])
    f = [r["fields"] for r in rows]
    window = current_window(client, today_eastern())
    print(json.dumps({
        "read_slack_from": window[0].isoformat() if window else None,
        "read_slack_to": window[1].isoformat() if window else None,
        "nothing_due": window is None,
        "slack_links": sorted({x["Slack link"] for x in f if x.get("Slack link")}),
        "slack_threads": sorted({x["Slack thread"] for x in f if x.get("Slack thread")}),
        "next_request_id": f"TS-{next_ts_number(x.get('Request ID') for x in f):04d}",
    }, indent=2))


def cmd_finish_run(client, path):
    run = json.load(open(path, encoding="utf-8"))
    today = today_eastern()
    problems = validate_run(run, current_window(client, today))
    if problems:
        print("Run not logged. Fix these first:\n" + "\n".join(problems), file=sys.stderr)
        return 1
    client.create_records(RUNS, [dict(run, Run=today.isoformat())])
    print(f"logged run {today.isoformat()} (Slack {run['Covered from']} to {run['Covered to']})")
    return 0


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
        elif cmd == "finish-run" and len(args) == 1:
            return cmd_finish_run(client, args[0])
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
