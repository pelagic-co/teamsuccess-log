"""Looks up a person's role on a client from PelOS (Engagements table). Read only.

    python3 scripts/pelos.py role "Rodri Leon" "Rosy Soil" 2026-10-19   # -> Tactical operator

Needs PELOS_TOKEN: a read-only Airtable token (data.records:read) for the PelOS base only.
"""

import json
import re
import sys
import unicodedata

from airtable_api import AirtableError, Client

PELOS_BASE = "appZ0oNZdr7yZNEb7"
ENGAGEMENTS = "tblecxB4fPyecKUp9"
ROLE_FIELDS = {"Client Management Lead": "CML", "Senior Operator": "Senior operator",
               "Tactical Operator(s)": "Tactical operator"}
SENIORITY = ["CML", "Senior operator", "Tactical operator"]  # several roles on one client: the first wins


def _plain(text):
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    return text.lower()


def client_key(name):
    """'RosySoil 5.0' and 'Rosy Soil' -> 'rosysoil'. Drops the engagement's version number."""
    name = re.sub(r"\s+\d+(\.\d+)*\s*$", "", _plain(name).strip())
    return re.sub(r"[^a-z0-9]", "", name)


def same_client(a, b):
    """Equal keys, or one starts with the other ('toon' / 'toonhealth', 'zoid' / 'zoidequip')."""
    a, b = client_key(a), client_key(b)
    if not a or not b:
        return False
    short, long_ = sorted((a, b), key=len)
    return len(short) >= 4 and long_.startswith(short)


def same_person(asked, listed):
    """'Rodri Leon' ~ 'Rodrigo León', 'Ciara Sophia Rudas' ~ 'Ciara Rudas'.
    A one-word name ('Lina') matches on first name only."""
    a, b = _plain(asked).split(), _plain(listed).split()
    if not a or not b:
        return False
    first = a[0].startswith(b[0]) or b[0].startswith(a[0])
    if len(a) == 1 or len(b) == 1:
        return first and min(len(a[0]), len(b[0])) >= 3
    return first and a[-1] == b[-1]


def roster(records):
    """Engagement records (REST shape: {'fields': {...}}) -> one row per person per role."""
    rows = []
    for rec in records:
        f = rec["fields"]
        name = (f.get("Name") or "").strip()
        for field, role in ROLE_FIELDS.items():
            for person in f.get(field) or []:
                rows.append({"client": name.split(",")[0].strip(), "person": person.get("name", ""), "role": role,
                             "start": f.get("Engagement Start Date"), "end": f.get("Engagement End Date"),
                             "status": f.get("Status (Dynamic)")})
    return rows


def role_on(rows, person, client, day):
    """The person's role on that client on that day (ISO date). Returns (role, why).
    role is None when it can't be found; why says what was missing."""
    if not client:
        return None, "no client on the record"
    on_client = [r for r in rows if same_client(client, r["client"])]
    if not on_client:
        return None, f"no PelOS engagement for client {client!r}"
    theirs = [r for r in on_client if same_person(person, r["person"])]
    if not theirs:
        return None, f"{person} is not staffed on {client} in PelOS"
    if len({r["person"] for r in theirs}) > 1:
        return None, f"{person!r} matches several people on {client}: " + ", ".join(sorted({r["person"] for r in theirs}))
    dated = [r for r in theirs if r["start"] and r["start"] <= day and (not r["end"] or r["end"] >= day)]
    pool = dated or [r for r in theirs if r["status"] == "ACTIVE"]
    if not pool:
        return None, f"{person} has no {client} engagement covering {day}"
    roles = sorted({r["role"] for r in pool}, key=SENIORITY.index)
    why = "" if len(roles) == 1 else f"also {', '.join(roles[1:])} on {client}"
    return roles[0], why


def fetch_rows():
    import os
    token = os.environ.get("PELOS_TOKEN", "").strip()
    if not token:
        raise AirtableError("PELOS_TOKEN is not set. Add a read-only PelOS token to the environment's secrets.")
    client = Client(token=token, base_id=PELOS_BASE)
    fields = ["Name", "Engagement Start Date", "Engagement End Date", "Status (Dynamic)", *ROLE_FIELDS]
    return roster(client.list_records(ENGAGEMENTS, fields=fields))


def main(argv):
    if len(argv) != 4 or argv[0] != "role":
        print(__doc__)
        return 2
    try:
        role, why = role_on(fetch_rows(), *argv[1:])
    except AirtableError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(json.dumps({"role": role, "why": why}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
