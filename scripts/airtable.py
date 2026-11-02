"""What an intake run is allowed to do in Airtable, and nothing more.

    python3 scripts/airtable.py logged              # Slack days to read, Slack links/threads already logged, next TS ID
    python3 scripts/airtable.py create drafts.json  # create draft Requests (validated first; all or nothing)
    python3 scripts/airtable.py finish-run run.json # log the run in Runs (only after its drafts are written)
    python3 scripts/airtable.py party "Name" "Client" 2026-10-28   # Requester party, with fallbacks
    python3 scripts/airtable.py open-requests       # requests not yet closed, for the follow-up
    python3 scripts/airtable.py follow-up followups.json   # add dated notes + update follow-up fields only
    python3 scripts/airtable.py pending-changes     # requests whose labels Hayden changed, no rule change yet
    python3 scripts/airtable.py propose change.json # create one Rule Changes row linked to its source records
    python3 scripts/airtable.py open-changes        # Rule Changes with status Open
    python3 scripts/airtable.py set-change recXXX Accepted [commit-url]   # only when Hayden says so
    python3 scripts/airtable.py topic-suggestions   # suggested topics shared by 3+ Other requests, not yet proposed
    python3 scripts/airtable.py update updates.json # overwrite fields on existing Requests (only when Hayden asks)

`update` is for edits Hayden asks for in a conversation (e.g. back-filling a new field);
the nightly run never uses it. The nightly run edits existing requests only through
`follow-up`. Neither ever sets Approved. There is deliberately no command to delete a
request record.
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
REQUIRED = ["Summary", "Message", "Type", "Topic", "Requester party", "Root cause", "Slack link", "Slack thread",
            "Message time", "Claude notes", "Original draft"]
SCRAP_REASON = re.compile(r"^\s*Scrap reason:\s*\S", re.MULTILINE | re.IGNORECASE)


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


RUN_COUNTS = ("Drafts created", "Already logged", "Personal skipped", "Rule changes logged", "Followed up", "Closed")


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
    required, groups = draft.get("Resource required") or [], draft.get("Resource group") or []
    if isinstance(required, list) and isinstance(groups, list):
        try:
            if set(groups) != {group_of(lists, r) for r in required}:
                problems.append("Resource group does not match Resource required")
        except ValueError as e:
            problems.append(str(e))
    if bool(draft.get("Needs help")) != bool(draft.get("Needs help party")):
        problems.append("Needs help and Needs help party must both be filled or both blank")
    if "Scrap" in draft and not isinstance(draft["Scrap"], bool):
        problems.append("Scrap must be true or false")
    topics = draft.get("Topic") or []
    if isinstance(topics, list) and "Other" in topics and len(topics) > 1:
        problems.append("Topic Other must be on its own")
    if topics == ["Other"]:
        suggested = suggested_topic(draft.get("Claude notes"))
        if not suggested:
            problems.append("Topic Other needs a 'Suggested topic: <name>' line in Claude notes")
        elif suggested.lower() in {t.lower() for t in lists["topic"]}:
            problems.append(f"suggested topic {suggested!r} is already in the list; use it instead of Other")
    if draft.get("Scrap") and not SCRAP_REASON.search(draft.get("Claude notes") or ""):
        problems.append("Scrap needs a 'Scrap reason: <reason>' line in Claude notes")
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


def field_type_drift(live_fields, lists):
    """Fields whose type in Airtable differs from schema.py; writing drafts then would fail."""
    live = {f["name"]: f["type"] for f in live_fields}
    return [f"{f['name']} is {live[f['name']]} in Airtable, expected {f['type']}"
            for f in requests_fields(lists) if f["name"] in live and live[f["name"]] != f["type"]]


def cmd_create(client, path):
    lists = load_lists()
    drafts = json.load(open(path, encoding="utf-8"))
    live = {t["name"]: t for t in client.tables()}[REQUESTS]["fields"]
    drift = field_type_drift(live, lists)
    if drift:
        print("Nothing written. Change these field types in Airtable first:\n" + "\n".join(drift), file=sys.stderr)
        return 1
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


SUGGESTED_TOPIC = re.compile(r"^\s*Suggested topic:\s*(.+?)\s*$", re.MULTILINE | re.IGNORECASE)
PROPOSED_TOPIC = re.compile(r'^Add topic "(.+?)"', re.IGNORECASE)
TOPIC_THRESHOLD = 3  # Other requests sharing a suggestion before it's proposed (Hayden, 2026-11-02)


def suggested_topic(notes):
    m = SUGGESTED_TOPIC.search(notes or "")
    return m.group(1).strip(" .\"'") if m else None


def topic_suggestions(rows, proposed_rules, lists, threshold=TOPIC_THRESHOLD):
    """Suggested topics ready to propose: at least `threshold` requests tagged only Other
    share the suggestion (case-insensitive), it isn't already a topic, and no Rule Changes
    row has proposed it before (whatever its status). Returns
    [{"topic", "count", "records": [record ids], "request_ids": [...]}], biggest first."""
    taken = {t.lower() for t in lists["topic"]}
    for rule in proposed_rules:
        m = PROPOSED_TOPIC.match(rule or "")
        if m:
            taken.add(m.group(1).strip().lower())
    groups = {}
    for r in rows:
        f = r["fields"]
        if (f.get("Topic") or []) != ["Other"]:
            continue
        name = suggested_topic(f.get("Claude notes"))
        if not name or name.lower() in taken:
            continue
        g = groups.setdefault(name.lower(), {"topic": name, "records": [], "request_ids": []})
        g["records"].append(r["id"])
        g["request_ids"].append(f.get("Request ID"))
    ready = [dict(g, count=len(g["records"])) for g in groups.values() if len(g["records"]) >= threshold]
    return sorted(ready, key=lambda g: (-g["count"], g["topic"].lower()))


def cmd_topic_suggestions(client):
    rows = client.list_records(REQUESTS, fields=["Request ID", "Topic", "Claude notes"])
    rules = [r["fields"].get("Proposed rule") for r in client.list_records(RULE_CHANGES, fields=["Proposed rule"])]
    print(json.dumps(topic_suggestions(rows, rules, load_lists()), indent=2))


HAYDEN_ONLY = ("Approved", "Rule changes")


def validate_update(fields, lists):
    """Returns a list of problems with one record's overwrite. Empty means it may be written."""
    problems = []
    specs = {f["name"]: f for f in requests_fields(lists)}
    if not fields:
        return ["no fields to change"]
    for name, value in fields.items():
        if name in HAYDEN_ONLY:
            problems.append(f"{name} is Hayden's; Claude never sets it")
            continue
        spec = specs.get(name)
        if not spec:
            problems.append(f"unknown field {name!r}")
            continue
        if value in (None, "", []):
            continue
        if spec["type"] == "singleSelect":
            if value not in [c["name"] for c in spec["options"]["choices"]]:
                problems.append(f"{name}={value!r} is not in the list")
        if spec["type"] == "multipleSelects":
            allowed = [c["name"] for c in spec["options"]["choices"]]
            if not isinstance(value, list):
                problems.append(f"{name} must be a list")
            else:
                problems += [f"{name}={v!r} is not in the list" for v in value if v not in allowed]
    topics = fields.get("Topic") or []
    if isinstance(topics, list) and "Other" in topics and len(topics) > 1:
        problems.append("Topic Other must be on its own")
    return problems


