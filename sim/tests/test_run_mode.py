import unittest

from clockwork.enemies import ENEMIES
from clockwork.parts import Kind, Mod
from clockwork.run_mode import (ACT_ARMOR, ACT_BOSSES, ACT_SCALE, BETWEEN_ACTS_HEAL, DAY_AMBUSH_PER_HOUR,
                                DAY_BED_PRICE, DAY_FULL_SLEEP, DAY_HOURS, DAY_HURRY_COGS, DAY_NIGHT_ATTACHMENTS,
                                DAY_NIGHT_COGS, DAY_NIGHT_SCALE, DAY_NODES, DAY_SLEEP_HEAL, DAY_SLEEP_HOURS,
                                DISTRICT_NODES, HOUR_COST, HOURS, LEVEL_PRICE, MACHINE, MACHINE_CHOICES, MARKET_STOCK,
                                MOD_RARITY, REST_HEAL, STOPS, Run, RunError)
from clockwork.run_policy import simulate_run


def started(seed, **kw):
    """A run past its starting machine-upgrade choice (none taken)."""
    return Run("starter", seed, **kw).choose_start("")


class RunMode(unittest.TestCase):
    def test_first_doors_are_fights_and_last_is_rest_or_workshop(self):
        run = started(1)
        self.assertEqual(run.doors, ["fight"])
        run.stop = STOPS - 1
        self.assertEqual(run._make_doors(), ["rest", "workshop"])
        run.stop = STOPS
        self.assertEqual(run._make_doors(), ["boss"])

    def test_win_gives_cogs_heal_and_rewards(self):
        run = started(2)
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
        run = started(3)
        run.choose_door(0)
        run.finish_fight("win", 50)
        cogs = run.cogs
        run.take_reward(scrap=True)
        self.assertEqual(run.cogs, cogs + 10)
        run.choose_door(0)
        run.finish_fight("loss", 0)
        self.assertEqual(run.phase, "lost")

    def test_elite_offers_attachment_and_attach_rules(self):
        run = started(4)
        run.phase, run.doors = "doors", ["elite"]
        run.choose_door(0)
        self.assertTrue(run.enemy in ("overclocker", "rust_golem", "pickpocket", "jammer_prime"))
        run.finish_fight("win", 40)
        self.assertNotIn("salvage", run.offer)               # elites give no machine upgrades (v18)
        self.assertEqual(len(run.offer["attachments"]), 3)
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

    def test_elite_parts_are_uncommon_or_rare(self):
        from clockwork.run_mode import PART_TIER
        for seed in range(10):
            run = started(seed)
            run.phase, run.doors = "doors", ["elite"]
            run.choose_door(0)
            run.finish_fight("win", 40)
            self.assertTrue(all(PART_TIER[Kind(p)] in ("uncommon", "rare") for p in run.offer["parts"]))

    def test_workshop_buy_sell_remove_repair(self):
        run = started(5)
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

    def test_rest(self):
        run = started(7)
        run.phase, run.doors = "doors", ["rest"]
        run.choose_door(0)
        run.hp = 20
        run.rest("heal")
        self.assertEqual(run.hp, 20 + REST_HEAL)

    def test_simulated_runs_finish(self):
        for seed in range(3):
            run = simulate_run("starter", seed, "greedy")
            self.assertIn(run.phase, ("won", "lost"))


