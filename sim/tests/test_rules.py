import itertools
import unittest
from dataclasses import replace as dc_replace

from clockwork import RulesConfig, apply, legal_actions, new_fight
from clockwork import engine
from clockwork.search import turn_outcomes
from clockwork.agents.random_agent import RandomAgent
from clockwork.decks import DECKS, deck_list
from clockwork.enemies import ENEMIES
from clockwork.parts import Kind as K, Mod, Part
from clockwork.enemies import EnemySpec

S, P, SP, M, A, C, L, CO, H, MG = (K.STRIKER, K.PLATE, K.SPRING, K.MIRROR, K.AMPLIFIER,
                                    K.COUPLER, K.LOADER, K.COOLANT, K.HAMMER, K.MAGNET)


# Mechanics tests pin the numbers they were written against, so balance passes that change
# defaults don't break them. Balance values themselves are checked in BalanceDefaults below.
MECH = RulesConfig(amplifier_bonus=0.5, polish_bonus=0.5, clamp_max_triggers=2, loader_loads=1,
                  loader_replaces=False, magnet_block_per_pull=0, coil_damage=4, bracing_damage=0,
                  bracing_block=0, feeder_extra_loads=0, feeder_triggers=0, part_overrides=(
    ("Slider", "moved_bonus", 6),
    ("Primer", "damage", 4), ("Primer", "fresh_damage", 18),
    ("Assembly", "per_part_damage", 1), ("Assembly", "per_install_damage", 2),
    ("Coupler", "extra_heat", 0), ("Spring", "block", 0), ("Loader", "block", 0),
    ("Coupler", "damage", 0), ("Assembly", "damage", 0)))


def mech(**kw):
    """MECH with some fields changed; part_overrides are appended."""
    extra = kw.pop("part_overrides", ())
    return dc_replace(MECH, part_overrides=MECH.part_overrides + tuple(extra), **kw)


def setup(arrival, enemy="dummy", rules=MECH, queue=()):
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


UNLOCKED = mech(crank_direction_lock=False)
# Rules.md's original Hammer (15 damage, +2 Heat), for tests written against the rules text.
RULES_MD = mech(part_overrides=(("Hammer", "damage", 15), ("Hammer", "extra_heat", 2)))


def free_crank(s, direction=None):
    apply(s, ("end_install",) if direction is None else ("end_install", direction))


class HeatAndExample(unittest.TestCase):
    def test_rules_section_8_example(self):
        # Rules.md §8. The listed order is the order parts reach the top.
        s, _ = setup([CO, SP, SP, H, A, P], rules=RULES_MD)
        free_crank(s)
        self.assertEqual(999 - s.enemy_hp, 22)          # 15 * 1.5, rounded down
        self.assertEqual(s.heat, 8)                     # Spring 2 + Spring 3 + Hammer 3
        self.assertEqual(s.triggers_turn, 3)

    def test_part_overrides(self):
        rules = mech(part_overrides=(("Hammer", "damage", 10), ("Hammer", "extra_heat", 4)))
        s, _ = setup([None, H], rules=rules)
        free_crank(s)
        self.assertEqual((999 - s.enemy_hp, s.heat), (10, 5))

    def test_every_trigger_adds_one_plus_extras(self):
        s, _ = setup([None, S, H], rules=RULES_MD)
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
        s, _ = setup([None, C, C, S], rules=mech(coupler_can_trigger_coupler=True))
        free_crank(s)
        self.assertGreater(s.triggers_turn, 1)

    def test_mirror_acts_as_opposite_part_in_its_place(self):
        # Mirror next to an Amplifier copies the Striker opposite: amplified by the Mirror's neighbour.
        s, _ = setup([None, M, A, None, S, None])
        free_crank(s)
        self.assertEqual(999 - s.enemy_hp, 9)
        self.assertEqual(s.heat, 1)

    def test_mirror_copying_hammer_costs_hammer_heat(self):
        s, _ = setup([None, M, None, None, H, None], rules=RULES_MD)
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

    def test_magnet_does_not_pull_into_occupied_without_swaps(self):
        s, slot = setup([P, MG, P, S, None, None], rules=mech(magnet_swaps=False))
        free_crank(s)
        self.assertEqual(s.gear[slot[3]].kind, S)

    def test_magnet_swaps_into_occupied(self):
        s, slot = setup([None, MG, P, S, None, None])
        free_crank(s)
        self.assertEqual((s.gear[slot[2]].kind, s.gear[slot[3]].kind), (S, P))
        self.assertEqual(len(s.moved), 2)

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