def cmd_update(client, path):
    """updates.json: [{"Request ID": "TS-0008", "fields": {"Topic": ["Ops Hub"]}}, ...]. All or nothing."""
    lists = load_lists()
    updates = json.load(open(path, encoding="utf-8"))
    rows = client.list_records(REQUESTS, fields=["Request ID"])
    ids = {}
    for r in rows:
        rid = r["fields"].get("Request ID")
        if rid:
            ids.setdefault(rid, []).append(r["id"])
    errors, writes, seen = [], [], set()
    for u in updates:
        rid = u.get("Request ID")
        problems = validate_update(u.get("fields") or {}, lists)
        if rid in seen:
            problems.append("listed twice")
        seen.add(rid)
        if len(ids.get(rid, [])) != 1:
            problems.append(f"{len(ids.get(rid, []))} records have this Request ID (need exactly 1)")
        if problems:
            errors.append(f"{rid}: " + "; ".join(problems))
        else:
            writes.append((ids[rid][0], u["fields"]))
    if errors:
        print("Nothing written. Fix these first:\n" + "\n".join(errors), file=sys.stderr)
        return 1
    client.update_records(REQUESTS, writes, typecast=True)  # values validated above
    print(f"updated {len(writes)} record(s)")
    return 0


# Labels that record Claude's classification call. Follow-up fields (Status, Response, ...)
# change as the work happens, so they never count as Hayden correcting Claude.
CLASSIFICATION = ("Type", "Topic", "Intake type", "Source", "Requester party", "Needs help", "Needs help party",
                  "Client", "Urgency", "Resource group", "Resource required", "Root cause", "Scrap")
