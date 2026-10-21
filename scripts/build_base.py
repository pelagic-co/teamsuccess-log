"""Builds the Team Success Log tables inside an existing (empty) Airtable base.

Safe to run again: it only adds what is missing and reports any drift. It never deletes
or renames anything Hayden made, apart from naming the one link field it creates.

    AIRTABLE_TOKEN=... AIRTABLE_BASE_ID=app... python3 scripts/build_base.py
"""

import sys

from airtable_api import AirtableError, Client
from lists import load_lists
from schema import REQUESTS, RULE_CHANGES, checks_formula, link_field, tables

REVERSE_LINK_NAME = "Rule changes"


def build(client):
    wanted = tables()
    existing = {t["name"]: t for t in client.tables()}
    report = []

    for name, fields in wanted.items():
        if name not in existing:
            client.create_table(name, fields)
            report.append(f"created table {name} ({len(fields)} fields)")
            continue
        have = {f["name"]: f for f in existing[name]["fields"]}
        for field in fields:
            if field["name"] not in have:
                client.create_field(existing[name]["id"], field)
                report.append(f"added field {name}.{field['name']}")
            elif have[field["name"]]["type"] != field["type"]:
                report.append(f"DRIFT {name}.{field['name']} is {have[field['name']]['type']}, expected {field['type']}")
            elif field["type"] in ("singleSelect", "multipleSelects"):
                got = {c["name"] for c in have[field["name"]]["options"]["choices"]}
                missing = [c["name"] for c in field["options"]["choices"] if c["name"] not in got]
                if missing:
                    report.append(f"note {name}.{field['name']} lacks choices {missing}; "
                                  "they are added automatically the first time a record uses them")

    existing = {t["name"]: t for t in client.tables()}
    rc, rq = existing[RULE_CHANGES], existing[REQUESTS]
    if not any(f["name"] == "Source records" for f in rc["fields"]):
        field = dict(link_field(), options={"linkedTableId": rq["id"]})
        client.create_field(rc["id"], field)
        report.append("added link Rule Changes.Source records")
        rq = {t["name"]: t for t in client.tables()}[REQUESTS]
        reverse = [f for f in rq["fields"] if f["type"] == "multipleRecordLinks"
                   and f.get("options", {}).get("linkedTableId") == rc["id"]]
        if len(reverse) != 1:
            raise AirtableError("could not find the reverse link field on Requests")
        if reverse[0]["name"] != REVERSE_LINK_NAME:
            client.rename_field(rq["id"], reverse[0]["id"], REVERSE_LINK_NAME)
            report.append(f"named Requests.{REVERSE_LINK_NAME}")

    return report


def main():
    try:
        report = build(Client())
    except AirtableError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print("\n".join(report) or "nothing to do; base already matches")
    print("\nAdd by hand (Airtable's API can't create these): a formula field named Checks on Requests:")
    print(checks_formula(load_lists()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
