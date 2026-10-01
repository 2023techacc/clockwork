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
    crank_limit: Optional[int] = None         # Clock Tower: total cranks in the fight


ENEMIES = {
    # Rules.md §8b paper-prototype baseline.
    "dummy": EnemySpec("dummy", 60, ((("attack", 8),),)),
    # Telegraphed big hit every 3rd turn: tests Block timing.
    "spiker": EnemySpec("spiker", 70, ((("attack", 4),), (("attack", 4),), (("attack", 18),))),
    # Enrage timer: 4, 6, 8, 10 ... tests burst.
    "enrager": EnemySpec("enrager", 75, ((("attack", 4),),), attack_growth=2),
    # Attacks the machine.
    "saboteur": EnemySpec("saboteur", 65, (
        (("attack", 8),),
        (("jam", 2), ("attack", 6)),
        (("wind_back",), ("attack", 8)),
        (("unscrew",), ("attack", 6)),
    )),
    # Rules.md §7 boss: every crank counts (free, extra, backward and Spring cranks).
    "clock_tower": EnemySpec("clock_tower", 50, ((("attack", 6),),), crank_limit=12),
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
