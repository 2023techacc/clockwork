import itertools
import unittest

from clockwork import RulesConfig, apply, legal_actions, new_fight
from clockwork import engine
from clockwork.search import turn_outcomes
from clockwork.agents.random_agent import RandomAgent
from clockwork.decks import DECKS, deck_list
from clockwork.enemies import ENEMIES
from clockwork.parts import Kind as K, Part

S, P, SP, M, A, C, L, CO, H, MG = (K.STRIKER, K.PLATE, K.SPRING, K.MIRROR, K.AMPLIFIER,
                                    K.COUPLER, K.LOADER, K.COOLANT, K.HAMMER, K.MAGNET)


def setup(arrival, enemy="dummy", rules=RulesConfig(), queue=()):
    """Gear given in arrival order: arrival[0] is at the Trigger Point now, arrival[1] comes up
    on the next forward crank, and so on. Returns (state, slot_of) where slot_of[k] is the gear
    slot of arrival[k]."""
    s = new_fight({S: 1}, enemy, seed=0, rules=rules, trace=True)
    n = rules.gear_size
    uid = itertools.count(100)
    s.gear = [None] * n
    s.top = 0
    slot_of = [(-k) % n for k in range(n)]
    for k, kind in enumerate(arrival):
        if kind is not None:
            s.gear[slot_of[k]] = Part(next(uid), kind)
    s.hand, s.discard = [], []
    s.queue = [Part(next(uid), kind) for kind in queue]
    s.enemy_hp = 999
    return s, slot_of


UNLOCKED = RulesConfig(crank_direction_lock=False)


def free_crank(s, direction=None):
    apply(s, ("end_install",) if direction is None else ("end_install", direction))


class HeatAndExample(unittest.TestCase):
    def test_rules_section_8_example(self):
        # Rules.md §8. The listed order is the order parts reach the top.
        s, _ = setup([CO, SP, SP, H, A, P])
        free_crank(s)
        self.assertEqual(999 - s.enemy_hp, 22)          # 15 * 1.5, rounded down
        self.assertEqual(s.heat, 8)                     # Spring 2 + Spring 3 + Hammer 3
        self.assertEqual(s.triggers_turn, 3)

    def test_every_trigger_adds_one_plus_extras(self):
        s, _ = setup([None, S, H])
        free_crank(s)
        self.assertEqual(s.heat, 1)
        apply(s, ("crank",))
        self.assertEqual(s.heat, 4)

    def test_empty_trigger_point_does_nothing(self):
        s, _ = setup([S, None])
        free_crank(s)
        self.assertEqual((s.heat, s.triggers_turn), (0, 0))

    def test_spring_chain_escalates_then_overheat_stops_turn(self):
        s, _ = setup([None, SP, SP, SP, P, S])
        free_crank(s)
        # Springs 2 + 3 + 4 = 9, Plate +1 = 10 -> Plate's Block still resolves, then Overheat.
        self.assertEqual(s.block, 6)
        self.assertEqual(s.heat, 0)
        self.assertEqual(s.stats.overheats, 1)
        self.assertEqual(s.enemy_hp, 999)               # the Striker after it never triggered
        self.assertEqual(legal_actions(s), [("end_turn",)])
        apply(s, ("end_turn",))
        self.assertTrue(s.dead_turn)
        top_before = s.top
        free_crank(s)                                   # dead turn: no free crank
        self.assertEqual(s.top, top_before)
        self.assertEqual(legal_actions(s), [("end_turn",)])
        apply(s, ("end_turn",))
        self.assertFalse(s.dead_turn)

    def test_chain_resets_per_player_crank(self):
        s, _ = setup([None, SP, None, SP])
        free_crank(s)                                   # Spring (2), cranks onto empty
        self.assertEqual(s.heat, 2)
        apply(s, ("crank",))                            # new chain: first Spring again
        self.assertEqual(s.heat, 4)

    def test_coolant(self):
        s, _ = setup([None, S, CO], rules=UNLOCKED)
        s.heat = 5
        free_crank(s)
        apply(s, ("crank",))
        self.assertEqual(s.heat, 4)                     # 5 + 1 + 1 - 3
        s.heat, s.crank_power = 0, 2
        apply(s, ("crank_back",))                       # back onto the Striker: Heat 1
        apply(s, ("crank",))                            # Coolant at Heat 1: +1 -3, floored at 0
        self.assertEqual(s.heat, 0)


