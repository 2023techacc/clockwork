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
            v = RunMode.play_fight(self, v, rng)
            self.assertIsNotNone(v["fight"]["result"])
            self.assertTrue(v["fight"]["summary"])
            self.assertTrue(v["fight"]["actions"])


class RunMode(unittest.TestCase):
    def play_fight(self, v, rng):
        for _ in range(500):
            f = v["fight"]
            if f["result"]:
                return v
            if f["can_install"] and f["hand"] and rng.random() < 0.6:
                v = json.loads(play.install(rng.randrange(len(f["hand"])), rng.randrange(len(f["gear"]))))
            elif f["can_end_install"]:
                v = json.loads(play.end_install(rng.choice(["cw", "ccw"])))
            elif f["can_crank"] and rng.random() < 0.6:
                v = json.loads(play.crank())
            else:
                v = json.loads(play.end_turn())
        self.fail("fight did not end")

    def test_full_runs_through_the_bridge(self):
        rng = random.Random(1)
        screens = set()
        for seed in range(8):
            v = json.loads(play.start_run("big_hit", seed))
            for _ in range(200):
                screen = v["screen"]
                screens.add(screen)
                run = v["run"]
                if screen in ("won", "lost"):
                    break
                if run["inventory"] and run["inventory"][0]["fits"]:
                    v = json.loads(play.attach(0, run["inventory"][0]["fits"][0]))
                    continue
                if screen == "start":
                    v = json.loads(play.choose_start(run["offer"]["machines"][0]))
                elif screen == "boss_reward":
                    v = json.loads(play.choose_boss_reward(run["offer"]["machines"][-1]))
                elif screen == "doors":
                    v = json.loads(play.choose_door(rng.randrange(len(run["doors"]))))
                elif screen == "fight":
                    hp = run["hp"]
                    self.assertEqual(v["fight"]["hp"], hp)              # HP carried into the fight
                    v = self.play_fight(v, rng)
                elif screen == "reward":
                    atts = run["offer"].get("attachments", [])
                    v = json.loads(play.take_reward(run["offer"]["parts"][0], atts[0] if atts else "", False))
                elif screen == "rest":
                    v = json.loads(play.rest("tinker", run["offer"]["attachments"][0]))
                elif screen == "workshop":
                    if run["cogs"] >= 30 and not run["offer"]["parts"][0]["sold"] and run["offer"]["parts"][0]["price"] <= run["cogs"]:
                        v = json.loads(play.buy("part", 0))
                    v = json.loads(play.leave_workshop())
            self.assertIn(v["screen"], ("won", "lost"))
        self.assertTrue({"start", "doors", "fight", "reward"} <= screens)

    def test_single_fight_mode(self):
        v = json.loads(play.start("starter", "dummy", 2))
        self.assertEqual((v["mode"], v["screen"], v["run"]), ("fight", "fight", None))