class PayoffParts(unittest.TestCase):
    def test_primer_fresh_then_weak(self):
        s, slot = setup([None, None, K.STRIKER])
        s.hand = [Part(1, K.PRIMER)]
        apply(s, ("install", 0, slot[1]))
        free_crank(s)
        self.assertEqual(999 - s.enemy_hp, 18)
        apply(s, ("end_turn",))
        s.top = slot[0]
        free_crank(s)
        self.assertEqual(999 - s.enemy_hp, 22)          # 18 + 4

    def test_primer_loaded_is_fresh(self):
        s, slot = setup([None, L, None], queue=[K.PRIMER])
        free_crank(s)
        self.assertEqual(s.queue, [])
        loaded = next(p for p in s.gear if p is not None and p.kind == K.PRIMER)
        self.assertIn(loaded.uid, s.fresh)

    def test_assembly_counts_parts(self):
        s, _ = setup([P, K.ASSEMBLY, S, None, P, None])
        free_crank(s)
        self.assertEqual(999 - s.enemy_hp, 4)           # 4 parts on the gear x 1

    def test_assembly_counts_installs_this_turn(self):
        s, slot = setup([P, K.ASSEMBLY, None, None, None, None])
        s.hand = [Part(1, S), Part(2, S)]
        apply(s, ("install", 0, slot[2]))
        apply(s, ("install", 0, slot[3]))
        free_crank(s)
        self.assertEqual(999 - s.enemy_hp, 4 + 2 * 2)   # 4 parts, 2 of them installed this turn

    def test_primer_bonus_only_on_install_turn(self):
        s, slot = setup([None, None, None])
        s.hand = [Part(1, K.PRIMER)]
        apply(s, ("install", 0, slot[2]))               # comes up on the 2nd crank; no crank this turn
        free_crank(s)
        apply(s, ("end_turn",))
        s.top = slot[1]
        free_crank(s)
        self.assertEqual(999 - s.enemy_hp, 4)           # next turn it is no longer armed

    def test_slider_moved_bonus(self):
        # Magnet comes up first and pulls the Slider (2 slots away) next to it; the next crank hits it.
        s, slot = setup([None, MG, None, K.SLIDER, None, None])
        free_crank(s)
        self.assertEqual(s.gear[slot[2]].kind, K.SLIDER)
        apply(s, ("crank",))
        self.assertEqual(999 - s.enemy_hp, 11)          # 5 + 6


class Attachments(unittest.TestCase):
    def test_deck_rejects_wrong_attachment(self):
        with self.assertRaises(ValueError):
            new_fight({(K.STRIKER, Mod.COIL): 1})

    def test_coil_adds_damage_to_triggered_part(self):
        s, slot = setup([None, None, P])
        s.gear[slot[1]] = Part(50, SP, Mod.COIL)
        free_crank(s)
        self.assertEqual((s.block, 999 - s.enemy_hp), (6, 4))   # the Plate also deals 4

    def test_coil_bonus_lost_on_empty(self):
        s, slot = setup([None, None, None])
        s.gear[slot[1]] = Part(50, SP, Mod.COIL)
        free_crank(s)
        self.assertEqual(s.enemy_hp, 999)

    def test_polish_mirror(self):
        s, slot = setup([None, None, None, None, S, None])
        s.gear[slot[1]] = Part(50, M, Mod.POLISH)
        free_crank(s)
        self.assertEqual(999 - s.enemy_hp, 9)           # 6 * 1.5

    def test_clamp_triggers_pulled_parts(self):
        s, slot = setup([None, None, None, S, None, P])
        s.gear[slot[1]] = Part(50, MG, Mod.CLAMP)
        free_crank(s)
        # Pulls the Striker (left side) and the Plate (right side), then triggers both.
        self.assertEqual((999 - s.enemy_hp, s.block), (6, 6))
        self.assertEqual(s.triggers_turn, 3)

    def test_clamp_with_slider(self):
        s, slot = setup([None, None, None, K.SLIDER, None, None])
        s.gear[slot[1]] = Part(50, MG, Mod.CLAMP)
        free_crank(s)
        self.assertEqual(999 - s.enemy_hp, 11)

    def test_feeder_loads_next_slot_to_come_up(self):
        s, slot = setup([None, None, None, P, None, None], queue=[S])
        s.gear[slot[1]] = Part(50, L, Mod.FEEDER)
        free_crank(s)
        self.assertEqual(s.gear[slot[2]].kind, S)       # next to arrive on a clockwise turn
        apply(s, ("crank",))
        self.assertEqual(999 - s.enemy_hp, 6)

    def test_feeder_follows_counter_clockwise_turn(self):
        s, slot = setup([None, None, P, None, None, None], queue=[S])
        s.gear[slot[5]] = Part(50, L, Mod.FEEDER)
        free_crank(s, engine.CCW)                       # the Loader (arrival 5) comes up going back
        self.assertEqual(s.gear[slot[4]].kind, S)

    def test_mirror_copies_attachment(self):
        s, slot = setup([None, M, P, None, None, None])
        s.gear[slot[4]] = Part(50, SP, Mod.COIL)        # opposite the Mirror
        free_crank(s)
        self.assertEqual((s.block, 999 - s.enemy_hp), (6, 4))