class Amplifier(unittest.TestCase):
    def test_two_amplifiers_add_up(self):
        s, _ = setup([A, S, A])                        # Striker between two Amplifiers
        free_crank(s)
        self.assertEqual(999 - s.enemy_hp, 12)

    def test_block_and_rounding(self):
        s, _ = setup([None, P, A])
        free_crank(s)
        self.assertEqual(s.block, 9)

    def test_amplifier_does_not_trigger(self):
        s, _ = setup([None, A])
        free_crank(s)
        self.assertEqual((s.heat, s.triggers_turn), (0, 0))


class CouplerAndMirror(unittest.TestCase):
    def test_coupler_depth_first_left_then_right(self):
        # Arrival order: Plate is at the top, Coupler comes up next. Coupler's left neighbour
        # (the next to arrive) is a Spring, its right neighbour is the Plate.
        s, _ = setup([P, C, SP, S])
        free_crank(s)
        order = [line.split()[0] for line in s.log if "triggers" in line]
        self.assertEqual(order, ["Coupler#101", "Spring#102", "Spring#102", "Striker#103", "Plate#100"])
        # Coupler 1 + Spring 2 + Spring 3 + Striker 1 + Plate 1
        self.assertEqual(s.heat, 8)
        self.assertEqual((999 - s.enemy_hp, s.block), (6, 6))

    def test_coupler_cannot_trigger_coupler(self):
        s, _ = setup([None, C, C, S])
        free_crank(s)
        self.assertEqual(s.triggers_turn, 1)

    def test_coupler_can_trigger_coupler_when_allowed(self):
        s, _ = setup([None, C, C, S], rules=RulesConfig(coupler_can_trigger_coupler=True))
        free_crank(s)
        self.assertGreater(s.triggers_turn, 1)

    def test_mirror_acts_as_opposite_part_in_its_place(self):
        # Mirror next to an Amplifier copies the Striker opposite: amplified by the Mirror's neighbour.
        s, _ = setup([None, M, A, None, S, None])
        free_crank(s)
        self.assertEqual(999 - s.enemy_hp, 9)
        self.assertEqual(s.heat, 1)

    def test_mirror_copying_hammer_costs_hammer_heat(self):
        s, _ = setup([None, M, None, None, H, None])
        free_crank(s)
        self.assertEqual((999 - s.enemy_hp, s.heat), (15, 3))

    def test_mirror_cannot_copy_mirror_or_empty(self):
        s, _ = setup([None, M, None, None, M, None])
        free_crank(s)
        self.assertEqual((s.heat, s.triggers_turn), (0, 0))
        s, _ = setup([None, M])
        free_crank(s)
        self.assertEqual((s.heat, s.triggers_turn), (0, 0))

    def test_mirror_copying_spring_cranks(self):
        s, _ = setup([None, M, S, None, SP, None])
        free_crank(s)
        self.assertEqual(999 - s.enemy_hp, 6)

    def test_coupler_mirror_loop_is_blocked(self):
        # Coupler A comes up; its left neighbour is Mirror M, whose opposite is Coupler B.
        # M acts as a Coupler, so A can't trigger it.
        s, slot = setup([None, C, M, None, None, C])
        free_crank(s)
        self.assertEqual(s.triggers_turn, 1)


