import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from airtable import next_ts_number, validate_draft  # noqa: E402
from lists import group_of, load_lists, resource_required_values  # noqa: E402
from schema import checks_formula, requests_fields, tables  # noqa: E402

LISTS = load_lists()
LINK = "https://pelagicworkspace.slack.com/archives/C0B00JQJLHZ/p1792092664499889"


def draft(**over):
    d = {
        "Summary": "Can you add Manukora to my hours tracker?",
        "Type": "TS",
        "Request ID": "TS-0008",
        "Source": "Team Support Slack",
        "Resource group": "Thing",
        "Resource required": "Access",
        "Root cause": "Insufficient resource",
        "Slack link": LINK,
        "Slack thread": LINK,
        "Message time": "2026-10-13T17:37:09-04:00",
        "Claude notes": "Hours-tracker access ask.",
        "Original draft": "Type: TS",
    }
    d.update(over)
    return d


class ListsMatchRequestModel(unittest.TestCase):
    """The lists must match the Brain's request model v1.4 / resource required v1.2."""

    def test_resource_required_counts(self):
        self.assertEqual(len(LISTS["resource_required"]["Thing"]), 6)
        self.assertEqual(len(LISTS["resource_required"]["Person"]), 5)

    def test_each_resource_in_exactly_one_group(self):
        values = resource_required_values(LISTS)
        self.assertEqual(len(values), len(set(values)))
        self.assertEqual(group_of(LISTS, "Information"), "Thing")
        self.assertEqual(group_of(LISTS, "Direction / clarity"), "Person")

    def test_four_root_causes_six_responses(self):
        self.assertEqual(len(LISTS["root_cause"]), 4)
        self.assertEqual(len(LISTS["response"]), 6)

    def test_personal_clients(self):
        self.assertEqual(LISTS["personal_clients"], ["DairyPill", "Little Saints", "Fronen"])


class Schema(unittest.TestCase):
    def test_every_request_model_field_present(self):
        names = {f["name"] for f in requests_fields(LISTS)}
        model = ["Request ID", "Date received", "Intake type", "Source", "Requester", "Requester party",
                 "Needs help", "Needs help party", "Client", "Summary", "Urgency", "Resource group",
                 "Resource required", "Root cause", "Response", "Routed to", "Unblocked date", "Lasting fix",
                 "Lasting fix status", "Resource link", "Workflow maturity", "Related requests",
                 "TS time spent", "Notes"]
        extra = ["Type", "Slack link", "Status", "Approved", "Why I changed it"]
        self.assertEqual([n for n in model + extra if n not in names], [])

    def test_no_duplicate_field_names(self):
        for name, fields in tables().items():
            names = [f["name"] for f in fields]
            self.assertEqual(len(names), len(set(names)), name)

    def test_primary_fields_are_text(self):
        for fields in tables().values():
            self.assertEqual(fields[0]["type"], "singleLineText")

    def test_checks_formula_lists_values(self):
        f = checks_formula(LISTS)
        self.assertIn("Tool|Training|Information|Process|Workflow|Access", f)
        self.assertNotIn("{thing}", f)


class Validation(unittest.TestCase):
    def test_good_draft_passes(self):
        self.assertEqual(validate_draft(draft(), LISTS, set()), [])

    def test_approved_is_refused(self):
        self.assertIn("drafts must not set Approved", validate_draft(draft(Approved=True), LISTS, set()))

    def test_group_mismatch(self):
        p = validate_draft(draft(**{"Resource group": "Person"}), LISTS, set())
        self.assertIn("Resource group does not match Resource required", p)

    def test_needs_help_pair(self):
        p = validate_draft(draft(**{"Needs help": "Natasha"}), LISTS, set())
        self.assertIn("Needs help and Needs help party must both be filled or both blank", p)

    def test_unknown_value(self):
        p = validate_draft(draft(**{"Root cause": "DK referral"}), LISTS, set())
        self.assertTrue(any("not in the list" in x for x in p))

    def test_already_logged(self):
        self.assertIn("already logged (Slack link)", validate_draft(draft(), LISTS, {LINK}))

    def test_personal_has_no_request_id(self):
        p = validate_draft(draft(Type="Personal"), LISTS, set())
        self.assertIn("Personal drafts get no Request ID", p)
        self.assertEqual(validate_draft(draft(Type="Personal", **{"Request ID": None}), LISTS, set()), [])

    def test_ts_needs_request_id(self):
        self.assertIn("TS draft needs a Request ID like TS-0008",
                      validate_draft(draft(**{"Request ID": None}), LISTS, set()))

    def test_unknown_field(self):
        self.assertIn("unknown field 'Priority'", validate_draft(draft(Priority="High"), LISTS, set()))

    def test_bad_slack_link(self):
        p = validate_draft(draft(**{"Slack link": "https://example.com"}), LISTS, set())
        self.assertIn("Slack link is not a Slack permalink", p)


class RequestIds(unittest.TestCase):
    def test_starts_after_sheet_backfill(self):
        self.assertEqual(next_ts_number([]), 8)

    def test_continues_after_highest(self):
        self.assertEqual(next_ts_number(["TS-0008", "TS-0012", None, "junk"]), 13)


if __name__ == "__main__":
    unittest.main()