class BalanceDefaults(unittest.TestCase):
    def test_clamp_triggers_one_pulled_part_by_default(self):
        s, slot = setup([None, None, None, S, None, P], rules=RulesConfig())
        s.gear[slot[1]] = Part(50, MG, Mod.CLAMP)
        free_crank(s)
        self.assertEqual((999 - s.enemy_hp, s.block), (6, 12))  # only the Striker triggers; 12 Block from 2 pulls

    def test_part_pass_v15(self):
        from clockwork.parts import SPECS
        self.assertEqual((SPECS[K.HAMMER].damage, SPECS[K.HAMMER].extra_heat), (10, 3))
        self.assertEqual((SPECS[K.SPRING].block, SPECS[K.LOADER].block), (3, 3))

    def test_default_numbers(self):
        s, _ = setup([None, S, A], rules=RulesConfig())
        free_crank(s)
        self.assertEqual(999 - s.enemy_hp, 7)                    # 6 * 1.3, rounded down


class LoaderTwoLoads(unittest.TestCase):
    def test_loader_loads_two_by_default(self):
        s, slot = setup([None, L, None, None, None, None], rules=RulesConfig(), queue=[S, P, S])
        free_crank(s)
        self.assertEqual([p.kind for p in s.queue], [S])
        self.assertEqual(sum(p is not None for p in s.gear), 3)

    def test_feeder_loads_next_two_slots(self):
        s, slot = setup([None, None, None, None, None, None], rules=RulesConfig(), queue=[S, P])
        s.gear[slot[1]] = Part(50, L, Mod.FEEDER)
        free_crank(s)
        self.assertEqual((s.gear[slot[2]].kind, s.gear[slot[3]].kind), (S, P))

    def test_second_load_stops_when_gear_full(self):
        s, slot = setup([S, L, S, S, S, None], rules=RulesConfig(loader_replaces=False), queue=[P, P])
        free_crank(s)
        self.assertEqual(len(s.queue), 1)


class LoaderReplacesAndMagnetBlock(unittest.TestCase):
    def test_full_gear_loader_replaces_opposite(self):
        s, slot = setup([S, L, S, P, S, S], rules=RulesConfig(), queue=[H, H])
        free_crank(s)
        self.assertEqual(s.gear[slot[4]].kind, H)        # opposite the Loader (arrival 1 -> 4)
        self.assertEqual([p.kind for p in s.discard], [S])
        self.assertEqual(len(s.queue), 1)                # only one replacement per trigger

    def test_feeder_replaces_next_to_come_up(self):
        s, slot = setup([S, None, S, P, S, S], rules=RulesConfig(), queue=[H])
        s.gear[slot[1]] = Part(50, L, Mod.FEEDER)
        free_crank(s)
        self.assertEqual(s.gear[slot[2]].kind, H)
        self.assertEqual([p.kind for p in s.discard], [S])

    def test_loader_fills_empty_before_replacing(self):
        s, slot = setup([S, L, S, P, None, S], rules=RulesConfig(), queue=[H, H, H])
        free_crank(s)
        self.assertEqual(s.gear[slot[4]].kind, H)        # empty slot first (it is also the opposite slot)
        self.assertEqual(s.discard, [])                  # the 2nd load won't replace what the 1st just loaded
        self.assertEqual(len(s.queue), 2)

    def test_magnet_block_per_pull(self):
        s, slot = setup([None, MG, None, S, None, P], rules=RulesConfig())
        free_crank(s)
        self.assertEqual(s.block, 12)                    # 2 parts pulled x 6


