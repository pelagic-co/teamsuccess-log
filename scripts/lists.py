"""Reads the value lists from the intake skill so there is one source for them."""

import json
import re
from pathlib import Path

SKILL_PATH = Path(__file__).resolve().parent.parent / ".claude" / "skills" / "ts-intake" / "SKILL.md"
_BLOCK = re.compile(r"```json ts-lists\n(.*?)\n```", re.DOTALL)


def load_lists(path=SKILL_PATH):
    text = Path(path).read_text(encoding="utf-8")
    blocks = _BLOCK.findall(text)
    if len(blocks) != 1:
        raise ValueError(f"expected exactly one ts-lists block in {path}, found {len(blocks)}")
    return json.loads(blocks[0])


def resource_required_values(lists):
    return [value for group in lists["resource_group"] for value in lists["resource_required"][group]]


def group_of(lists, resource_required):
    for group in lists["resource_group"]:
        if resource_required in lists["resource_required"][group]:
            return group
    raise ValueError(f"unknown Resource required value: {resource_required!r}")
