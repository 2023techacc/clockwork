"""Part definitions (Rules.md §4, Rules-Decisions.md)."""
from dataclasses import dataclass, replace
from functools import lru_cache
from enum import Enum
from typing import Optional


class Kind(str, Enum):
    STRIKER = "Striker"
    PLATE = "Plate"
    SPRING = "Spring"
    MIRROR = "Mirror"
    AMPLIFIER = "Amplifier"
    COUPLER = "Coupler"
    LOADER = "Loader"
    COOLANT = "Coolant"
    HAMMER = "Hammer"
    MAGNET = "Magnet"
    PRIMER = "Primer"
    ASSEMBLY = "Assembly"
    SLIDER = "Slider"

    def __str__(self) -> str:
        return self.value


class Mod(str, Enum):
    """Attachments: at most one per part, each fits one part kind."""
    COIL = "Coil"        # Spring: the part its crank triggers also deals COIL_DAMAGE
    POLISH = "Polish"    # Mirror: the copy's damage/Block gets +POLISH_BONUS (adds to Amplifiers)
    CLAMP = "Clamp"      # Magnet: every part it pulls is triggered
    FEEDER = "Feeder"    # Loader: loads into the next empty slot to come up, not a random one

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class PartSpec:
    damage: int = 0
    block: int = 0
    extra_heat: int = 0        # on top of the per-trigger Heat
    cooling: int = 0
    triggers: bool = True      # False = passive, never triggers (no effect, no Heat)
    fresh_damage: int = 0      # replaces `damage` on the first trigger after being installed
    per_part_damage: int = 0   # extra damage per occupied gear slot (itself included)
    per_install_damage: int = 0  # extra damage per part installed this turn (by hand or Loader)
    moved_bonus: int = 0       # extra damage if a Magnet moved it this turn


SPECS = {
    Kind.STRIKER: PartSpec(damage=6),
    Kind.PLATE: PartSpec(block=6),
    Kind.SPRING: PartSpec(),                 # extra Heat depends on its place in the chain
    Kind.MIRROR: PartSpec(),
    Kind.AMPLIFIER: PartSpec(triggers=False),
    Kind.COUPLER: PartSpec(extra_heat=2),                  # balance pass v5 (was +0)
    Kind.LOADER: PartSpec(),
    Kind.COOLANT: PartSpec(cooling=3),
    Kind.HAMMER: PartSpec(damage=9, extra_heat=4),     # Rules.md: 15 damage, +2 Heat (swept down, v3)
    Kind.MAGNET: PartSpec(),
    # Payoff parts (sim v4 proposals)
    # Primer: fresh_damage only if it triggers on the turn it was installed.
    # Balance pass v5 values; first proposals were Primer 4/18 and Assembly 2 per part.
    Kind.PRIMER: PartSpec(damage=2, fresh_damage=8),       # pairs with Loader (Feeder) / placement
    Kind.ASSEMBLY: PartSpec(per_install_damage=3),         # pairs with Loader
    Kind.SLIDER: PartSpec(damage=5, moved_bonus=3),        # pairs with Magnet (moved bonus was 6)
}

MOD_FITS = {Mod.COIL: Kind.SPRING, Mod.POLISH: Kind.MIRROR, Mod.CLAMP: Kind.MAGNET, Mod.FEEDER: Kind.LOADER}
# Coil damage, Polish bonus and the Amplifier bonus live in RulesConfig (sweepable).



@dataclass(frozen=True)
class Part:
    uid: int
    kind: Kind
    mod: Optional[Mod] = None

    def __str__(self) -> str:
        return f"{self.kind}{'+' + self.mod.value if self.mod else ''}#{self.uid}"


@lru_cache(maxsize=None)
def specs_for(overrides: tuple) -> dict:
    """SPECS with overrides applied, e.g. (("Hammer", "damage", 10), ("Hammer", "extra_heat", 3))."""
    specs = dict(SPECS)
    for kind_name, field_name, value in overrides:
        kind = Kind(kind_name)
        specs[kind] = replace(specs[kind], **{field_name: value})
    return specs
