import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "sim"))

import build_database  # noqa: E402
from clockwork.enemies import ENEMIES  # noqa: E402
from clockwork.parts import Kind, Mod  # noqa: E402


class Database(unittest.TestCase):
    def test_database_is_up_to_date(self):
        with open(build_database.OUT) as f:
            self.assertEqual(f.read(), build_database.build(), "Database.md is stale: run python sim/build_database.py")

    def test_everything_is_listed(self):
        text = build_database.build()
        for name in [k.value for k in Kind] + [m.value for m in Mod] + list(ENEMIES):
            self.assertIn(f"**{name}**", text)

    def test_target_status(self):
        from clockwork.targets import status
        self.assertEqual(status((65, 70), "67%"), "on target")
        self.assertEqual(status((65, 70), 72), "off target")
        self.assertEqual(status((2.5, 4), "a +5.0, b +3.1"), "partly off")
        self.assertEqual(status("on target", "72% vs 63%"), "on target")
        self.assertIn("## Balance targets", build_database.build())


if __name__ == "__main__":
    unittest.main()
