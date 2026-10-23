"""Table and field definitions for the Team Success Log base, built from the skill's lists."""

from lists import load_lists, resource_required_values

REQUESTS = "Requests"
RULE_CHANGES = "Rule Changes"


def _select(name, choices, description=""):
    return {
        "name": name,
        "type": "singleSelect",
        "description": description,
        "options": {"choices": [{"name": c} for c in choices]},
    }


def _multi(name, choices, description=""):
    return {
        "name": name,
        "type": "multipleSelects",
        "description": description,
        "options": {"choices": [{"name": c} for c in choices]},
    }


def _text(name, description=""):
    return {"name": name, "type": "singleLineText", "description": description}


def _long(name, description=""):
    return {"name": name, "type": "multilineText", "description": description}


def _date(name, description=""):
    return {"name": name, "type": "date", "description": description, "options": {"dateFormat": {"name": "iso"}}}


def _datetime(name, description=""):
    return {
        "name": name,
        "type": "dateTime",
        "description": description,
        "options": {
            "dateFormat": {"name": "iso"},
            "timeFormat": {"name": "24hour"},
            "timeZone": "America/New_York",
        },
    }


def _url(name, description=""):
    return {"name": name, "type": "url", "description": description}


CHECKS_FORMULA = (
    "TRIM(CONCATENATE("
    "IF(AND({Resource required}, {Resource group}, "
    "OR("
    "AND({Resource group}='Thing', FIND({Resource required}, '{thing}')=0), "
    "AND({Resource group}='Person', FIND({Resource required}, '{person}')=0)"
    ")), 'Resource group does not match Resource required. ', ''), "
    "IF(OR(AND({Needs help}, NOT({Needs help party})), AND({Needs help party}, NOT({Needs help}))), "
    "'Needs help and Needs help party must both be filled or both blank. ', ''), "
    "IF(AND({Type}='TS', NOT({Request ID})), 'TS record has no Request ID. ', '')"
    "))"
)


def requests_fields(lists):
    return [
        _text("Summary", "Field 7. One line, in Claude's words: what is being asked for."),
        _long("Message", "The Slack message text, word for word."),
        _select("Type", lists["type"], "Drafts are always TS. Hayden sets Personal by hand on a draft that isn't TS work."),
        _text("Request ID", "Field 0. TS-0001 style. TS records only. Never reused."),
        _date("Date received", "Field 1."),
        _select("Intake type", lists["intake_type"], "Field 2."),
        _select("Source", lists["source"], "Field 3."),
        _text("Requester", "Field 4."),
        _select("Requester party", lists["party"], "Field 4b."),
        _text("Needs help", "Field 5. Filled only with Needs help party."),
        _select("Needs help party", lists["party"], "Field 5b. Filled only with Needs help."),
        _text("Client", "Field 6. Client, or Internal."),
        _select("Urgency", lists["urgency"], "Field 8."),
        _select("Resource group", lists["resource_group"], "Field 9a. Must match Resource required."),
        _select("Resource required", resource_required_values(lists), "Field 9."),
        _select("Root cause", lists["root_cause"], "Field 10."),
        _multi("Response", lists["response"], "Field 11."),
        _text("Routed to", "Field 12. Party or person."),
        _date("Unblocked date", "Field 13. Blank = open."),
        _select("Lasting fix", lists["lasting_fix"], "Field 14."),
        _select("Lasting fix status", lists["lasting_fix_status"], "Field 15."),
        _url("Resource link", "Field 16."),
        _select("Workflow maturity", lists["workflow_maturity"], "Field 17."),
        _text("Related requests", "Field 18. Request IDs of repeats."),
        {
            "name": "TS time spent",
            "type": "number",
            "description": "Field 19. Hours estimate.",
            "options": {"precision": 1},
        },
        _long("Notes", "Field 20."),
        _select("Status", lists["status"]),
        _url("Slack link", "Permalink of the ask. Dedupe key."),
        _url("Slack thread", "Permalink of the thread root. Dedupe key."),
        _datetime("Message time", "When the Slack message was posted."),
        {"name": "Approved", "type": "checkbox", "description": "Hayden only. Claude never ticks this.",
         "options": {"icon": "check", "color": "greenBright"}},
        _long("Why I changed it", "Hayden: say why you changed Claude's draft. Claude turns this into a proposed rule."),
        _long("Claude notes", "Why Claude picked this Type and these labels, and what it assumed."),
        _long("Original draft", "Claude's labels as first drafted. Used to see what Hayden changed."),
    ]


def checks_formula(lists):
    """Airtable's API can't create formula fields, so Hayden pastes this into a "Checks" field by hand."""
    thing = "|".join(lists["resource_required"]["Thing"])
    person = "|".join(lists["resource_required"]["Person"])
    return CHECKS_FORMULA.replace("{thing}", thing).replace("{person}", person)


def rule_changes_fields(lists):
    return [
        _text("Proposed rule", "One sentence, written as it would appear in the intake skill."),
        _long("Reason"),
        _text("Skill section", "Which section of the intake skill this changes."),
        _select("Status", lists["rule_change_status"]),
        _url("Commit", "Link to the commit that applied an accepted rule."),
    ]


def link_field():
    """Added after both tables exist. Airtable creates the reverse field on Requests."""
    return {"name": "Source records", "type": "multipleRecordLinks",
            "description": "The request records this rule change came from."}


def tables():
    lists = load_lists()
    return {REQUESTS: requests_fields(lists), RULE_CHANGES: rule_changes_fields(lists)}