LOOP_START = "2026-11-03"  # requests drafted earlier predate Original-draft comparison (rules v1.13)


def _plain_value(value):
    if isinstance(value, bool):
        return "true" if value else ""
    if isinstance(value, list):
        return ", ".join(sorted(str(v).strip() for v in value))
    return str(value or "").strip()


def parse_original_draft(text):
    """'Field: value' lines -> {field: value}. Only classification fields are kept."""
    out = {}
    for line in (text or "").splitlines():
        name, sep, value = line.partition(":")
        if sep and name.strip() in CLASSIFICATION:
            out[name.strip()] = value.strip()
    return out


def label_changes(fields):
    """[(field, Claude's value, current value)] for classification labels in Original draft
    that no longer match. Multi-value labels compare as sets; case and order don't matter."""
    changes = []
    for name, drafted in parse_original_draft(fields.get("Original draft")).items():
        now = fields.get(name)
        if name == "Scrap":
            same = (drafted.lower() in ("true", "yes", "ticked", "checked")) == bool(now)
        elif isinstance(now, list):
            same = {v.strip().lower() for v in drafted.split(",") if v.strip()} == {v.lower() for v in now}
        else:
            same = drafted.lower() == _plain_value(now).lower()
        if not same:
            changes.append((name, drafted, _plain_value(now)))
    return changes


def pending_changes(rows, start=LOOP_START):
    out = []
    for r in rows:
        f = r["fields"]
        if f.get("Rule changes") or eastern_day(r["createdTime"]).isoformat() < start:
            continue
        changes = label_changes(f)
        if changes:
            out.append({"id": r["id"], "Request ID": f.get("Request ID"), "Summary": f.get("Summary"),
                        "Message": f.get("Message"), "Claude notes": f.get("Claude notes"),
                        "changes": [{"field": n, "claude": a, "now": b} for n, a, b in changes]})
    return out


def cmd_pending_changes(client):
    rows = client.list_records(REQUESTS)
    print(json.dumps(pending_changes(rows), indent=2, default=str))


CLOSED = ("Done", "Not an ask")
FOLLOW_UP_FIELDS = ("Status", "Unblocked date", "Response", "Routed to", "Resource link", "Related requests")


def is_closed(fields):
    return fields.get("Status") in CLOSED


def validate_follow_up(entry, current, lists):
    """Problems with one follow-up entry against the record as it is now."""
    problems = []
    fields, note = entry.get("fields") or {}, (entry.get("note") or "").strip()
    if not note:
        problems.append("needs a note saying what happened")
    if "\n" in note:
        problems.append("note must be one line")
    if is_closed(current):
        problems.append(f"already closed ({current['Status']}); a recurrence is a new request")
    for name in fields:
        if name not in FOLLOW_UP_FIELDS:
            problems.append(f"{name} can't be changed by a follow-up")
    specs = {f["name"]: f for f in requests_fields(lists)}
    for name, value in fields.items():
        spec = specs.get(name)
        if name not in FOLLOW_UP_FIELDS or not spec or value in (None, "", []):
            continue
        choices = [c["name"] for c in spec.get("options", {}).get("choices", [])]
        if spec["type"] == "singleSelect" and value not in choices:
            problems.append(f"{name}={value!r} is not in the list")
        if spec["type"] == "multipleSelects":
            if not isinstance(value, list):
                problems.append(f"{name} must be a list")
            else:
                problems += [f"{name}={v!r} is not in the list" for v in value if v not in choices]
        if spec["type"] == "date":
            try:
                date.fromisoformat(value)
            except (TypeError, ValueError):
                problems.append(f"{name} must be a date like 2026-11-03")
    if fields.get("Status") == "Done" and not (fields.get("Unblocked date") or current.get("Unblocked date")):
        problems.append("Done needs an Unblocked date")
    return problems