class ClockTowerChime(unittest.TestCase):
    def tower(self, arrival, cranks_used):
        s, slot = setup(arrival, enemy="clock_tower", rules=MECH)
        s.cranks_used = cranks_used
        return s, slot

    def test_chime_on_every_4th_crank_after_the_arriving_part(self):
        s, _ = self.tower([None, P, S], cranks_used=3)
        free_crank(s)                                    # crank 4: the Plate triggers, then the chime
        self.assertEqual((s.stats.chimes, s.stats.chime_blocked), (1, 6))
        self.assertEqual(s.hp, 55 - (s.enemy.chime_damage - 6))   # the Plate's 6 Block absorbs part
        apply(s, ("crank",))                             # crank 5: no chime
        self.assertEqual(s.stats.chimes, 1)

    def test_chime_still_strikes_after_overheat(self):
        s, _ = self.tower([None, H], cranks_used=3)
        s.heat = 8
        free_crank(s)
        self.assertEqual((s.stats.overheats, s.stats.chimes), (1, 1))

    def test_chime_can_kill(self):
        s, _ = self.tower([None, S], cranks_used=3)
        s.hp = 10
        free_crank(s)
        self.assertEqual((s.result, s.reason), ("loss", "hp"))

    def test_spring_cranks_count(self):
        s, _ = self.tower([None, SP, S], cranks_used=2)
        free_crank(s)                                    # cranks 3 (Spring) and 4 (Striker) -> chime
        self.assertEqual(s.stats.chimes, 1)


