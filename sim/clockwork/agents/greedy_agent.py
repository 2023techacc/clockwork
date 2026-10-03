"""Stage 1: greedy. Searches every way to play the current turn and takes the one whose
end-of-turn state scores best on a hand-written heuristic. No look-ahead past this turn.

Hidden information is not peeked at: the search runs in a copy whose random number
generator is reseeded, so mid-turn shuffles and random Loader slots are guesses.
"""
import random

from ..search import turn_outcomes


class GreedyAgent:
    name = "greedy"

    def __init__(self, seed=0, w_block=1.0, w_heat=2.0, overheat_penalty=15.0, w_part=0.1):
        self.rng = random.Random(seed)
        self.w_block, self.w_heat = w_block, w_heat
        self.overheat_penalty, self.w_part = overheat_penalty, w_part
        self.plan = []

    def score(self, start, end):
        if end.result == "win":
            return 1e6
        incoming = sum(a[1] for a in end.intent if a[0] == "attack")
        score = (start.enemy_hp - end.enemy_hp
                 - (start.hp - end.hp)               # damage taken during the turn (Clock Tower chimes)
                 + self.w_block * min(end.block, incoming)
                 - self.w_heat * end.heat
                 + self.w_part * sum(p is not None for p in end.gear))
        if end.overheat_pending:
            score -= self.overheat_penalty
        if end.hp - max(0, incoming - end.block) <= 0:
            score -= 1e5                       # this line dies to the enemy's attack
        return score

    def act(self, state, legal):
        if self.plan and self.plan[0] in legal:
            return self.plan.pop(0)
        world = state.clone()
        world.log = None
        world.rng.seed(self.rng.random())
        best, best_score = None, None
        for acts, end in turn_outcomes(world):
            sc = self.score(world, end)
            if best_score is None or sc > best_score:
                best, best_score = acts, sc
        self.plan = list(best) + [("end_turn",)]
        if not self.plan or self.plan[0] not in legal:      # e.g. the fight already ended
            self.plan = []
            return legal[0]
        return self.plan.pop(0)
