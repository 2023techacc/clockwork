"""Scripted test enemies. Numbers are "Experiment setup v1" in AI-Playtesting-Roadmap.md.

An intent is a tuple of actions, revealed at the start of the player's turn and
carried out at the end of it. Random targets (Jam, Unscrew) are picked when the
intent is revealed, so the player can see them.
"""
from dataclasses import dataclass, field
from typing import Optional, Tuple

# Intent actions (gear slots are gear-relative indices):
#   ("attack", amount)
#   ("jam", slot, turns)        slot can't trigger for `turns` player turns
#   ("wind_back",)              gear turns 1 step counter-clockwise, no trigger
#   ("unscrew", slot)           part goes to the discard pile
Action = tuple
Intent = Tuple[Action, ...]


@dataclass(frozen=True)
class EnemySpec:
    name: str
    hp: int
    pattern: Tuple[Tuple[tuple, ...], ...]   # cycled; ("jam", turns) / ("unscrew",) get a slot when revealed
    attack_growth: int = 0                    # added to every attack per turn elapsed
    crank_limit: Optional[int] = None         # total cranks in the fight (old Clock Tower rule)
    chime_every: Optional[int] = None         # Clock Tower: strikes on every Nth crank of the fight
    chime_damage: int = 0                     # ... for this much damage, hitting your current Block


# Tuned v7 for runs where HP carries over (clockwork.tune; MCTS@50 = casual player stand-in):
# normal enemies cost ~15 HP per win; the boss is tuned for a player arriving with 35 HP.
# v1 values (before any tuning) in the comments.
ENEMIES = {
    # Normal fights (v7, HP carries over in a run): tuned so MCTS@50 loses ~15 HP per win.
    # Rules.md §8b paper-prototype baseline. v1: 60 HP, Attack 8.
    "dummy": EnemySpec("dummy", 55, ((("attack", 7),),)),
    # Telegraphed big hit every 3rd turn: tests Block timing. v1: 70 HP, 4/4/18.
    "spiker": EnemySpec("spiker", 58, ((("attack", 3),), (("attack", 3),), (("attack", 14),))),
    # Enrage timer: 3, 4, 5, 6 ... tests burst. v1: 75 HP, 4 +2 per turn.
    "enrager": EnemySpec("enrager", 60, ((("attack", 3),),), attack_growth=1),
    # Attacks the machine. v1: 65 HP, attacks 8/6/8/6.
    "saboteur": EnemySpec("saboteur", 56, (
        (("attack", 7),),
        (("jam", 2), ("attack", 5)),
        (("wind_back",), ("attack", 7)),
        (("unscrew",), ("attack", 5)),
    )),
    # Boss. v2 (chime): no regular attack; every 4th crank of the fight it strikes at once.
    # Old v1 rule: 12 cranks in the whole fight, then instant loss (crank_limit=12).
    "clock_tower": EnemySpec("clock_tower", 98, ((),), chime_every=4, chime_damage=12),
}


def reveal_intent(spec: EnemySpec, turn: int, gear, rng) -> Intent:
    """Materialize the intent for `turn` (1-based), picking random targets now."""
    template = spec.pattern[(turn - 1) % len(spec.pattern)]
    occupied = [i for i, p in enumerate(gear) if p is not None]
    out = []
    for act in template:
        if act[0] == "attack":
            out.append(("attack", act[1] + spec.attack_growth * (turn - 1)))
        elif act[0] == "jam":
            slot = rng.choice(occupied) if occupied else rng.randrange(len(gear))
            out.append(("jam", slot, act[1]))
        elif act[0] == "unscrew":
            if occupied:
                out.append(("unscrew", rng.choice(occupied)))
        else:
            out.append(act)
    return tuple(out)


def scaled(spec: EnemySpec, f: float, attack_f: Optional[float] = None) -> EnemySpec:
    """The same enemy with HP multiplied by f and every attack (attack growth, chime damage)
    by attack_f (default: f), rounded."""
    a = f if attack_f is None else attack_f
    def scale_act(act):
        return ("attack", max(1, round(act[1] * a))) if act[0] == "attack" else act
    pattern = tuple(tuple(scale_act(x) for x in intent) for intent in spec.pattern)
    return EnemySpec(spec.name, max(1, round(spec.hp * f)), pattern,
                     attack_growth=round(spec.attack_growth * a), crank_limit=spec.crank_limit,
                     chime_every=spec.chime_every, chime_damage=max(1, round(spec.chime_damage * a))
                     if spec.chime_damage else 0)