class NewAttachmentsAndElites(unittest.TestCase):
    def one(self, kind, mods, arrival_rest=(), **kw):
        s, slot = setup([None, None] + list(arrival_rest), **kw)
        s.gear[slot[1]] = Part(77, kind, mods)
        return s, slot

    def test_sharpened_and_counterweight(self):
        s, _ = self.one(S, Mod.SHARPENED)
        free_crank(s)
        self.assertEqual(999 - s.enemy_hp, 8)
        s, _ = self.one(P, (Mod.SHARPENED, Mod.COUNTERWEIGHT))
        free_crank(s)
        self.assertEqual((999 - s.enemy_hp, s.block), (2, 8))

    def test_heat_sink_and_governor(self):
        s, _ = self.one(H, Mod.HEAT_SINK, rules=RULES_MD)
        free_crank(s)
        self.assertEqual(s.heat, 2)                      # Hammer 3 Heat - 1
        s, _ = self.one(H, Mod.GOVERNOR, rules=RULES_MD)
        free_crank(s)
        self.assertEqual(s.heat, 0)

    def test_echo_once_per_turn(self):
        s, _ = self.one(S, Mod.ECHO)
        free_crank(s)
        self.assertEqual((999 - s.enemy_hp, s.heat), (12, 2))
        s.crank_power = 2
        apply(s, ("crank",))                             # onto the empty slot
        s.top = (s.top + 1) % 6                          # put the Echo Striker back on top by hand
        s.stack = None
        engine._resolve(s, [("trigger", s.top, engine.CW, False, None, 0)])
        self.assertEqual(999 - s.enemy_hp, 18)           # no second echo this turn

    def test_two_attachments_stack(self):
        s, _ = self.one(S, (Mod.SHARPENED, Mod.ECHO))
        free_crank(s)
        self.assertEqual(999 - s.enemy_hp, 16)

    def test_bracing_ignores_jam_unscrew_rust(self):
        s, slot = self.one(S, Mod.BRACING)
        s.jams[slot[1]] = 2
        free_crank(s)
        self.assertEqual(999 - s.enemy_hp, 6)            # jammed slot, but Bracing
        s.intent = (("unscrew", slot[1]), ("rust", 2))
        apply(s, ("end_turn",))
        self.assertIsNotNone(s.gear[slot[1]])
        self.assertEqual(s.rust, {})

    def test_bracing_v12_adds_damage_and_block(self):
        s, _ = self.one(S, Mod.BRACING, rules=dc_replace(MECH, bracing_damage=1, bracing_block=1))
        free_crank(s)
        self.assertEqual((999 - s.enemy_hp, s.block), (7, 1))

    def test_feeder_v12_loaded_parts_trigger(self):
        rules = dc_replace(MECH, loader_loads=2, feeder_extra_loads=1, feeder_triggers=3)
        s, slot = setup([None, None, None, None, None, None], queue=[S, P, S], rules=rules)
        s.gear[slot[1]] = Part(50, L, Mod.FEEDER)
        free_crank(s)
        # Loads 3 parts into the next slots to come up, and each triggers right away.
        self.assertEqual([s.gear[slot[k]].kind for k in (2, 3, 4)], [S, P, S])
        self.assertEqual((999 - s.enemy_hp, s.block, s.triggers_turn), (12, 6, 4))

    def test_rust_weakens_top_part_for_the_fight(self):
        s, slot = self.one(S, ())
        free_crank(s)                                    # Striker now at the top
        s.intent = (("rust", 2),)
        apply(s, ("end_turn",))
        self.assertEqual(s.rust, {77: 2})
        s.top = slot[0]
        s.enemy_hp = 999
        free_crank(s)
        self.assertEqual(999 - s.enemy_hp, 4)

    def test_overclock_adds_heat_and_can_overheat(self):
        s, _ = setup([None])
        free_crank(s)
        s.heat, s.intent = 8, (("overclock", 3),)
        apply(s, ("end_turn",))
        self.assertTrue(s.dead_turn)
        self.assertEqual(s.heat, 0)

    def test_deck_with_two_attachments(self):
        s = new_fight({(S, (Mod.SHARPENED, Mod.ECHO)): 1, P: 1}, "dummy", seed=0)
        parts = s.hand + s.queue
        self.assertIn((Mod.ECHO, Mod.SHARPENED), [p.mods for p in parts])
        with self.assertRaises(ValueError):
            new_fight({(S, (Mod.SHARPENED, Mod.SHARPENED)): 1})


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

    def test_crank_limit_rule(self):
        # The old Clock Tower rule (12 cranks, then instant loss) is still available as an option.
        old_tower = EnemySpec("old_tower", 50, ((("attack", 6),),), crank_limit=12)
        s, _ = setup([None, SP, SP, SP, SP, SP], enemy=old_tower)
        s.cranks_used = 10
        free_crank(s)
        self.assertEqual(s.cranks_used, 12)
        apply(s, ("end_turn",))
        self.assertEqual((s.result, s.reason), ("loss", "clock tower struck"))

    def test_turn_cap_option(self):
        rules = mech(max_triggers_per_turn=2)
        s, _ = setup([None, SP, SP, SP, S], rules=rules)
        free_crank(s)
        self.assertEqual(s.triggers_turn, 2)

    def test_safety_cap_flags_runaway(self):
        # Couplers allowed to chain, with Coolants keeping Heat down: an unbounded loop.
        rules = mech(coupler_can_trigger_coupler=True, safety_triggers_per_turn=50)
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



class NewBosses(unittest.TestCase):
    def test_armor_reduces_every_hit(self):
        s, _ = setup([None, S], enemy=EnemySpec("armored", 999, ((("attack", 1),),), armor=3))
        free_crank(s)
        self.assertEqual(999 - s.enemy_hp, 3)            # 6 - 3

    def test_swing_forces_turn_direction(self):
        s = new_fight(DECKS["starter"], EnemySpec("swinger", 99, ((("attack", 1),),), swing=True), seed=0)
        ends = [a for a in legal_actions(s) if a[0] == "end_install"]
        self.assertEqual(ends, [("end_install", engine.CW)])     # turn 1: clockwise
        with self.assertRaises(ValueError):
            apply(s, ("end_install", engine.CCW))
        apply(s, ("end_install", engine.CW))
        apply(s, ("end_turn",))
        ends = [a for a in legal_actions(s) if a[0] == "end_install"]
        self.assertTrue(s.dead_turn or ends == [("end_install", engine.CCW)])

    def test_dismantler_unscrews_two_different_parts(self):
        from clockwork.enemies import reveal_intent
        import random
        gear = [Part(i, S) for i in range(6)]
        for seed in range(20):
            intent = reveal_intent(ENEMIES["dismantler"], 1, gear, random.Random(seed))
            slots = [a[1] for a in intent if a[0] == "unscrew"]
            self.assertEqual(len(set(slots)), 2)


if __name__ == "__main__":
    unittest.main()
