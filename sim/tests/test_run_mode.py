import unittest

from clockwork.parts import Kind, Mod
from clockwork.run_mode import STOPS, Run, RunError
from clockwork.run_policy import simulate_run


class RunMode(unittest.TestCase):
    def test_first_doors_are_fights_and_last_is_rest_or_workshop(self):
        run = Run("starter", 1)
        self.assertEqual(run.doors, ["fight"])
        run.stop = STOPS - 1
        self.assertEqual(run._make_doors(), ["rest", "workshop"])
        run.stop = STOPS
        self.assertEqual(run._make_doors(), ["boss"])

    def test_win_gives_cogs_heal_and_rewards(self):
        run = Run("starter", 2)
        run.choose_door(0)
        self.assertEqual(run.phase, "fight")
        run.finish_fight("win", 30)
        self.assertEqual(run.hp, 30 + run.base_rules.heal_between_fights)
        self.assertGreater(run.cogs, 0)
        self.assertEqual(len(run.offer["parts"]), 3)
        part = run.offer["parts"][0]
        n = len(run.cards)
        run.take_reward(part=part)
        self.assertEqual(len(run.cards), n + 1)
        self.assertEqual(run.phase, "doors")

    def test_scrap_and_loss(self):
        run = Run("starter", 3)
        run.choose_door(0)
        run.finish_fight("win", 50)
        cogs = run.cogs
        run.take_reward(scrap=True)
        self.assertEqual(run.cogs, cogs + 10)
        run.choose_door(0)
        run.finish_fight("loss", 0)
        self.assertEqual(run.phase, "lost")

    def test_elite_offers_attachment_and_attach_rules(self):
        run = Run("starter", 4)
        run.phase, run.doors = "doors", ["elite"]
        run.choose_door(0)
        self.assertTrue(run.enemy in ("overclocker", "rust_golem", "pickpocket", "jammer_prime"))
        run.finish_fight("win", 40)
        mod = run.offer["attachments"][0]
        run.take_reward(attachment=mod)
        self.assertEqual([m.value for m in run.inventory], [mod])
        run.inventory = [Mod.SHARPENED, Mod.SHARPENED, Mod.ECHO, Mod.COIL]
        striker = next(c for c in run.cards if c["kind"] == Kind.STRIKER)
        run.attach(0, striker["id"])
        with self.assertRaises(RunError):                   # no duplicates on one part
            run.attach(0, striker["id"])
        run.attach(1, striker["id"])                        # Echo: second attachment
        with self.assertRaises(RunError):                   # limit 2
            run.attach(0, striker["id"])
        with self.assertRaises(RunError):                   # Coil only fits Springs
            run.attach(1, striker["id"])
        self.assertIn(((Kind.STRIKER, (Mod.ECHO, Mod.SHARPENED))), run.fight_deck())

    def test_workshop_buy_sell_remove_repair(self):
        run = Run("starter", 5)
        run.phase, run.doors = "doors", ["workshop"]
        run.choose_door(0)
        run.cogs = 500
        run.hp = 20
        run.buy("repair")
        self.assertEqual(run.hp, 35)
        n = len(run.cards)
        run.buy("part", 0)
        self.assertEqual(len(run.cards), n + 1)
        run.buy("attachment", 0)
        self.assertEqual(len(run.inventory), 1)
        cogs = run.cogs
        run.sell_attachment(0)
        self.assertGreater(run.cogs, cogs)
        price = run.remove_price()
        run.remove_card(run.cards[0]["id"])
        self.assertEqual(run.remove_price(), price + 15)
        with self.assertRaises(RunError):
            run.buy("part", 0)                              # already sold
        run.leave_workshop()
        self.assertEqual(run.phase, "doors")

    def test_workshop_sells_every_missing_machine_upgrade(self):
        from clockwork.run_mode import MACHINE
        run = Run("starter", 5)
        run.machine = ["flywheel"]
        run.phase, run.doors = "doors", ["workshop"]
        run.choose_door(0)
        self.assertEqual({m["key"] for m in run.offer["machines"]}, set(MACHINE) - {"flywheel"})
        run.cogs = 500
        i = next(i for i, m in enumerate(run.offer["machines"]) if m["key"] == "extra_hands")
        run.buy("machine", i)
        self.assertIn("extra_hands", run.machine)
        with self.assertRaises(RunError):
            run.buy("machine", i)

    def test_salvage_is_a_choice_of_two(self):
        from clockwork import run_mode
        old, run_mode.ELITE_SALVAGE = run_mode.ELITE_SALVAGE, 1.0
        try:
            run = Run("starter", 4)
            run.phase, run.doors = "doors", ["elite"]
            run.choose_door(0)
            run.finish_fight("win", 40)
            offered = run.offer["salvage"]
            self.assertEqual(len(offered), 2)
            run.take_reward(salvage=offered[1])
            self.assertEqual(run.machine, [offered[1]])
        finally:
            run_mode.ELITE_SALVAGE = old

    def test_boss_is_known_from_the_start(self):
        from clockwork.enemies import BOSSES
        bosses = {Run("starter", seed).boss for seed in range(40)}
        self.assertEqual(bosses, set(BOSSES))
        run = Run("starter", 1, boss="pendulum")
        run.stop, run.doors = run.stops, ["boss"]
        run.choose_door(0)
        self.assertEqual(run.enemy, "pendulum")

    def test_machine_upgrades_change_rules(self):
        run = Run("starter", 6)
        run.machine = ["flywheel", "heat_housing", "extra_hands", "bigger_gear"]
        r = run.rules()
        self.assertEqual((r.crank_power, r.overheat_at, r.installs_per_turn, r.gear_size), (4, 12, 3, 8))

    def test_rest(self):
        run = Run("starter", 7)
        run.phase, run.doors = "doors", ["rest"]
        run.choose_door(0)
        run.hp = 20
        run.rest("heal")
        from clockwork.run_mode import REST_HEAL
        self.assertEqual(run.hp, 20 + REST_HEAL)

    def test_simulated_runs_finish(self):
        for seed in range(3):
            run = simulate_run("starter", seed, "greedy")
            self.assertIn(run.phase, ("won", "lost"))


class Growth(unittest.TestCase):
    def test_play_styles_and_starting_machine(self):
        for style in ({"elites": "seek", "rest": "tinker"}, {"elites": "avoid", "parts": "none"},
                      {"remove_basics": True, "machine_first": True, "rest": "heal"}):
            run = simulate_run("starter", 4, "greedy", style=style, machine=["flywheel"])
            self.assertIn(run.phase, ("won", "lost"))
            self.assertIn("flywheel", run.machine)
        run = simulate_run("starter", 4, "greedy", style={"elites": "avoid"})
        self.assertFalse(any(h.get("node") == "elite" for h in run.history))

    def test_enemies_grow_through_the_district(self):
        run = Run("starter", 1, growth=0.5)
        run.choose_door(0)
        first = run.enemy_spec()
        self.assertEqual(first.hp, __import__("clockwork.enemies", fromlist=["ENEMIES"]).ENEMIES[run.enemy].hp)
        run.stop = run.stops
        run.enemy = "clock_tower"
        self.assertEqual(run.enemy_scale(), 1.5)
        self.assertGreater(run.enemy_spec().hp, 98)
