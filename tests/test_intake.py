import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from datetime import date  # noqa: E402

from airtable import (add_note, eastern_day, field_type_drift, label_changes, latest_message_before,  # noqa: E402
                      next_ts_number, pending_changes, scan_window, topic_suggestions, validate_draft,
                      validate_follow_up, validate_run, validate_update)
from pelos import pick_party  # noqa: E402
from build_base import build  # noqa: E402
from lists import group_of, load_lists, resource_required_values  # noqa: E402
from schema import REQUESTS, RULE_CHANGES, checks_formula, requests_fields, tables  # noqa: E402

LISTS = load_lists()
LINK = "https://pelagicworkspace.slack.com/archives/C0B00JQJLHZ/p1792092664499889"


def draft(**over):
    d = {
        "Summary": "Add Manukora to the hours tracker.",
        "Message": "Hey @Hayden can you add Manukora to my hours tracker?",
        "Type": "TS",
        "Topic": ["Hours & Capacity"],
        "Request ID": "TS-0008",
        "Source": "Team Support Slack",
        "Requester party": "Tactical operator",
        "Resource group": ["Thing"],
        "Resource required": ["Access"],
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
        self.assertEqual(len(LISTS["resource_required"]["Person"]), 6)

    def test_each_resource_in_exactly_one_group(self):
        values = resource_required_values(LISTS)
        self.assertEqual(len(values), len(set(values)))
        self.assertEqual(group_of(LISTS, "Information"), "Thing")
        self.assertEqual(group_of(LISTS, "Direction / clarity"), "Person")

    def test_four_root_causes_six_responses(self):
        self.assertEqual(len(LISTS["root_cause"]), 4)
        self.assertEqual(len(LISTS["response"]), 6)

    def test_topics(self):
        self.assertEqual(LISTS["topic"][:3], ["Ops Hub", "Forecasting", "COGS"])
        self.assertEqual(LISTS["topic"][-1], "Other")

    def test_personal_clients(self):
        self.assertEqual(LISTS["personal_clients"], ["DairyPill", "Little Saints", "Fronen"])


class Schema(unittest.TestCase):
    def test_every_request_model_field_present(self):
        names = {f["name"] for f in requests_fields(LISTS)}
        model = ["Request ID", "Date received", "Intake type", "Source", "Requester", "Requester party",
                 "Needs help", "Needs help party", "Client", "Summary", "Urgency", "Resource group",
                 "Resource required", "Root cause", "Response", "Routed to", "Unblocked date",
                 "Resource link", "Related requests", "Notes"]
        extra = ["Type", "Topic", "Message", "Slack link", "Status", "Approved"]
        self.assertEqual([n for n in model + extra if n not in names], [])

    def test_removed_fields_gone(self):
        names = {f["name"] for f in requests_fields(LISTS)}
        removed = ["TS time spent", "Lasting fix", "Lasting fix status", "Workflow maturity", "Why I changed it",
                   "Scrap reason"]
        self.assertEqual([n for n in removed if n in names], [])

    def test_party_list_split_account_team(self):
        self.assertNotIn("Account team", LISTS["party"])
        for p in ("CML", "Senior operator", "Tactical operator", "Services team"):
            self.assertIn(p, LISTS["party"])

    def test_no_duplicate_field_names(self):
        for name, fields in tables().items():
            names = [f["name"] for f in fields]
            self.assertEqual(len(names), len(set(names)), name)

    def test_primary_fields_are_text(self):
        for fields in tables().values():
            self.assertEqual(fields[0]["type"], "singleLineText")

    def test_field_type_drift(self):
        live = [dict(f) for f in requests_fields(LISTS)]
        self.assertEqual(field_type_drift(live, LISTS), [])
        next(f for f in live if f["name"] == "Resource required")["type"] = "singleSelect"
        self.assertEqual(field_type_drift(live, LISTS),
                         ["Resource required is singleSelect in Airtable, expected multipleSelects"])

    def test_message_is_long_text(self):
        fields = {f["name"]: f for f in requests_fields(LISTS)}
        self.assertEqual(fields["Message"]["type"], "multilineText")

    def test_checks_formula_lists_values(self):
        f = checks_formula(LISTS)
        self.assertIn("FIND('Tool', {Resource required}&'')", f)
        self.assertIn("FIND('Analysis', {Resource required}&'')", f)
        self.assertNotIn("{thing_any}", f)
        self.assertNotIn("{person_any}", f)

    def test_checks_formula_finds_are_unambiguous(self):
        # The formula spots a resource by text search, so no value may sit inside another.
        values = resource_required_values(LISTS)
        self.assertEqual([(a, b) for a in values for b in values if a != b and a in b], [])


class Validation(unittest.TestCase):
    def test_good_draft_passes(self):
        self.assertEqual(validate_draft(draft(), LISTS, set()), [])

    def test_message_is_required(self):
        self.assertIn("missing Message", validate_draft(draft(Message=""), LISTS, set()))

    def test_topic_is_required(self):
        self.assertIn("missing Topic", validate_draft(draft(Topic=[]), LISTS, set()))

    def test_topic_is_a_list_from_the_list(self):
        self.assertIn("Topic must be a list", validate_draft(draft(Topic="Ops Hub"), LISTS, set()))
        p = validate_draft(draft(Topic=["Inventory"]), LISTS, set())
        self.assertIn("Topic='Inventory' is not in the list", p)

    def test_topic_can_have_several(self):
        self.assertEqual(validate_draft(draft(Topic=["Ops Hub", "Forecasting"]), LISTS, set()), [])

    def test_topic_other_stands_alone(self):
        p = validate_draft(draft(Topic=["Other", "Ops Hub"]), LISTS, set())
        self.assertIn("Topic Other must be on its own", p)

    def test_scrap_needs_a_reason_in_notes(self):
        p = validate_draft(draft(Scrap=True), LISTS, set())
        self.assertIn("Scrap needs a 'Scrap reason: <reason>' line in Claude notes", p)
        ok = draft(Scrap=True, **{"Claude notes": "Hours add.\nScrap reason: Hours tracking / client add"})
        self.assertEqual(validate_draft(ok, LISTS, set()), [])

    def test_scrap_reason_field_is_gone(self):
        p = validate_draft(draft(**{"Scrap reason": "Boring"}), LISTS, set())
        self.assertIn("unknown field 'Scrap reason'", p)

    def test_party_and_root_cause_required(self):
        self.assertIn("missing Requester party", validate_draft(draft(**{"Requester party": None}), LISTS, set()))
        self.assertIn("missing Root cause", validate_draft(draft(**{"Root cause": None}), LISTS, set()))

    def test_account_team_retired(self):
        p = validate_draft(draft(**{"Requester party": "Account team"}), LISTS, set())
        self.assertIn("Requester party='Account team' is not in the list", p)

    def test_approved_is_refused(self):
        self.assertIn("drafts must not set Approved", validate_draft(draft(Approved=True), LISTS, set()))

    def test_group_mismatch(self):
        p = validate_draft(draft(**{"Resource group": ["Person"]}), LISTS, set())
        self.assertIn("Resource group does not match Resource required", p)

    def test_two_resources_need_both_groups(self):
        two = {"Resource required": ["Information", "Capacity / hours"]}
        self.assertIn("Resource group does not match Resource required",
                      validate_draft(draft(**two, **{"Resource group": ["Thing"]}), LISTS, set()))
        self.assertEqual(validate_draft(draft(**two, **{"Resource group": ["Thing", "Person"]}), LISTS, set()), [])

    def test_group_without_resource(self):
        p = validate_draft(draft(**{"Resource required": None}), LISTS, set())
        self.assertIn("Resource group does not match Resource required", p)

    def test_resources_must_be_a_list(self):
        p = validate_draft(draft(**{"Resource required": "Access"}), LISTS, set())
        self.assertIn("Resource required must be a list", p)

    def test_needs_help_pair(self):
        p = validate_draft(draft(**{"Needs help": "Natasha"}), LISTS, set())
        self.assertIn("Needs help and Needs help party must both be filled or both blank", p)

    def test_unknown_value(self):
        p = validate_draft(draft(**{"Root cause": "DK referral"}), LISTS, set())
        self.assertTrue(any("not in the list" in x for x in p))

    def test_already_logged(self):
        self.assertIn("already logged (Slack link)", validate_draft(draft(), LISTS, {LINK}))

    def test_personal_is_never_written(self):
        for d in (draft(Type="Personal"), draft(Type="Personal", **{"Request ID": None})):
            self.assertIn("Personal asks are not logged in this base; list them in the run summary",
                          validate_draft(d, LISTS, set()))

    def test_personal_still_a_choice_for_hayden(self):
        self.assertIn("Personal", LISTS["type"])

    def test_ts_needs_request_id(self):
        self.assertIn("TS draft needs a Request ID like TS-0008",
                      validate_draft(draft(**{"Request ID": None}), LISTS, set()))

    def test_unknown_field(self):
        self.assertIn("unknown field 'Priority'", validate_draft(draft(Priority="High"), LISTS, set()))

    def test_bad_slack_link(self):
        p = validate_draft(draft(**{"Slack link": "https://example.com"}), LISTS, set())
        self.assertIn("Slack link is not a Slack permalink", p)


class FakeBase:
    """An already-built base, before the Message field existed and with the old Summary description."""

    def __init__(self):
        requests = [dict(f, id=f"fld{i}") for i, f in enumerate(requests_fields(LISTS)) if f["name"] != "Message"]
        requests.append({"id": "fldLink", "name": "Rule changes", "type": "multipleRecordLinks",
                         "options": {"linkedTableId": "tblRC"}})
        summary = next(f for f in requests if f["name"] == "Summary")
        summary["description"] = "Field 7. One line, in the requester's words."
        rule_changes = [dict(f, id=f"fldR{i}") for i, f in enumerate(tables()[RULE_CHANGES])]
        rule_changes.append({"id": "fldSrc", "name": "Source records", "type": "multipleRecordLinks"})
        self._tables = [{"id": "tblRQ", "name": REQUESTS, "fields": requests},
                        {"id": "tblRC", "name": RULE_CHANGES, "fields": rule_changes}]
        self.calls = []

    def tables(self):
        return self._tables

    def create_field(self, table_id, field):
        self.calls.append(("create", table_id, field["name"]))

    def describe_field(self, table_id, field_id, description):
        self.calls.append(("describe", table_id, field_id, description))

    def create_table(self, name, fields):
        self.calls.append(("create table", name))


class BuildExistingBase(unittest.TestCase):
    def test_adds_message_and_updates_summary_description(self):
        base = FakeBase()
        report = build(base)
        summary_id = next(f["id"] for f in base._tables[0]["fields"] if f["name"] == "Summary")
        self.assertEqual(base.calls, [
            ("describe", "tblRQ", summary_id, "Field 7. One line, in Claude's words: what is being asked for."),
            ("create", "tblRQ", "Message"),
            ("create table", "Runs"),
        ])
        self.assertIn("added field Requests.Message", report)


MON, TUE, WED, THU, FRI, SAT = (date(2026, 10, d) for d in (19, 20, 21, 22, 23, 24))


class NightlyWindow(unittest.TestCase):
    """A run reads whole Eastern days, from the day after the last run's last day up to the
    day before yesterday. "today" is the day the midnight run fires on."""

    def test_midnight_run_reads_day_before_yesterday(self):
        # Fires 12am Friday: Thursday gets a full working day; it reads Wednesday.
        self.assertEqual(scan_window(FRI, last_covered_to=TUE), (WED, WED))

    def test_missed_runs_become_backlog(self):
        self.assertEqual(scan_window(SAT, last_covered_to=MON), (TUE, THU))

    def test_second_run_same_day_has_nothing_due(self):
        self.assertIsNone(scan_window(FRI, last_covered_to=WED))

    def test_run_after_a_daytime_catch_up_has_nothing_due(self):
        # A catch-up on Friday afternoon read through Thursday; the 12am Saturday run waits.
        self.assertIsNone(scan_window(SAT, last_covered_to=THU))

    def test_first_run_starts_on_day_of_latest_logged_message(self):
        # 23:56 UTC on the 21st is 7:56pm Eastern on the 21st.
        self.assertEqual(eastern_day("2026-10-21T23:56:22.000Z"), WED)
        self.assertEqual(eastern_day("2026-10-22T02:00:00.000Z"), WED)
        self.assertEqual(scan_window(SAT, latest_message_time="2026-10-21T23:56:22.000Z"), (WED, THU))

    def test_nothing_logged_reads_last_week(self):
        self.assertEqual(scan_window(SAT), (date(2026, 10, 17), THU))

    def test_first_runs_own_drafts_do_not_move_its_window(self):
        rows = [
            {"createdTime": "2026-10-22T14:00:00.000Z", "fields": {"Message time": "2026-10-21T23:56:22.000Z"}},
            # Drafted by today's run, for a message on the 22nd: must not count yet.
            {"createdTime": "2026-10-24T04:05:00.000Z", "fields": {"Message time": "2026-10-22T18:00:00.000Z"}},
            {"createdTime": "2026-10-20T14:00:00.000Z", "fields": {}},
        ]
        self.assertEqual(latest_message_before(rows, SAT), "2026-10-21T23:56:22.000Z")
        self.assertIsNone(latest_message_before(rows[1:], SAT))

    def test_runs_win_over_message_times(self):
        self.assertEqual(scan_window(SAT, WED, "2026-10-19T15:00:00.000Z"), (THU, THU))


class RunLog(unittest.TestCase):
    RUN = {"Covered from": "2026-10-22", "Covered to": "2026-10-22", "Drafts created": 3,
           "Already logged": 1, "Personal skipped": 2, "Rule changes logged": 0, "Followed up": 4, "Closed": 1}

    def test_good_run(self):
        self.assertEqual(validate_run(self.RUN, (THU, THU)), [])

    def test_dates_must_match_what_was_due(self):
        p = validate_run(dict(self.RUN, **{"Covered from": "2026-10-21"}), (THU, THU))
        self.assertIn("Covered from must be 2026-10-22", p)

    def test_counts_must_be_whole_numbers(self):
        self.assertIn("Drafts created must be a whole number",
                      validate_run(dict(self.RUN, **{"Drafts created": "3"}), (THU, THU)))

    def test_no_personal_details(self):
        self.assertIn("unknown field 'Personal asks'",
                      validate_run(dict(self.RUN, **{"Personal asks": "DairyPill thing"}), (THU, THU)))

    def test_nothing_due(self):
        self.assertEqual(validate_run(self.RUN, None), ["no Slack days were due, so there is no run to log"])


def other(rid, notes, topic=("Other",)):
    return {"id": f"rec{rid}", "fields": {"Request ID": rid, "Topic": list(topic), "Claude notes": notes}}


class NewTopics(unittest.TestCase):
    def test_other_draft_needs_a_suggestion(self):
        p = validate_draft(draft(Topic=["Other"]), LISTS, set())
        self.assertIn("Topic Other needs a 'Suggested topic: <name>' line in Claude notes", p)
        ok = draft(Topic=["Other"], **{"Claude notes": "Packaging spec ask.\nSuggested topic: Packaging"})
        self.assertEqual(validate_draft(ok, LISTS, set()), [])

    def test_suggestion_already_in_list_refused(self):
        d = draft(Topic=["Other"], **{"Claude notes": "Suggested topic: forecasting"})
        self.assertIn("suggested topic 'forecasting' is already in the list; use it instead of Other",
                      validate_draft(d, LISTS, set()))

    def test_three_matching_others_are_proposed(self):
        rows = [other("TS-0100", "Suggested topic: Packaging"),
                other("TS-0101", "x\nsuggested topic: packaging."),
                other("TS-0102", "Suggested topic: Packaging"),
                other("TS-0103", "Suggested topic: Freight")]
        out = topic_suggestions(rows, [], LISTS)
        self.assertEqual([(g["topic"], g["count"]) for g in out], [("Packaging", 3)])
        self.assertEqual(out[0]["request_ids"], ["TS-0100", "TS-0101", "TS-0102"])

    def test_two_is_not_enough(self):
        rows = [other("TS-0100", "Suggested topic: Packaging"), other("TS-0101", "Suggested topic: Packaging")]
        self.assertEqual(topic_suggestions(rows, [], LISTS), [])

    def test_only_other_alone_counts(self):
        rows = [other(f"TS-01{i:02}", "Suggested topic: Packaging", topic=("Ops Hub",)) for i in range(3)]
        rows += [other("TS-0200", "no suggestion here")]
        self.assertEqual(topic_suggestions(rows, [], LISTS), [])

    def test_never_proposed_twice(self):
        rows = [other(f"TS-01{i:02}", "Suggested topic: Packaging") for i in range(4)]
        self.assertEqual(topic_suggestions(rows, ['Add topic "packaging" to the Topic list.'], LISTS), [])

    def test_existing_topic_not_proposed(self):
        rows = [other(f"TS-01{i:02}", "Suggested topic: COGS") for i in range(3)]
        self.assertEqual(topic_suggestions(rows, [], LISTS), [])


class Overwrite(unittest.TestCase):
    def test_good_update(self):
        self.assertEqual(validate_update({"Topic": ["Ops Hub", "Forecasting"]}, LISTS), [])

    def test_hayden_fields_refused(self):
        for name in ("Approved", "Rule changes"):
            self.assertIn(f"{name} is Hayden's; Claude never sets it", validate_update({name: True}, LISTS))

    def test_values_from_list(self):
        self.assertIn("Topic='Inventory' is not in the list", validate_update({"Topic": ["Inventory"]}, LISTS))
        self.assertIn("Urgency='Soon' is not in the list", validate_update({"Urgency": "Soon"}, LISTS))

    def test_other_alone(self):
        self.assertIn("Topic Other must be on its own", validate_update({"Topic": ["Other", "COGS"]}, LISTS))

    def test_unknown_and_empty(self):
        self.assertIn("unknown field 'Priority'", validate_update({"Priority": "High"}, LISTS))
        self.assertEqual(validate_update({}, LISTS), ["no fields to change"])


ROSTER = [
    {"client": "Rosy Soil 5.0", "person": "Rodrigo León", "role": "Tactical operator", "start": "2026-09-01",
     "end": None, "status": "ACTIVE"},
    {"client": "Nemah 5.0", "person": "Lauren Villaverde", "role": "CML", "start": "2026-10-01",
     "end": "2026-10-29", "status": "CLOSED"},
    {"client": "Toon Health", "person": "Brian Murray", "role": "Senior operator", "start": "2026-11-01",
     "end": None, "status": "ACTIVE"},
]
PARTIES = LISTS["party"]


class RequesterParty(unittest.TestCase):
    def test_internal_is_services_team(self):
        for client in (None, "", "Internal"):
            self.assertEqual(pick_party("Steph Shein", client, "2026-10-28", ROSTER, [], PARTIES), ("Services team", ""))

    def test_pelos_role_on_client(self):
        self.assertEqual(pick_party("Rodri Leon", "Rosy Soil", "2026-10-28", ROSTER, [], PARTIES)[0],
                         "Tactical operator")

    def test_history_fallback_skips_account_team(self):
        hist = [{"Requester": "Brian Murray", "Requester party": "Account team"},
                {"Requester": "Brian Murray", "Requester party": "Tactical operator"}]
        party, why = pick_party("Brian Murray", "Cadence", "2026-10-28", ROSTER, hist, PARTIES)
        self.assertEqual(party, "Tactical operator")
        self.assertTrue(why.startswith("best guess"))

    def test_active_role_fallback(self):
        party, why = pick_party("Brian Murray", "Cadence", "2026-10-28", ROSTER, [], PARTIES)
        self.assertEqual(party, "Senior operator")
        self.assertIn("most senior active PelOS role", why)

    def test_no_pelos_uses_history(self):
        hist = [{"Requester": "Lauren", "Requester party": "CML"}]
        self.assertEqual(pick_party("Lauren", "Nemah", "2026-10-28", None, hist, PARTIES)[0], "CML")

    def test_nothing_found_asks_for_judgement(self):
        party, why = pick_party("Paulina Almaguer", "Nemah", "2026-10-28", None, [], PARTIES)
        self.assertIsNone(party)
        self.assertIn("pick the closest party yourself", why)


OPEN = {"Status": "Open", "Notes": "2026-10-30: Hayden looking into it."}


class FollowUp(unittest.TestCase):
    def test_good_follow_up(self):
        e = {"note": "Javier fixed the formula.", "fields": {"Status": "Done", "Unblocked date": "2026-11-01",
                                                            "Response": ["Fixed directly"]}}
        self.assertEqual(validate_follow_up(e, OPEN, LISTS), [])

    def test_note_required_and_one_line(self):
        self.assertIn("needs a note saying what happened", validate_follow_up({"fields": {}}, OPEN, LISTS))
        self.assertIn("note must be one line", validate_follow_up({"note": "a\nb"}, OPEN, LISTS))

    def test_classification_fields_refused(self):
        for name in ("Topic", "Root cause", "Requester party", "Type", "Approved", "Notes"):
            p = validate_follow_up({"note": "x", "fields": {name: "y"}}, OPEN, LISTS)
            self.assertIn(f"{name} can't be changed by a follow-up", p)

    def test_done_needs_unblocked_date(self):
        p = validate_follow_up({"note": "x", "fields": {"Status": "Done"}}, OPEN, LISTS)
        self.assertIn("Done needs an Unblocked date", p)
        self.assertEqual(validate_follow_up({"note": "x", "fields": {"Status": "Done"}},
                                            dict(OPEN, **{"Unblocked date": "2026-10-31"}), LISTS), [])

    def test_closed_is_never_reopened(self):
        p = validate_follow_up({"note": "x", "fields": {"Status": "Open"}}, {"Status": "Done"}, LISTS)
        self.assertIn("already closed (Done); a recurrence is a new request", p)

    def test_bad_values(self):
        p = validate_follow_up({"note": "x", "fields": {"Status": "Closed", "Unblocked date": "Monday"}}, OPEN, LISTS)
        self.assertIn("Status='Closed' is not in the list", p)
        self.assertIn("Unblocked date must be a date like 2026-11-03", p)

    def test_notes_are_appended_with_date(self):
        self.assertEqual(add_note("2026-10-30: first.", "second.", date(2026, 11, 3)),
                         "2026-10-30: first.\n2026-11-03: second.")
        self.assertEqual(add_note(None, "first.", date(2026, 11, 3)), "2026-11-03: first.")


def rec(created, **fields):
    return {"id": "recX", "createdTime": created, "fields": fields}


class HaydenChanges(unittest.TestCase):
    DRAFTED = "Type: TS\nTopic: Ops Hub, Forecasting\nRoot cause: Poor visibility\nStatus: Open\nScrap: false"

    def test_unchanged_record_is_quiet(self):
        f = {"Original draft": self.DRAFTED, "Type": "TS", "Topic": ["Forecasting", "Ops Hub"],
             "Root cause": "Poor visibility", "Status": "Done"}
        self.assertEqual(label_changes(f), [])

    def test_changed_label_found(self):
        f = {"Original draft": self.DRAFTED, "Type": "TS", "Topic": ["Ops Hub"], "Root cause": "Compliance"}
        self.assertEqual([c[0] for c in label_changes(f)], ["Topic", "Root cause"])

    def test_scrap_ticked_by_hayden(self):
        self.assertEqual([c[0] for c in label_changes({"Original draft": "Scrap: false", "Scrap": True})], ["Scrap"])

    def test_only_new_unlinked_records(self):
        changed = {"Original draft": "Root cause: Poor visibility", "Root cause": "Compliance"}
        rows = [rec("2026-11-04T05:00:00.000Z", **changed),
                rec("2026-10-28T05:00:00.000Z", **changed),
                rec("2026-11-04T05:00:00.000Z", **changed, **{"Rule changes": ["recRC"]})]
        self.assertEqual(len(pending_changes(rows)), 1)


class RequestIds(unittest.TestCase):
    def test_starts_after_sheet_backfill(self):
        self.assertEqual(next_ts_number([]), 8)

    def test_continues_after_highest(self):
        self.assertEqual(next_ts_number(["TS-0008", "TS-0012", None, "junk"]), 13)


if __name__ == "__main__":
    unittest.main()
