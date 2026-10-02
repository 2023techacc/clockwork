"""Stage 2: determinized MCTS over whole-turn plans.

Each decision:
1. Sample `worlds` determinizations: the unseen part of the queue is reshuffled and the
   random number generator reseeded, so nothing hidden is peeked at.
2. In each world, grow a search tree whose moves are complete turn plans (installs and
   cranks up to end of turn). Moves are added to a node in order of the greedy heuristic
   (progressive widening) and chosen with UCB1.
3. New leaves are valued by playing the fight out with a fast sampled-greedy policy.
4. Root visit counts are summed across worlds; the most-visited plan is played.

Rewards: a win scores 0.7-1.0 (more HP left is better), a loss or unfinished fight scores
0-0.5 by how much of the enemy's HP was removed.
"""
import math
import random

from ..engine import apply, legal_actions
from ..search import after_installs, gear_key, turn_outcomes
from .greedy_agent import GreedyAgent

_SCORER = GreedyAgent()


def reward(s) -> float:
    if s.result == "win":
        return 0.7 + 0.3 * max(0, s.hp) / s.rules.player_hp
    return 0.5 * (1 - max(0, s.enemy_hp) / s.enemy.hp)


def end_key(s) -> tuple:
    return (gear_key(s), s.top, s.heat, s.block, s.enemy_hp, s.overheat_pending, s.result,
            tuple(sorted(p.kind.value for p in s.discard)), tuple(sorted(s.jams.items())))


def ranked_outcomes(s, outcomes):
    """Dedupe (plan, end) pairs by end state and sort by greedy score, best first."""
    best = {}
    for plan, end in outcomes:
        k = end_key(end)
        sc = _SCORER.score(s, end)
        if k not in best or sc > best[k][0]:
            best[k] = (sc, plan, end)
    return [(plan, end) for sc, plan, end in sorted(best.values(), key=lambda x: -x[0])]


def sampled_outcomes(s, rng, samples):
    """A cheap subset of this turn's outcomes: no installs plus `samples` random install sequences,
    each with every way to spend Crank Power."""
    seqs, seen = [], set()
    for i in range(samples + 1):
        cur, acts = s.clone(), []
        n = 0 if i == 0 else rng.randint(1, s.installs_left)
        for _ in range(n):
            options = [a for a in legal_actions(cur) if a[0] == "install"]
            if not options:
                break
            a = rng.choice(options)
            apply(cur, a)
            acts.append(a)
        k = gear_key(cur)
        if k in seen:
            continue
        seen.add(k)
        seqs.append((acts, cur))
    for acts, cur in seqs:
        yield from after_installs(cur, acts)


def fast_turn(s, rng, samples):
    """Rollout policy: best of a sampled set of turn plans by the greedy heuristic."""
    best, best_sc = None, None
    for _, end in sampled_outcomes(s, rng, samples):
        sc = _SCORER.score(s, end)
        if best_sc is None or sc > best_sc:
            best, best_sc = end, sc
    return best


def end_turn(end):
    nxt = end.clone()
    if nxt.result is None:
        apply(nxt, ("end_turn",))
    return nxt


class _Node:
    __slots__ = ("state", "cands", "children", "n")

    def __init__(self, state):
        self.state = state
        self.cands = None      # ranked (plan, end) list, built on the node's second visit
        self.children = []     # _Edge list, in candidate order
        self.n = 0


class _Edge:
    __slots__ = ("plan", "node", "n", "w")

    def __init__(self, plan, node):
        self.plan, self.node, self.n, self.w = plan, node, 0, 0.0


class MCTSAgent:
    name = "mcts"

    def __init__(self, seed=0, budget=200, worlds=8, c=0.5, pw_c=1.5, pw_alpha=0.5,
                 rollout_samples=3, rollout_turns=15):
        self.rng = random.Random(seed)
        self.budget, self.worlds, self.c = budget, worlds, c
        self.pw_c, self.pw_alpha = pw_c, pw_alpha
        self.rollout_samples, self.rollout_turns = rollout_samples, rollout_turns
        self.plan = []
        self.last_root = None   # per-plan (visits, mean value) of the last decision, for inspection

    # --- determinization ---
    def determinize(self, state):
        world = state.clone()
        world.log = None
        visible = len(world.visible_queue())
        hidden = world.queue[visible:]
        self.rng.shuffle(hidden)
        world.queue = world.queue[:visible] + hidden
        world.rng.seed(self.rng.random())
        return world

    # --- search ---
    def rollout(self, s):
        s = s.clone()
        for _ in range(self.rollout_turns):
            if s.result is not None:
                break
            s = end_turn(fast_turn(s, self.rng, self.rollout_samples))
        return reward(s)

    def simulate(self, root):
        node, path = root, []
        while True:
            node.n += 1
            s = node.state
            if s.result is not None:
                value = reward(s)
                break
            if node.cands is None:
                node.cands = ranked_outcomes(s, sampled_outcomes(s, self.rng, 2 * self.rollout_samples))
            allowed = min(len(node.cands), math.ceil(self.pw_c * node.n ** self.pw_alpha))
            if len(node.children) < allowed:
                plan, end = node.cands[len(node.children)]
                if end is None:     # root plans are shared across worlds; replay in this one
                    end = s.clone()
                    for a in plan:
                        apply(end, a)
                edge = _Edge(plan, _Node(end_turn(end)))
                node.children.append(edge)
                path.append(edge)
                edge.node.n += 1
                value = self.rollout(edge.node.state)
                break
            log_n = math.log(node.n)
            edge = max(node.children,
                       key=lambda e: e.w / e.n + self.c * math.sqrt(log_n / e.n))
            path.append(edge)
            node = edge.node
        for edge in path:
            edge.n += 1
            edge.w += value

    def search(self, state):
        totals = {}
        per_world = max(1, self.budget // self.worlds)
        # Every world shares the same root plans (the hand and machine are known); rank them once.
        first = self.determinize(state)
        plans = [plan for plan, _ in ranked_outcomes(first, turn_outcomes(first))]
        for w in range(self.worlds):
            root = _Node(first if w == 0 else self.determinize(state))
            root.cands = [(plan, None) for plan in plans]
            for _ in range(per_world):
                self.simulate(root)
            for e in root.children:
                key = tuple(e.plan)
                n, w = totals.get(key, (0, 0.0))
                totals[key] = (n + e.n, w + e.w)
        self.last_root = {k: (n, w / n) for k, (n, w) in totals.items()}
        return max(totals, key=lambda k: (totals[k][0], totals[k][1] / totals[k][0]))

    def act(self, state, legal):
        if self.plan and self.plan[0] in legal:
            return self.plan.pop(0)
        self.plan = list(self.search(state)) + [("end_turn",)]
        if self.plan[0] not in legal:
            self.plan = []
            return legal[0]
        return self.plan.pop(0)
