import unittest

from clockwork.agents.greedy_agent import GreedyAgent
from clockwork.agents.random_agent import RandomAgent
from clockwork.engine import summary
from clockwork.loopfinder import _template, evaluate, layouts
from clockwork.config import DEFAULT_RULES
from clockwork.parts import Kind as K
from clockwork.run import play
from clockwork.search import turn_outcomes
from clockwork.decks import DECKS
from clockwork.engine import new_fight


class Search(unittest.TestCase):
    def test_turn_outcomes_leave_state_untouched_and_dedupe(self):
        s = new_fight(DECKS["starter"], "dummy", seed=1)
        before = summary(s), list(s.gear), list(s.hand)
        outs = list(turn_outcomes(s))
        self.assertEqual((summary(s), list(s.gear), list(s.hand)), before)
        gears = {tuple(p.kind if p else None for p in end.gear) for acts, end in outs if acts[-1] == ("end_install",)}
        self.assertEqual(len(gears), len([a for a, e in outs if a[-1] == ("end_install",)]))


class Agents(unittest.TestCase):
    def test_greedy_beats_random(self):
        def wins(agent_cls):
            return sum(summary(play("starter", "spiker", i, agent_cls(seed=i)))["result"] == "win"
                       for i in range(20))
        self.assertGreater(wins(GreedyAgent), wins(RandomAgent) + 5)

    def test_greedy_plays_legal_moves_on_every_deck(self):
        for deck in DECKS:
            s = play(deck, "saboteur", 3, GreedyAgent(seed=3))
            self.assertIsNotNone(s.result)


class LoopFinder(unittest.TestCase):
    def test_rules_example_layout(self):
        layout = (K.COOLANT, K.SPRING, K.SPRING, K.HAMMER, K.AMPLIFIER, K.PLATE)
        best_t, best_d = evaluate(layout, 0, _template(DEFAULT_RULES))
        self.assertGreaterEqual(best_d[1], 22)

    def test_layouts_respect_deck_counts(self):
        deck = {K.SPRING: 1, K.STRIKER: 2}
        for lay in layouts(deck, 4):
            self.assertLessEqual(lay.count(K.SPRING), 1)
            self.assertLessEqual(lay.count(K.STRIKER), 2)


if __name__ == "__main__":
    unittest.main()
