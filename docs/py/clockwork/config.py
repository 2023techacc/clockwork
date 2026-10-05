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

    # --- Part-effect numbers that aren't per-part stats ---
    amplifier_bonus: float = 0.3     # per adjacent Amplifier, additive (Rules.md: 0.5; balance pass v5)
    coil_damage: int = 8             # Coil attachment (was 4; v12)
    bracing_damage: int = 1          # Bracing attachment: flat damage/Block when the part triggers (v12)
    bracing_block: int = 1           # (on top of its immunity to Jam, Rust and Unscrew)
    feeder_extra_loads: int = 1      # a Loader with Feeder installs this many more parts per trigger
    feeder_triggers: int = 3         # ... and the first this-many parts it loads trigger right away (v12)
    polish_bonus: float = 0.2        # Polish attachment, added to the Amplifier bonus (was 0.5)
    clamp_max_triggers: int = 1      # Clamp triggers at most this many pulled parts (was 2)
    loader_loads: int = 2            # parts a Loader installs per trigger (was 1)
    loader_replaces: bool = True     # with the gear full, one load replaces the part opposite the Loader
                                     # (with Feeder: the next part to come up); the replaced part is discarded
    max_attachments: int = 2         # attachments per part
    rust_per_hit: int = 2            # Rust: the part loses this much damage/Block for the fight
    magnet_block_per_pull: int = 2   # Magnet gains this much Block per part it pulls (amplifiable)
    magnet_damage_per_pull: int = 0  # ... and deals this much damage per part pulled
    magnet_swaps: bool = True        # Magnet pulls into an occupied slot by swapping the two parts

    # --- Part stat overrides, for balance sweeps: (("Hammer", "damage", 10), ...) ---
    part_overrides: tuple = ()

    # --- Runs ---
    heal_between_fights: int = 5     # HP carries over between fights; this much is healed after each win

    # --- Enemies ---
    enemy_hp_jitter: int = 3         # each fight's enemy HP is base +/- this (uniform)

    # --- Simulator safety (not game rules) ---
    safety_triggers_per_turn: int = 200   # stop a runaway turn and flag it
    max_turns: int = 40                   # fight counts as a timeout loss after this


DEFAULT_RULES = RulesConfig()