class MachineUpgrades(unittest.TestCase):
    def test_start_offers_a_choice(self):
        run = Run("starter", 3)
        self.assertEqual(run.phase, "start")
        offered = run.offer["machines"]
        self.assertEqual(len(offered), MACHINE_CHOICES)
        with self.assertRaises(RunError):
            run.choose_start(next(k for k in MACHINE if k not in offered))
        run.choose_start(offered[1])
        self.assertEqual(run.machine, [offered[1]])
        self.assertEqual(run.phase, "doors")

    def test_workshop_sells_level_ups_only(self):
        run = started(5)
        run.machine = ["flywheel", "bigger_gear"]               # Bigger Gear has one level only
        run.phase, run.doors = "doors", ["workshop"]
        run.choose_door(0)
        self.assertEqual([(m["key"], m["level"], m["price"]) for m in run.offer["machines"]],
                         [("flywheel", 2, LEVEL_PRICE[2])])
        run.cogs = 500
        run.buy("machine", 0)
        self.assertEqual(run.level("flywheel"), 2)
        with self.assertRaises(RunError):
            run.buy("machine", 0)

    def test_levels_stack_in_the_rules(self):
        run = started(6)
        run.machine = ["flywheel", "flywheel", "heat_housing", "extra_hands", "bigger_gear", "frame", "frame",
                       "hopper", "cooling_fins"]
        r = run.rules()
        self.assertEqual((r.crank_power, r.overheat_at, r.installs_per_turn, r.gear_size), (5, 12, 3, 8))
        self.assertEqual((r.player_hp, r.offered_per_turn, r.heat_decay), (55 + 16, 4, 1))
        with self.assertRaises(RunError):
            run._install_machine("bigger_gear")


class Acts(unittest.TestCase):
    def test_bosses_by_act_known_from_the_start(self):
        for seed in range(30):
            run = Run("starter", seed)
            self.assertEqual(len(run.bosses), 3)
            for act, boss in enumerate(run.bosses):
                self.assertIn(boss, ACT_BOSSES[act])
        run = started(1, boss="pendulum")
        run.stop, run.doors = run.stops, ["boss"]
        run.choose_door(0)
        self.assertEqual(run.enemy, "pendulum")

    def test_boss_reward_heals_half_and_starts_the_next_act(self):
        run = started(2)
        run.stop, run.doors = run.stops, ["boss"]
        run.choose_door(0)
        run.finish_fight("win", 15)
        self.assertEqual(run.phase, "boss_reward")
        offered = run.offer["machines"]
        self.assertEqual(len(offered), MACHINE_CHOICES)
        run.choose_boss_reward("cooling_fins" if "cooling_fins" in offered else "")
        self.assertEqual((run.act, run.stop, run.phase, run.doors), (1, 0, "doors", ["fight"]))
        self.assertEqual(run.hp, 15 + int((run.max_hp() - 15) * BETWEEN_ACTS_HEAL))

    def test_last_boss_wins_the_run(self):
        run = started(3, acts=1)
        run.stop, run.doors = run.stops, ["boss"]
        run.choose_door(0)
        run.finish_fight("win", 20)
        self.assertEqual(run.phase, "won")

    def test_veterans_in_later_acts(self):
        run = started(4)
        run.act = 1
        run.choose_door(0)
        spec = run.enemy_spec()
        base = ENEMIES[run.enemy]
        self.assertEqual(spec.armor, base.armor + ACT_ARMOR[1])
        self.assertGreater(spec.hp, base.hp * ACT_SCALE[1] - 2)


class Growth(unittest.TestCase):
    def test_play_styles_and_starting_machine(self):
        for style in ({"elites": "seek", "rest": "tinker"}, {"elites": "avoid", "parts": "none"},
                      {"remove_basics": True, "machine_first": True, "rest": "heal"}):
            run = simulate_run("starter", 4, "greedy", style=style, machine=["flywheel"], acts=1)
            self.assertIn(run.phase, ("won", "lost"))
            self.assertIn("flywheel", run.machine)
        run = simulate_run("starter", 4, "greedy", style={"elites": "avoid"}, acts=1)
        self.assertFalse(any(h.get("node") == "elite" for h in run.history))

    def test_enemies_grow_through_the_district(self):
        run = started(1, growth=0.5)
        run.choose_door(0)
        first = run.enemy_spec()
        self.assertEqual(first.hp, ENEMIES[run.enemy].hp)
        run.stop = run.stops
        run.node, run.enemy = "boss", "clock_tower"
        self.assertEqual(run.enemy_scale(), 1.5)
        self.assertGreater(run.enemy_spec().hp, ENEMIES["clock_tower"].hp)


