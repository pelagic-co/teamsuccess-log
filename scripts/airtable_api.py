"""Minimal Airtable Web API client (standard library only). Raises on any error."""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.airtable.com/v0"


class AirtableError(RuntimeError):
    pass


def _env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise AirtableError(f"{name} is not set. Add it to the environment's secrets.")
    return value


class Client:
    def __init__(self, token=None, base_id=None):
        self.token = token or _env("AIRTABLE_TOKEN")
        self.base_id = base_id or _env("AIRTABLE_BASE_ID")

    def request(self, method, path, body=None, query=None):
        url = f"{API}/{path}"
        if query:
            url += "?" + urllib.parse.urlencode(query, doseq=True)
        data = json.dumps(body).encode() if body is not None else None
        for attempt in range(5):
            req = urllib.request.Request(url, data=data, method=method, headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            })
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    return json.loads(resp.read() or b"{}")
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")
                if e.code == 429 and attempt < 4:
                    time.sleep(2 ** attempt)
                    continue
                raise AirtableError(f"{method} {path} failed ({e.code}): {detail}") from None
            except urllib.error.URLError as e:
                raise AirtableError(f"{method} {path} could not reach Airtable: {e.reason}") from None
        raise AirtableError(f"{method} {path} kept hitting the rate limit")

    # Schema
    def tables(self):
        return self.request("GET", f"meta/bases/{self.base_id}/tables")["tables"]

    def create_table(self, name, fields, description=""):
        return self.request("POST", f"meta/bases/{self.base_id}/tables",
                            {"name": name, "description": description, "fields": fields})

    def create_field(self, table_id, field):
        return self.request("POST", f"meta/bases/{self.base_id}/tables/{table_id}/fields", field)

    def rename_field(self, table_id, field_id, name):
        return self.request("PATCH", f"meta/bases/{self.base_id}/tables/{table_id}/fields/{field_id}",
                            {"name": name})

    # Records
    def list_records(self, table, fields=None, formula=None):
        records, offset = [], None
        while True:
            query = {"pageSize": 100}
            if fields:
                query["fields[]"] = fields
            if formula:
                query["filterByFormula"] = formula
            if offset:
                query["offset"] = offset
            page = self.request("GET", f"{self.base_id}/{urllib.parse.quote(table)}", query=query)
            records.extend(page.get("records", []))
            offset = page.get("offset")
            if not offset:
                return records

    def create_records(self, table, rows):
        created = []
        for i in range(0, len(rows), 10):
            batch = [{"fields": r} for r in rows[i:i + 10]]
            out = self.request("POST", f"{self.base_id}/{urllib.parse.quote(table)}",
                               {"records": batch, "typecast": True})
            created.extend(out["records"])
        return created

    def update_records(self, table, updates):
        out = []
        for i in range(0, len(updates), 10):
            batch = [{"id": rid, "fields": f} for rid, f in updates[i:i + 10]]
            out.extend(self.request("PATCH", f"{self.base_id}/{urllib.parse.quote(table)}",
                                    {"records": batch})["records"])
        return out