class Cranking(unittest.TestCase):
    def test_backward_crank_triggers_and_costs_power(self):
        s, _ = setup([S, None, None, None, None, P], rules=UNLOCKED)
        free_crank(s)                                   # onto empty
        apply(s, ("crank_back",))                       # back to the Striker
        self.assertEqual((s.crank_power, 999 - s.enemy_hp), (1, 6))
        apply(s, ("crank_back",))                       # the Plate is next going backward
        self.assertEqual((s.crank_power, s.block), (0, 6))
        self.assertNotIn(("crank_back",), legal_actions(s))

    def test_spring_follows_backward_crank(self):
        # Going backward from the top: Spring, then Striker. The Spring keeps cranking backward.
        s, _ = setup([None, None, None, None, S, SP], rules=UNLOCKED)
        s.phase, s.crank_power = "crank", 1
        apply(s, ("crank_back",))
        self.assertEqual(999 - s.enemy_hp, 6)

    def test_direction_lock_offers_both_directions_then_one(self):
        s, _ = setup([None, S])
        self.assertIn(("end_install", engine.CW), legal_actions(s))
        self.assertIn(("end_install", engine.CCW), legal_actions(s))
        free_crank(s, engine.CW)
        self.assertEqual(legal_actions(s), [("crank",), ("end_turn",)])
        self.assertRaises(ValueError, apply, s, ("crank_back",))

    def test_counter_clockwise_turn(self):
        # Going backward from the top: Plate, then Striker. Free and paid cranks both go that way.
        s, _ = setup([None, None, None, None, S, P])
        free_crank(s, engine.CCW)
        self.assertEqual(s.block, 6)
        apply(s, ("crank",))
        self.assertEqual(999 - s.enemy_hp, 6)

    def test_spring_follows_counter_clockwise_turn(self):
        s, _ = setup([None, None, None, None, S, SP])
        free_crank(s, engine.CCW)
        self.assertEqual(999 - s.enemy_hp, 6)

    def test_no_back_and_forth_pendulum(self):
        # Striker > Spring > Striker: unlocked, the Spring fires on every crank; locked, it can't repeat.
        s, _ = setup([None, SP, S, None, None, S], rules=UNLOCKED)
        free_crank(s)
        apply(s, ("crank_back",))
        apply(s, ("crank",))
        self.assertGreater(max(s.part_triggers.values()), 2)
        best = max(max(e.part_triggers.values(), default=0)
                   for _, e in turn_outcomes(setup([None, SP, S, None, None, S])[0]))
        self.assertLessEqual(best, 2)

    def test_dead_turn_has_single_end_install(self):
        s, _ = setup([None])
        s.dead_turn = True
        self.assertEqual([a for a in legal_actions(s) if a[0] == "end_install"], [("end_install",)])

    def test_install_into_top_does_not_trigger_and_replace_discards(self):
        s, slot = setup([S])
        s.hand = [Part(1, P)]
        apply(s, ("install", 0, slot[0]))
        self.assertEqual((s.triggers_turn, s.block), (0, 0))
        self.assertEqual([p.kind for p in s.discard], [S])
        self.assertEqual(s.gear[slot[0]].kind, P)


class UtilityParts(unittest.TestCase):
    def test_magnet_pulls_both_sides(self):
        s, slot = setup([None, MG, None, S, P, None])
        # Magnet at arrival 1: left side is arrival 2 (empty) <- arrival 3 (Striker);
        # right side is arrival 0 (empty) <- arrival 5 (empty). Add a part there.
        s.gear[slot[5]] = Part(50, P)
        free_crank(s)
        self.assertEqual(s.gear[slot[2]].kind, S)
        self.assertEqual(s.gear[slot[0]].kind, P)
        self.assertIsNone(s.gear[slot[3]])
        self.assertIsNone(s.gear[slot[5]])

    def test_magnet_does_not_pull_into_occupied(self):
        s, slot = setup([P, MG, P, S, None, None])
        free_crank(s)
        self.assertEqual(s.gear[slot[3]].kind, S)

    def test_loader_installs_next_part_in_queue(self):
        s, slot = setup([None, L], queue=[H, S])
        free_crank(s)
        self.assertEqual([p.kind for p in s.queue], [S])
        self.assertIn(H, [p.kind for p in s.gear if p is not None])

    def test_loader_recycles_when_queue_empty(self):
        s, _ = setup([None, L])
        s.discard = [Part(60, S)]
        free_crank(s)
        self.assertEqual(s.stats.reshuffles, 1)
        self.assertEqual(sum(p is not None for p in s.gear), 2)

    def test_reshuffle_heat_curve(self):
        s, _ = setup([None])
        s.heat = 0
        for expected in (0, 1, 3):           # +0, +1, +2
            s.discard = [Part(70, S)]
            engine._recycle(s)
            self.assertEqual(s.heat, expected)