class HoursMap(unittest.TestCase):
    def test_district_layout(self):
        run = Run("starter", 3, map="hours").choose_start("")
        kinds = [t for t in run.district.values() if t != "gate"]
        self.assertEqual({t: kinds.count(t) for t in DISTRICT_NODES}, DISTRICT_NODES)
        self.assertEqual(run.doors, ["fight", "fight", "fight", "boss"])     # the gate's neighbours, or wait

    def test_nodes_cost_hours_and_enemies_grow(self):
        run = Run("starter", 4, map="hours").choose_start("")
        run.choose_door(0)
        self.assertEqual((run.hours_used, run.hours_left()), (0, HOURS - HOUR_COST["fight"]))
        self.assertEqual(run.enemy_scale(), 1.0)
        run.finish_fight("win", 40)
        run.take_reward(scrap=True)
        self.assertEqual(run.hours_used, HOUR_COST["fight"])
        self.assertGreater(run.enemy_scale("fight"), 1.0)
        self.assertTrue(all(HOUR_COST[d] <= run.hours_left() for d in run.doors[:-1]))
        run.hours_used = HOURS - 1                      # only a 1-hour Workshop could still fit
        self.assertTrue(set(run._make_doors()) <= {"workshop", "boss"})
        run.hours_used = HOURS
        self.assertEqual(run._make_doors(), ["boss"])

    def test_waiting_for_midnight_and_a_new_district_each_act(self):
        run = Run("starter", 5, map="hours").choose_start("")
        first = dict(run.district)
        run.choose_door(len(run.doors) - 1)            # wait for the boss
        self.assertEqual(run.node, "boss")
        run.finish_fight("win", 30)
        run.choose_boss_reward("")
        self.assertEqual((run.act, run.hours_used, len(run.visited)), (1, 0, 1))
        self.assertNotEqual(run.district, first)

    def test_simulated_hours_runs_finish(self):
        for style in ({}, {"plan": True}):
            run = simulate_run("starter", 2, "greedy", style=style, acts=1, map="hours")
            self.assertIn(run.phase, ("won", "lost"))


