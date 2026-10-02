"""Rules configuration.

Every number and every still-undecided rule lives here, so balance questions
become config sweeps instead of code edits. Defaults are "Simulator defaults v1"
in Rules-Decisions.md.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class RulesConfig:
    # --- Player basics (Rules.md §1) ---
    player_hp: int = 55
    gear_size: int = 6
    offered_per_turn: int = 3        # parts offered from the front of the queue
    queue_visible: int = 5           # front-of-queue window, including the offered parts
    installs_per_turn: int = 2       # a replace counts as an install
    crank_power: int = 2             # fresh every turn, never carries over
    # All of a turn's player cranks (free and paid) go one way, chosen when installing ends.
    # False = old rule: free crank clockwise, paid cranks either way.
    crank_direction_lock: bool = True

    # --- Heat (Rules.md §3, §8b #3) ---
    overheat_at: int = 10            # reaching this stops the turn, resets Heat to 0, next turn is dead
    heat_per_trigger: int = 1        # every trigger, before part-specific extras
    # Extra Heat for the n-th Spring in one chain is n * spring_heat_step (1st +1, 2nd +2, 3rd +3...).
    spring_heat_step: int = 1
    # Reshuffle Heat for the k-th recycle in one turn (k starts at 1): +0, +1, +2, ...
    reshuffle_heat_first: int = 0

    # --- Loop brakes (Rules.md §8b). None = rule on hold (not enforced). ---
    max_triggers_per_part: Optional[int] = None   # §8b #1 (on hold)
    max_triggers_per_turn: Optional[int] = None   # §8b #2 (on hold)
    coupler_can_trigger_coupler: bool = False     # §8b #4 (active)
    # Mirror copying a Mirror is always "nothing": on an even gear it can only point back at itself.

    # --- Simulator safety (not game rules) ---
    safety_triggers_per_turn: int = 200   # stop a runaway turn and flag it
    max_turns: int = 40                   # fight counts as a timeout loss after this


DEFAULT_RULES = RulesConfig()