def add_note(existing, note, day):
    line = f"{day.isoformat()}: {note.strip()}"
    return f"{existing.rstrip()}\n{line}" if (existing or "").strip() else line


def cmd_open_requests(client):
    keep = ["Request ID", "Summary", "Requester", "Client", "Status", "Response", "Unblocked date", "Routed to",
            "Resource link", "Notes", "Slack link", "Slack thread", "Message time", "Approved", "Scrap"]
    rows = [r for r in client.list_records(REQUESTS, fields=keep)
            if r["fields"].get("Request ID") and not is_closed(r["fields"])]
    rows.sort(key=lambda r: r["fields"]["Request ID"])
    print(json.dumps([{"id": r["id"], **r["fields"]} for r in rows], indent=2, default=str))


def cmd_follow_up(client, path):
    """followups.json: [{"Request ID": "TS-0041", "note": "...", "fields": {"Status": "Done", ...}}]. All or nothing."""
    lists = load_lists()
    entries = json.load(open(path, encoding="utf-8"))
    rows = client.list_records(REQUESTS, fields=["Request ID", "Status", "Unblocked date", "Notes"])
    by_id = {}
    for r in rows:
        if r["fields"].get("Request ID"):
            by_id.setdefault(r["fields"]["Request ID"], []).append(r)
    today, errors, writes, seen = today_eastern(), [], [], set()
    for e in entries:
        rid = e.get("Request ID")
        matches = by_id.get(rid, [])
        problems = [] if len(matches) == 1 else [f"{len(matches)} records have this Request ID (need exactly 1)"]
        if rid in seen:
            problems.append("listed twice")
        seen.add(rid)
        if not problems:
            problems = validate_follow_up(e, matches[0]["fields"], lists)
        if problems:
            errors.append(f"{rid}: " + "; ".join(problems))
            continue
        fields = dict(e.get("fields") or {})
        fields["Notes"] = add_note(matches[0]["fields"].get("Notes"), e["note"], today)
        writes.append((matches[0]["id"], fields))
    if errors:
        print("Nothing written. Fix these first:\n" + "\n".join(errors), file=sys.stderr)
        return 1
    client.update_records(REQUESTS, writes, typecast=True)  # values validated above
    closed = sum(1 for _, f in writes if f.get("Status") in CLOSED)
    print(f"followed up {len(writes)} request(s), closed {closed}")
    return 0


def cmd_party(client, person, client_name, day):
    import os
    from pelos import fetch_rows, pick_party
    history = [r["fields"] for r in client.list_records(REQUESTS, fields=["Requester", "Requester party"])]
    roster, note = None, ""
    if os.environ.get("PELOS_TOKEN", "").strip():
        roster = fetch_rows()
    else:
        note = "PELOS_TOKEN not set, so PelOS was skipped"
    party, why = pick_party(person, client_name, day, roster, history, load_lists()["party"])
    print(json.dumps({"party": party, "why": "; ".join(x for x in (why, note) if x)}))


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
        elif cmd == "party" and len(args) == 3:
            cmd_party(client, *args)
        elif cmd == "open-requests":
            cmd_open_requests(client)
        elif cmd == "follow-up" and len(args) == 1:
            return cmd_follow_up(client, args[0])
        elif cmd == "topic-suggestions":
            cmd_topic_suggestions(client)
        elif cmd == "update" and len(args) == 1:
            return cmd_update(client, args[0])
        else:
            print(__doc__)
            return 2
    except AirtableError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