class DayMap(unittest.TestCase):
    """Package 1 of Hours-Map-Ideas.md: a day in the Brass Quarter."""
    def day(self, seed=3):
        return Run("starter", seed, map="day").choose_start("")

    def test_layout_and_opening_hours(self):
        run = self.day()
        kinds = [t for t in run.district.values() if t != "gate"]
        self.assertEqual({t: kinds.count(t) for t in DAY_NODES}, DAY_NODES)
        self.assertEqual((run.clock(), run.is_night()), (6, False))
        self.assertEqual(run.doors, ["fight", "fight", "fight", "wait", "boss"])
        self.assertTrue(run.is_open("workshop") and not run.is_open("rest") and not run.is_open("elite"))
        self.assertEqual((run.clock(12), run.is_night(12)), (18, True))
        self.assertTrue(run.is_open("rest", 12) and run.is_open("elite", 12) and not run.is_open("workshop", 12))

    def test_night_shift_and_hurry_bonus(self):
        run = self.day()
        run.choose_door(0)
        day_hp = run.enemy_spec().hp
        self.assertAlmostEqual(run.loot_bonus(), 1 + DAY_HURRY_COGS)          # dawn
        run.hours_used = 6
        self.assertAlmostEqual(run.loot_bonus(), 1 + DAY_HURRY_COGS / 2)      # noon
        run.hours_used = 13
        self.assertEqual(run.loot_bonus(), DAY_NIGHT_COGS)
        grown = run.enemy_spec(progress=0)
        self.assertGreater(grown.hp, day_hp)                                 # x DAY_NIGHT_SCALE at night
        self.assertGreater(DAY_NIGHT_SCALE, 1)

    def test_sleep(self):
        run = self.day()
        run.hours_used = 14                                                  # 20:00
        run.phase, run.node, run.offer = "rest", "rest", {"attachments": ["Sharpened", "Bracing"]}
        self.assertEqual(run.sleep_options(), {"nap": 1})                    # beds cost cogs; a nap is free
        run.cogs = 100
        self.assertEqual(run.sleep_options(), {"nap": 1, "sleep": DAY_SLEEP_HOURS, "dawn": DAY_FULL_SLEEP})
        run.hp = 20
        run.rest("sleep")
        self.assertEqual((run.hp, run.hours_used), (20 + DAY_SLEEP_HEAL * DAY_SLEEP_HOURS, 14 + DAY_SLEEP_HOURS))
        self.assertEqual(run.cogs, 100 - DAY_BED_PRICE["sleep"])
        run.phase, run.offer = "rest", {"attachments": ["Sharpened", "Bracing"]}
        run.rest("dawn")                                                     # what's left of the night
        self.assertEqual((run.hours_used, len(run.inventory), run.doors), (DAY_HOURS, 2, ["boss"]))
        early = self.day(4)
        early.hours_used, early.phase, early.offer, early.cogs = 12, "rest", {"attachments": ["Sharpened"]}, 50
        early.rest("dawn")                                                   # a full night's sleep at 18:00...
        self.assertEqual((early.hours_used, early.rested), (12 + DAY_FULL_SLEEP, True))
        self.assertEqual(early.sleep_options(), {"nap": 1})                  # ...then only naps
        with self.assertRaises(RunError):
            run.phase = "rest"
            run.rest("heal")

    def test_night_market_and_night_loot(self):
        run = self.day()
        run.hours_used = 13
        self.assertTrue(run.is_open("market") and not run.is_open("market", 0))
        run.node, run.phase = "market", "doors"
        run.doors, run.door_nodes = ["market"], [(6, 0)]
        run.choose_door(0)
        self.assertTrue(run.offer["market"] and run.offer["machines"] == [])
        self.assertEqual(len(run.offer["attachments"]), MARKET_STOCK["attachments"])
        self.assertTrue(all(MOD_RARITY[Mod(a["mod"])] in ("uncommon", "rare") for a in run.offer["attachments"]))
        run.cogs = 100
        with self.assertRaises(RunError):
            run.buy("repair")
        run.leave_workshop()
        self.assertEqual(run.history[-1]["node"], "market")
        run.phase, run.node, run.enemy = "fight", "fight", "dummy"           # a night win: a part and an attachment
        run.finish_fight("win", 30)
        self.assertEqual(len(run.offer["attachments"]), DAY_NIGHT_ATTACHMENTS)

    def test_wait_and_ambush(self):
        run = self.day()
        run.choose_door(run.doors.index("wait"))
        self.assertEqual((run.hours_used, run.phase), (1, "doors"))
        run.hours_used = DAY_HOURS                                           # nothing fits: no inn, no wait
        self.assertEqual(run._make_doors(), ["boss"])
        run.hours_used = 1
        run.choose_door(run.doors.index("boss"))
        full = Run("starter", 3).enemy_spec(run.boss, "boss")
        self.assertEqual(run.enemy_spec().hp, round(full.hp * (1 - min(0.3, DAY_AMBUSH_PER_HOUR * 23))))

    def test_simulated_day_runs_finish(self):
        for style in ({}, {"plan": True}):
            run = simulate_run("starter", 2, "greedy", style=style, acts=1, map="day")
            self.assertIn(run.phase, ("won", "lost"))

class ExpertPlanner(unittest.TestCase):
    def test_forecast_and_projection(self):
        from clockwork import planner
        run = started(3)
        f = planner.forecast(run)
        self.assertEqual(set(f), {"fight", "elite", "elite_worst", "boss"})
        self.assertGreaterEqual(f["elite_worst"], f["elite"])
        self.assertIs(planner.forecast(run), f)          # cached
        self.assertLessEqual(planner.boss_need(f, run), run.max_hp())
        run.hp = 30
        self.assertEqual(planner.projected_boss_hp(run, "rest", 0, f), 30 + REST_HEAL)
        self.assertLess(planner.projected_boss_hp(run, "elite", 2, f), planner.projected_boss_hp(run, "fight", 2, f))

    def test_planned_runs_finish(self):
        run = simulate_run("starter", 1, "greedy", style={"plan": True}, acts=1)
        self.assertIn(run.phase, ("won", "lost"))

if __name__ == "__main__":
    unittest.main()
