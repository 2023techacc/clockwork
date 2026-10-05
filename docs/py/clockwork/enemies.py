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
#   ("overclock", heat)         adds Heat to your machine (can overheat it)
#   ("rust", amount)            the part at the Trigger Point deals/blocks `amount` less this fight
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
    cogs: int = 0                             # cogs looted on a win (harder enemies carry more)
    elite: bool = False
    armor: int = 0                            # every hit on it deals this much less (min 0)
    swing: bool = False                       # forces the turn direction: odd turns clockwise, even counter-clockwise


# Tuned v7 for runs where HP carries over (clockwork.tune; MCTS@50 = casual player stand-in):
# normal enemies cost ~15 HP per win; the boss is tuned for a player arriving with 35 HP.
# v1 values (before any tuning) in the comments.
ENEMIES = {
    # Normal fights (v7, HP carries over in a run): tuned so MCTS@50 loses ~15 HP per win.
    # Rules.md §8b paper-prototype baseline. v1: 60 HP, Attack 8.
    "dummy": EnemySpec("dummy", 55, ((("attack", 7),),), cogs=12),
    # Telegraphed big hit every 3rd turn: tests Block timing. v1: 70 HP, 4/4/18.
    "spiker": EnemySpec("spiker", 58, ((("attack", 3),), (("attack", 3),), (("attack", 14),)), cogs=15),
    # Enrage timer: 3, 4, 5, 6 ... tests burst. v1: 75 HP, 4 +2 per turn.
    "enrager": EnemySpec("enrager", 60, ((("attack", 3),),), attack_growth=1, cogs=14),
    # Attacks the machine. v1: 65 HP, attacks 8/6/8/6.
    "saboteur": EnemySpec("saboteur", 56, (
        (("attack", 7),),
        (("jam", 2), ("attack", 5)),
        (("wind_back",), ("attack", 7)),
        (("unscrew",), ("attack", 5)),
    ), cogs=16),
    # Boss. v2 (chime): no regular attack; every 4th crank of the fight it strikes at once.
    # Old v1 rule: 12 cranks in the whole fight, then instant loss (crank_limit=12).
    "clock_tower": EnemySpec("clock_tower", 98, ((),), chime_every=4, chime_damage=12, cogs=60),
    # Other bosses (v13, to compare with the Clock Tower). Tuned in run conditions (clockwork.boss_tune:
    # the states 285 casual runs reached the boss with) to the Clock Tower's 78% win rate there.
    # Furnace: heats your machine every turn, a big stoke every 3rd. Tests Heat management.
    "furnace": EnemySpec("furnace", 75, (
        (("overclock", 1), ("attack", 5)),
        (("overclock", 1), ("attack", 5)),
        (("overclock", 3), ("attack", 9)),
    ), cogs=60),
    # Dismantler: takes your machine apart. Tests rebuilding and Bracing.
    "dismantler": EnemySpec("dismantler", 94, (
        (("unscrew",), ("unscrew",), ("attack", 5)),
        (("rust", 2), ("attack", 7)),
    ), cogs=60),
    # Iron Colossus: armor 3 on every hit, slow heavy attacks. Tests big single hits.
    "iron_colossus": EnemySpec("iron_colossus", 68, ((("attack", 7),),), armor=3, cogs=60),
    # Pendulum: forces the turn direction (odd turns clockwise, even counter-clockwise); a light
    # swing then a heavy one. Tests layouts that work both ways.
    "pendulum": EnemySpec("pendulum", 83, ((("attack", 4),), (("attack", 10),)), swing=True, cogs=60),
    # Elites (machine attackers), tuned so a casual player (MCTS@50) loses ~25 HP per win.
    "overclocker": EnemySpec("overclocker", 80, (
        (("attack", 7),),
        (("overclock", 3), ("attack", 5)),
    ), cogs=32, elite=True),
    "rust_golem": EnemySpec("rust_golem", 86, (
        (("rust", 2), ("attack", 7)),
        (("attack", 7),),
    ), cogs=34, elite=True),
    "pickpocket": EnemySpec("pickpocket", 84, ((("unscrew",), ("attack", 7)),), cogs=30, elite=True),
    "jammer_prime": EnemySpec("jammer_prime", 74, (
        (("jam", 2), ("jam", 2), ("attack", 7)),
        (("attack", 7),),
    ), cogs=36, elite=True),
}
NORMAL = ["dummy", "spiker", "enrager", "saboteur"]
ELITES = ["overclocker", "rust_golem", "pickpocket", "jammer_prime"]
BOSSES = ["clock_tower", "furnace", "dismantler", "iron_colossus", "pendulum"]


def reveal_intent(spec: EnemySpec, turn: int, gear, rng) -> Intent:
    """Materialize the intent for `turn` (1-based), picking random targets now."""
    template = spec.pattern[(turn - 1) % len(spec.pattern)]
    occupied = [i for i, p in enumerate(gear) if p is not None]
    jammed, unscrewed = set(), set()
    out = []
    for act in template:
        if act[0] == "attack":
            out.append(("attack", act[1] + spec.attack_growth * (turn - 1)))
        elif act[0] == "jam":
            free = [i for i in occupied if i not in jammed]
            slot = rng.choice(free) if free else rng.randrange(len(gear))
            jammed.add(slot)
            out.append(("jam", slot, act[1]))
        elif act[0] == "unscrew":
            free = [i for i in occupied if i not in unscrewed]
            if free:
                slot = rng.choice(free)
                unscrewed.add(slot)
                out.append(("unscrew", slot))
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
                     if spec.chime_damage else 0, cogs=spec.cogs, elite=spec.elite,
                     armor=spec.armor, swing=spec.swing)
