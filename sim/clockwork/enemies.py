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


# Tuned v6 (balance pass v5, two-part Loader, enemy HP +/-3 per fight): HP and attacks scaled (clockwork.tune) until MCTS with 50 simulations per decision
# (a stand-in for a casual player) wins ~60-67% on average across the six test decks, with the
# crank direction locked per turn. v1 values (before any tuning) in the comments.
ENEMIES = {
    # Rules.md §8b paper-prototype baseline. v1: 60 HP, Attack 8.
    "dummy": EnemySpec("dummy", 82, ((("attack", 11),),)),
    # Telegraphed big hit every 3rd turn: tests Block timing. v1: 70 HP, 4/4/18.
    "spiker": EnemySpec("spiker", 89, ((("attack", 5),), (("attack", 5),), (("attack", 22),))),
    # Enrage timer: 4, 6, 8, 10 ... tests burst. v1: 75 HP.
    "enrager": EnemySpec("enrager", 82, ((("attack", 4),),), attack_growth=2),
    # Attacks the machine. v1: 65 HP, attacks 8/6/8/6.
    "saboteur": EnemySpec("saboteur", 92, (
        (("attack", 12),),
        (("jam", 2), ("attack", 8)),
        (("wind_back",), ("attack", 12)),
        (("unscrew",), ("attack", 8)),
    )),
    # Rules.md §7 boss: every crank counts (free, extra, backward and Spring cranks). v1: 50 HP.
    # v2 (chime): no regular attack; every 4th crank of the fight it strikes at once.
    # Old v1 rule: 12 cranks in the whole fight, then instant loss (crank_limit=12).
    "clock_tower": EnemySpec("clock_tower", 115, ((),), chime_every=4, chime_damage=15),
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


def scaled(spec: EnemySpec, f: float) -> EnemySpec:
    """The same enemy with HP and every attack (and attack growth) multiplied by f, rounded."""
    def scale_act(act):
        return ("attack", max(1, round(act[1] * f))) if act[0] == "attack" else act
    pattern = tuple(tuple(scale_act(a) for a in intent) for intent in spec.pattern)
    return EnemySpec(spec.name, max(1, round(spec.hp * f)), pattern,
                     attack_growth=round(spec.attack_growth * f), crank_limit=spec.crank_limit,
                     chime_every=spec.chime_every, chime_damage=round(spec.chime_damage * f))
