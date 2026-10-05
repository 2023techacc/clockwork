"""Part balance pass (v15): what one pick of a part is worth, as win-rate points over the starter
deck in fights that start at 30 HP (typical mid-run HP), against every enemy, paired seeds.
Target: +3 to +10 (clockwork.targets); combo enablers may be slightly negative alone.

    python -m clockwork.part_pass --fights 40              # current values for every part
    python -m clockwork.part_pass --fights 40 --sweep      # the candidate settings below
"""
import argparse
import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace

from .config import DEFAULT_RULES
from .decks import STARTER
from .enemies import ENEMIES
from .engine import apply, legal_actions, new_fight
from .parts import Kind as K
from .run import make_agent
from .run_mode import PART_TIER

START_HP = 30


def _cell(args):
    deck, enemy, seeds, agent, rules = args
    wins = 0
    for seed in seeds:
        s = new_fight(deck, enemy, seed=seed, rules=rules, start_hp=START_HP)
        a = make_agent(agent, seed)
        while s.result is None:
            apply(s, a.act(s, legal_actions(s)))
        wins += s.result == "win"
    return wins, len(seeds)


def win_rate(pool, deck, rules, agent, fights, block=10):
    res = list(pool.map(_cell, [(deck, e, range(lo, min(lo + block, fights)), agent, rules)
                                for e in ENEMIES for lo in range(0, fights, block)]))
    return sum(w for w, _ in res) / sum(n for _, n in res)


def with_part(kind):
    deck = dict(STARTER)
    deck[kind] = deck.get(kind, 0) + 1
    return deck


def rules_for(setting):
    parts = tuple(setting.get("part", ()))
    other = {k: v for k, v in setting.items() if k != "part"}
    return replace(DEFAULT_RULES, part_overrides=DEFAULT_RULES.part_overrides + parts, **other)


# part, label, setting (RulesConfig fields; "part" entries become part_overrides)
SWEEP = [
    # Round 3 (after rounds 1-2: Hammer 10/+3, Loader and Spring +3 Block, Coupler 2 dmg no extra Heat,
    # Assembly 1 + 3 per install). Magnet's value jumps between 3 and 4 Block per pull (two pulls stop
    # a 7-damage attack), so split its Block between pulls and a flat amount.
    (K.MAGNET, "3 per pull + 1", {"magnet_block_per_pull": 3, "part": [("Magnet", "block", 1)]}),
    (K.MAGNET, "3 per pull + 2", {"magnet_block_per_pull": 3, "part": [("Magnet", "block", 2)]}),
    (K.MAGNET, "2 per pull + 3", {"magnet_block_per_pull": 2, "part": [("Magnet", "block", 3)]}),
    (K.SLIDER, "7 dmg", {"part": [("Slider", "damage", 7)]}),
    (K.SLIDER, "6 dmg", {"part": [("Slider", "damage", 6)]}),
]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="mcts@50")
    ap.add_argument("--fights", type=int, default=40)
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--only", nargs="*", help="part names to measure")
    args = ap.parse_args(argv)
    with ProcessPoolExecutor(os.cpu_count()) as pool:
        base = win_rate(pool, STARTER, DEFAULT_RULES, args.agent, args.fights)
        print(f"starter from {START_HP} HP: {base:.1%}", flush=True)
        if args.sweep:
            for kind, label, setting in SWEEP:
                if args.only and kind.value not in args.only:
                    continue
                rules = rules_for(setting)
                # The part's own setting can change the starter too (e.g. Spring), so re-measure it.
                b = base if kind not in STARTER else win_rate(pool, STARTER, rules, args.agent, args.fights)
                r = win_rate(pool, with_part(kind), rules, args.agent, args.fights)
                print(f"{kind.value:10s} {label:22s} {(r - b) * 100:+5.1f} pts", flush=True)
        else:
            for kind in PART_TIER:
                if args.only and kind.value not in args.only:
                    continue
                r = win_rate(pool, with_part(kind), DEFAULT_RULES, args.agent, args.fights)
                print(f"{kind.value:10s} {(r - base) * 100:+5.1f} pts", flush=True)


if __name__ == "__main__":
    main()
