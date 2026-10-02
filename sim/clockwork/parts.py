"""Part definitions (Rules.md §4, Rules-Decisions.md)."""
from dataclasses import dataclass, replace
from functools import lru_cache
from enum import Enum


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

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class PartSpec:
    damage: int = 0
    block: int = 0
    extra_heat: int = 0        # on top of the per-trigger Heat
    cooling: int = 0
    triggers: bool = True      # False = passive, never triggers (no effect, no Heat)


SPECS = {
    Kind.STRIKER: PartSpec(damage=6),
    Kind.PLATE: PartSpec(block=6),
    Kind.SPRING: PartSpec(),                 # extra Heat depends on its place in the chain
    Kind.MIRROR: PartSpec(),
    Kind.AMPLIFIER: PartSpec(triggers=False),
    Kind.COUPLER: PartSpec(),
    Kind.LOADER: PartSpec(),
    Kind.COOLANT: PartSpec(cooling=3),
    Kind.HAMMER: PartSpec(damage=15, extra_heat=2),
    Kind.MAGNET: PartSpec(),
}

AMPLIFIER_BONUS = 0.5   # per adjacent Amplifier, additive; damage and Block only; rounded down


@dataclass(frozen=True)
class Part:
    uid: int
    kind: Kind

    def __str__(self) -> str:
        return f"{self.kind}#{self.uid}"


@lru_cache(maxsize=None)
def specs_for(overrides: tuple) -> dict:
    """SPECS with overrides applied, e.g. (("Hammer", "damage", 10), ("Hammer", "extra_heat", 3))."""
    specs = dict(SPECS)
    for kind_name, field_name, value in overrides:
        kind = Kind(kind_name)
        specs[kind] = replace(specs[kind], **{field_name: value})
    return specs
