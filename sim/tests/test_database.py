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


if __name__ == "__main__":
    unittest.main()