class EnemiesAndCaps(unittest.TestCase):
    def test_jam_lasts_two_turns(self):
        s, slot = setup([None, S, None, None, None, None])
        s.intent = (("jam", slot[1], 2),)
        apply(s, ("end_install",))
        s.enemy_hp = 999                     # Striker hit; reset
        apply(s, ("end_turn",))
        for _ in range(2):
            s.top = slot[0]
            s.intent = ()
            free_crank(s)
            self.assertEqual(s.enemy_hp, 999)
            apply(s, ("end_turn",))
        s.top = slot[0]
        free_crank(s)
        self.assertEqual(s.enemy_hp, 993)

    def test_wind_back(self):
        s, slot = setup([None, S])
        s.intent = (("wind_back",),)
        free_crank(s)
        apply(s, ("end_turn",))
        self.assertEqual(s.top, slot[0])

    def test_clock_tower_limit(self):
        s, _ = setup([None, SP, SP, SP, SP, SP], enemy="clock_tower")
        s.cranks_used = 10
        free_crank(s)
        self.assertEqual(s.cranks_used, 12)
        apply(s, ("end_turn",))
        self.assertEqual((s.result, s.reason), ("loss", "clock tower struck"))

    def test_turn_cap_option(self):
        rules = RulesConfig(max_triggers_per_turn=2)
        s, _ = setup([None, SP, SP, SP, S], rules=rules)
        free_crank(s)
        self.assertEqual(s.triggers_turn, 2)

    def test_safety_cap_flags_runaway(self):
        # Couplers allowed to chain, with Coolants keeping Heat down: an unbounded loop.
        rules = RulesConfig(coupler_can_trigger_coupler=True, safety_triggers_per_turn=50)
        s, _ = setup([None, C, C, CO, CO, CO], rules=rules)
        free_crank(s)
        apply(s, ("end_turn",))
        self.assertEqual(s.stats.runaway_turns, 1)


class Fuzz(unittest.TestCase):
    def test_random_play_invariants(self):
        for deck, enemy in itertools.product(DECKS, ENEMIES):
            size = len(deck_list(DECKS[deck]))
            for seed in range(15):
                s = new_fight(DECKS[deck], enemy, seed=seed)
                agent = RandomAgent(seed)
                while s.result is None:
                    acts = legal_actions(s)
                    self.assertTrue(acts)
                    apply(s, agent.act(s, acts))
                    on_gear = sum(p is not None for p in s.gear)
                    self.assertEqual(on_gear + len(s.queue) + len(s.discard) + len(s.hand), size)
                    if s.result is None:   # a winning trigger can end the fight at 10+
                        self.assertTrue(0 <= s.heat < s.rules.overheat_at)
                self.assertEqual(legal_actions(s), [])

    def test_clone_is_independent_and_deterministic(self):
        s = new_fight(DECKS["utility"], "saboteur", seed=4)
        agent = RandomAgent(1)
        for _ in range(10):
            apply(s, agent.act(s, legal_actions(s)))
        a, b = s.clone(), s.clone()
        for _ in range(500):
            if a.result is not None:
                break
            act = RandomAgent(len(a.stats.damage_by_turn)).act(a, legal_actions(a))
            apply(a, act)
            apply(b, act)
        self.assertEqual(engine.summary(a), engine.summary(b))
        self.assertNotEqual(engine.summary(a), engine.summary(s))


if __name__ == "__main__":
    unittest.main()
