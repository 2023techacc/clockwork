import json
import os
import random
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "sim"))
sys.path.insert(0, os.path.join(ROOT, "docs"))

import build_web  # noqa: E402
import play  # noqa: E402


class WebBundle(unittest.TestCase):
    def test_docs_copy_is_up_to_date(self):
        for path, text in build_web.expected().items():
            with open(os.path.join(ROOT, "docs", "py", path)) as f:
                self.assertEqual(f.read(), text, f"docs/py/{path} is stale: run python sim/build_web.py")

    def test_bridge_plays_full_fights(self):
        opts = json.loads(play.options())
        self.assertIn("starter", opts["decks"])
        rng = random.Random(0)
        for deck in opts["decks"]:
            v = json.loads(play.start(deck, "saboteur", 3))
            for _ in range(400):
                if v["result"]:
                    break
                if v["can_install"] and v["hand"] and rng.random() < 0.6:
                    v = json.loads(play.install(rng.randrange(len(v["hand"])), rng.randrange(6)))
                elif v["can_end_install"]:
                    v = json.loads(play.end_install(rng.choice(["cw", "ccw"])))
                elif v["can_crank"] and rng.random() < 0.6:
                    v = json.loads(play.crank())
                else:
                    v = json.loads(play.end_turn())
            self.assertIsNotNone(v["result"])
            self.assertTrue(v["summary"])
            self.assertTrue(v["actions"])
