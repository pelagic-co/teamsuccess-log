import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pelos import client_key, role_on, roster, same_client, same_person  # noqa: E402


def engagement(name, start="2026-10-01", end="2026-10-31", status="ACTIVE", **people):
    fields = {"Name": name, "Engagement Start Date": start, "Engagement End Date": end, "Status (Dynamic)": status}
    for field, names in people.items():
        fields[{"cml": "Client Management Lead", "senior": "Senior Operator",
                "tactical": "Tactical Operator(s)"}[field]] = [{"name": n} for n in names]
    return {"fields": fields}


ROWS = roster([
    engagement("RosySoil 5.0, Planning", cml=["Juan Ignacio Rion"], senior=["Javier Rojas"], tactical=["Rodrigo León"]),
    engagement("TOON 1.3, Ops", senior=["Mandy Brendle"], tactical=["Guadalupe Lestelle"]),
    engagement("Fixie Dust 5.0, 3PL", cml=["Ciara Rudas"], tactical=["Lina Park"]),
    engagement("Manukora 3.0, Ops", cml=["Daniel Manley"], tactical=["Daniel Manley"]),
    engagement("Doughlicious 4.0, Planning", start="2026-01-01", end="2026-06-30", status="CLOSED / OLD SOW",
               cml=["Max Sunseri"]),
    engagement("Doughlicious 5.0, Planning", start="2026-07-01", end="2026-12-31", tactical=["Max Sunseri"]),
])


class Matching(unittest.TestCase):
    def test_client_key_drops_version_spaces_accents(self):
        self.assertEqual(client_key("RosySoil 5.0"), client_key("Rosy Soil"))
        self.assertEqual(client_key("Frönen Ice Cream 6.0"), "fronenicecream")

    def test_client_prefix(self):
        self.assertTrue(same_client("Toon Health", "TOON 1.3"))
        self.assertTrue(same_client("Zoid / Equip", "Zoid 7.0"))
        self.assertFalse(same_client("SunPowder", "Sunrise Organics 6.0"))
        self.assertFalse(same_client("Sun", "Sunrise Organics 6.0"))  # too short to trust

    def test_person_nicknames_and_middle_names(self):
        self.assertTrue(same_person("Rodri Leon", "Rodrigo León"))
        self.assertTrue(same_person("Ciara Sophia Rudas", "Ciara Rudas"))
        self.assertTrue(same_person("Lina", "Lina Park"))
        self.assertFalse(same_person("Javier Rojas", "Juan Ignacio Rion"))


class RoleOnClient(unittest.TestCase):
    def test_role_changes_by_client(self):
        self.assertEqual(role_on(ROWS, "Rodri Leon", "Rosy Soil", "2026-10-19")[0], "Tactical operator")
        self.assertEqual(role_on(ROWS, "Juan Ignacio Rion", "Rosy Soil", "2026-10-19")[0], "CML")
        self.assertEqual(role_on(ROWS, "Mandy Brendle", "Toon Health", "2026-10-20")[0], "Senior operator")

    def test_engagement_covering_the_message_date_wins(self):
        self.assertEqual(role_on(ROWS, "Max Sunseri", "Doughlicious", "2026-10-16")[0], "Tactical operator")
        self.assertEqual(role_on(ROWS, "Max Sunseri", "Doughlicious", "2026-03-01")[0], "CML")

    def test_most_senior_role_wins(self):
        role, why = role_on(ROWS, "Daniel Manley", "Manukora", "2026-10-21")
        self.assertEqual(role, "CML")
        self.assertIn("Tactical operator", why)

    def test_not_found_says_why(self):
        self.assertEqual(role_on(ROWS, "Natasha Uszak", None, "2026-10-15"), (None, "no client on the record"))
        self.assertIn("not staffed", role_on(ROWS, "Brian Murray", "Toon Health", "2026-10-15")[1])
        self.assertIn("no PelOS engagement", role_on(ROWS, "Brian Murray", "Acme", "2026-10-15")[1])


if __name__ == "__main__":
    unittest.main()
