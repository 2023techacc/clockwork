"""Headless Clockwork fight simulator.

Geometry
--------
Gear slots are numbered clockwise around the gear body and never change while
the gear turns; `state.top` is the slot currently at the Trigger Point.

* A forward crank turns the gear clockwise, which brings the slot to the left
  of the top (counter-clockwise neighbour, `top - 1`) up to the Trigger Point.
* "Left"/"right" are as seen from the centre of the gear looking out at a part:
  left = counter-clockwise neighbour (slot - 1), right = clockwise neighbour (slot + 1).
* A trigger travels in a direction. A forward (clockwise) crank moves the
  trigger leftwards along the gear; a backward crank moves it rightwards.
  A Spring cranks the gear in the direction its trigger was travelling.

Trigger resolution is depth-first on an explicit stack (no recursion limit).

Actions are plain tuples:
    ("install", hand_index, slot)   slot = gear slot index
    ("end_install",)                then the free crank happens automatically
    ("crank",)                      1 Crank Power, forward
    ("crank_back",)                 1 Crank Power, backward
    ("end_turn",)
"""
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .config import DEFAULT_RULES, RulesConfig
from .decks import deck_list
from .enemies import ENEMIES, EnemySpec, reveal_intent
from .parts import AMPLIFIER_BONUS, SPECS, Kind, Part

CW, CCW = "cw", "ccw"   # crank directions; CW = forward

# §8b caps that are on hold. Tracked as "would have been hit" so their impact is visible.
REF_TURN_CAP = 8
REF_PART_CAP = 2


@dataclass
class Stats:
    damage_by_turn: List[int] = field(default_factory=list)
    triggers_by_turn: List[int] = field(default_factory=list)
    heat_by_turn: List[int] = field(default_factory=list)   # Heat at end of each player turn
    overheats: int = 0
    runaway_turns: int = 0          # turns stopped by the simulator safety cap
    reshuffles: int = 0
    turns_over_turn_cap: int = 0    # turns with > REF_TURN_CAP triggers
    turns_over_part_cap: int = 0    # turns where some part triggered > REF_PART_CAP times
    damage_taken: int = 0


@dataclass
class State:
    rules: RulesConfig
    enemy: EnemySpec
    rng: random.Random
    gear: List[Optional[Part]]
    queue: List[Part]
    discard: List[Part] = field(default_factory=list)
    hand: List[Part] = field(default_factory=list)
    top: int = 0
    jams: Dict[int, int] = field(default_factory=dict)   # slot -> player turns left
    turn: int = 0
    phase: str = "install"          # install | crank | over
    hp: int = 0
    block: int = 0
    heat: int = 0
    crank_power: int = 0
    installs_left: int = 0
    dead_turn: bool = False         # this turn follows an Overheat: no cranks at all
    overheat_pending: bool = False  # next turn will be dead
    locked: bool = False            # no more cranks this turn
    enemy_hp: int = 0
    intent: tuple = ()
    cranks_used: int = 0            # whole fight, all cranks (for Clock Tower)
    tower_strikes: bool = False
    # per-turn counters
    triggers_turn: int = 0
    damage_turn: int = 0
    reshuffles_turn: int = 0
    part_triggers: Dict[int, int] = field(default_factory=dict)
    turn_runaway: bool = False
    # per-chain counter
    chain_springs: int = 0
    result: Optional[str] = None    # "win" | "loss"
    reason: str = ""
    stats: Stats = field(default_factory=Stats)
    log: Optional[List[str]] = None

    def clone(self) -> "State":
        s = State.__new__(State)
        s.__dict__.update(self.__dict__)
        s.rng = random.Random()
        s.rng.setstate(self.rng.getstate())
        for name in ("gear", "queue", "discard", "hand"):
            setattr(s, name, list(getattr(self, name)))
        s.jams = dict(self.jams)
        s.part_triggers = dict(self.part_triggers)
        st = Stats(**self.stats.__dict__)
        for name in ("damage_by_turn", "triggers_by_turn", "heat_by_turn"):
            setattr(st, name, list(getattr(st, name)))
        s.stats = st
        s.log = list(self.log) if self.log is not None else None
        return s

    # --- observation helpers ---
    def visible_queue(self) -> List[Part]:
        return self.queue[: max(0, self.rules.queue_visible - self.rules.offered_per_turn)]

    def arrival_order(self) -> List[Optional[Part]]:
        """Gear from the Trigger Point onward, in the order forward cranks bring parts up."""
        n = len(self.gear)
        return [self.gear[(self.top - k) % n] for k in range(n)]


# ---------------------------------------------------------------------------
# Setup

def new_fight(deck, enemy="dummy", seed=0, rules: RulesConfig = DEFAULT_RULES, trace=False) -> State:
    spec = ENEMIES[enemy] if isinstance(enemy, str) else enemy
    rng = random.Random(seed)
    parts = [Part(uid, kind) for uid, kind in enumerate(deck_list(deck))]
    rng.shuffle(parts)
    s = State(rules=rules, enemy=spec, rng=rng, gear=[None] * rules.gear_size, queue=parts,
              hp=rules.player_hp, enemy_hp=spec.hp, log=[] if trace else None)
    _start_turn(s)
    return s


# ---------------------------------------------------------------------------
# Public API

def legal_actions(s: State) -> List[tuple]:
    if s.phase == "over":
        return []
    if s.phase == "install":
        acts = []
        if s.installs_left > 0:
            seen = set()
            for i, part in enumerate(s.hand):
                if part.kind in seen:          # identical parts give identical results
                    continue
                seen.add(part.kind)
                acts.extend(("install", i, slot) for slot in range(len(s.gear)))
        acts.append(("end_install",))
        return acts
    acts = []
    if _can_crank(s):
        acts += [("crank",), ("crank_back",)]
    acts.append(("end_turn",))
    return acts


def apply(s: State, action: tuple) -> None:
    """Apply one action in place."""
    kind = action[0]
    if s.phase == "over":
        raise ValueError("fight is over")
    if kind == "install":
        _install(s, action[1], action[2])
    elif kind == "end_install":
        _require(s.phase == "install", action)
        s.phase = "crank"
        if s.dead_turn:
            s.locked = True
            _log(s, "overheated: no cranks this turn")
        else:
            _player_crank(s, CW, free=True)
    elif kind in ("crank", "crank_back"):
        _require(s.phase == "crank" and _can_crank(s), action)
        s.crank_power -= 1
        _player_crank(s, CW if kind == "crank" else CCW, free=False)
    elif kind == "end_turn":
        _require(s.phase == "crank", action)
        _end_turn(s)
    else:
        raise ValueError(f"unknown action {action}")


def summary(s: State) -> dict:
    st = s.stats
    return {
        "result": s.result, "reason": s.reason, "turns": s.turn,
        "hp": s.hp, "enemy_hp": max(0, s.enemy_hp),
        "total_damage": sum(st.damage_by_turn),
        "max_damage_turn": max(st.damage_by_turn, default=0),
        "max_triggers_turn": max(st.triggers_by_turn, default=0),
        "overheats": st.overheats, "runaway_turns": st.runaway_turns,
        "reshuffles": st.reshuffles, "final_heat": s.heat,
        "turns_over_turn_cap": st.turns_over_turn_cap,
        "turns_over_part_cap": st.turns_over_part_cap,
        "damage_taken": st.damage_taken, "cranks_used": s.cranks_used,
    }


def render(s: State) -> str:
    def name(p, slot):
        if p is None:
            return "--"
        return f"{p.kind}{'(J)' if slot in s.jams else ''}"
    n = len(s.gear)
    order = [name(s.gear[(s.top - k) % n], (s.top - k) % n) for k in range(n)]
    return (f"T{s.turn} HP {s.hp} Block {s.block} Heat {s.heat} CP {s.crank_power} | "
            f"enemy {s.enemy.name} {s.enemy_hp} intent {s.intent} | "
            f"gear (top, then arrival order) [{' > '.join(order)}] | "
            f"hand {[str(p.kind) for p in s.hand]} | next {[str(p.kind) for p in s.visible_queue()]}")


# ---------------------------------------------------------------------------
# Turn flow

def _start_turn(s: State) -> None:
    s.turn += 1
    if s.turn > s.rules.max_turns:
        _finish(s, "loss", "timeout")
        return
    s.block = 0
    s.crank_power = s.rules.crank_power
    s.installs_left = s.rules.installs_per_turn
    s.triggers_turn = s.damage_turn = s.reshuffles_turn = 0
    s.part_triggers = {}
    s.turn_runaway = False
    s.dead_turn, s.overheat_pending = s.overheat_pending, False
    s.locked = False
    s.phase = "install"
    _draw(s)
    s.intent = reveal_intent(s.enemy, s.turn, s.gear, s.rng)
    if s.log is not None:
        _log(s, render(s))


def _draw(s: State) -> None:
    need = s.rules.offered_per_turn
    if len(s.queue) < need:
        _recycle(s)
        _check_overheat(s)
    s.hand, s.queue = s.queue[:need], s.queue[need:]


def _recycle(s: State) -> bool:
    if not s.discard:
        return False
    pile = s.discard
    s.discard = []
    s.rng.shuffle(pile)
    s.queue.extend(pile)
    s.reshuffles_turn += 1
    s.stats.reshuffles += 1
    heat = s.rules.reshuffle_heat_first + s.reshuffles_turn - 1
    s.heat += heat
    _log(s, f"recycle #{s.reshuffles_turn} this turn: {len(pile)} parts, +{heat} Heat")
    return True


def _install(s: State, hand_index: int, slot: int) -> None:
    _require(s.phase == "install" and s.installs_left > 0, ("install", hand_index, slot))
    part = s.hand.pop(hand_index)
    old = s.gear[slot]
    if old is not None:
        s.discard.append(old)
    s.gear[slot] = part
    s.installs_left -= 1
    pos = (s.top - slot) % len(s.gear)
    _log(s, f"install {part} at slot {slot} (+{pos})" + (f", replacing {old}" if old else ""))


def _can_crank(s: State) -> bool:
    if s.locked or s.dead_turn or s.crank_power < 1:
        return False
    limit = s.enemy.crank_limit
    return limit is None or s.cranks_used < limit


def _end_turn(s: State) -> None:
    _close_turn_stats(s)
    s.discard.extend(s.hand)
    s.hand = []
    if s.tower_strikes:
        _finish(s, "loss", "clock tower struck")
        return
    # Jams count down player turns; a new jam lasts through the next `turns` turns.
    s.jams = {slot: t - 1 for slot, t in s.jams.items() if t > 1}
    n = len(s.gear)
    for act in s.intent:
        if act[0] == "attack":
            absorbed = min(s.block, act[1])
            s.block -= absorbed
            s.hp -= act[1] - absorbed
            s.stats.damage_taken += act[1] - absorbed
        elif act[0] == "jam":
            s.jams[act[1]] = max(s.jams.get(act[1], 0), act[2])
        elif act[0] == "wind_back":
            s.top = (s.top + 1) % n     # gear turns counter-clockwise, nothing triggers
        elif act[0] == "unscrew":
            part = s.gear[act[1]]
            if part is not None:
                s.discard.append(part)
                s.gear[act[1]] = None
        _log(s, f"enemy: {act}")
    if s.hp <= 0:
        _finish(s, "loss", "hp")
        return
    _start_turn(s)


def _close_turn_stats(s: State) -> None:
    st = s.stats
    st.damage_by_turn.append(s.damage_turn)
    st.triggers_by_turn.append(s.triggers_turn)
    st.heat_by_turn.append(s.heat)
    if s.triggers_turn > REF_TURN_CAP:
        st.turns_over_turn_cap += 1
    if any(c > REF_PART_CAP for c in s.part_triggers.values()):
        st.turns_over_part_cap += 1
    if s.turn_runaway:
        st.runaway_turns += 1


def _finish(s: State, result: str, reason: str) -> None:
    s.result, s.reason, s.phase = result, reason, "over"
    _log(s, f"fight over: {result} ({reason})")


# ---------------------------------------------------------------------------
# Trigger resolution

def _player_crank(s: State, direction: str, free: bool) -> None:
    """A crank started by the player begins a new chain."""
    s.chain_springs = 0
    _log(s, f"{'free ' if free else ''}crank {direction}")
    _resolve(s, [("crank", direction)])


def _resolve(s: State, stack: list) -> None:
    n = len(s.gear)
    while stack and s.phase != "over":
        task = stack.pop()
        if task[0] == "crank":
            limit = s.enemy.crank_limit
            if limit is not None and s.cranks_used >= limit:
                _log(s, "crank fizzles: crank limit reached")
                continue
            s.cranks_used += 1
            if limit is not None and s.cranks_used >= limit:
                s.tower_strikes = True
                s.locked = True
            s.top = (s.top - 1) % n if task[1] == CW else (s.top + 1) % n
            stack.append(("trigger", s.top, task[1], False, None))
        else:
            _, slot, direction, from_coupler, uid = task
            if uid is not None:     # Coupler targets are bound to the part, not the slot
                slot = next((i for i, p in enumerate(s.gear) if p is not None and p.uid == uid), None)
                if slot is None:
                    continue
            if not _trigger(s, slot, direction, from_coupler, stack):
                stack.clear()


def _effective_kind(s: State, slot: int) -> Optional[Kind]:
    """What the part in `slot` does when triggered. A Mirror acts as the part opposite it."""
    part = s.gear[slot]
    if part is None:
        return None
    if part.kind != Kind.MIRROR:
        return part.kind
    n = len(s.gear)
    if n % 2:
        return None
    opp = s.gear[(slot + n // 2) % n]
    if opp is None or opp.kind == Kind.MIRROR:
        return None
    return opp.kind


def _trigger(s: State, slot: int, direction: str, from_coupler: bool, stack: list) -> bool:
    """Trigger the part in `slot`. Returns False if resolution must stop."""
    r = s.rules
    n = len(s.gear)
    part = s.gear[slot]
    if part is None:
        _log(s, f"  slot {slot}: empty, nothing happens")
        return True
    if slot in s.jams:
        _log(s, f"  {part}: jammed")
        return True
    kind = _effective_kind(s, slot)
    if kind is None or not SPECS[kind].triggers:
        _log(s, f"  {part}: does not trigger")
        return True
    if from_coupler and kind == Kind.COUPLER and not r.coupler_can_trigger_coupler:
        _log(s, f"  {part}: Coupler can't trigger a Coupler")
        return True
    if r.max_triggers_per_part is not None and s.part_triggers.get(part.uid, 0) >= r.max_triggers_per_part:
        _log(s, f"  {part}: spent")
        return True
    if r.max_triggers_per_turn is not None and s.triggers_turn >= r.max_triggers_per_turn:
        _log(s, "  trigger limit reached")
        return False
    if s.triggers_turn >= r.safety_triggers_per_turn:
        s.turn_runaway = True
        s.locked = True
        _log(s, "  SAFETY CAP: runaway turn stopped")
        return False

    spec = SPECS[kind]
    s.triggers_turn += 1
    s.part_triggers[part.uid] = s.part_triggers.get(part.uid, 0) + 1
    heat = r.heat_per_trigger + spec.extra_heat
    if kind == Kind.SPRING:
        s.chain_springs += 1
        heat += s.chain_springs * r.spring_heat_step
    s.heat += heat
    label = str(part) if part.kind == kind else f"{part} as {kind}"
    notes = [f"+{heat} Heat"]

    if spec.damage or spec.block:
        mult = 1 + AMPLIFIER_BONUS * _adjacent_amplifiers(s, slot)
        if spec.damage:
            dmg = int(spec.damage * mult)
            s.enemy_hp -= dmg
            s.damage_turn += dmg
            notes.append(f"{dmg} damage")
        if spec.block:
            blk = int(spec.block * mult)
            s.block += blk
            notes.append(f"{blk} Block")
    if spec.cooling:
        s.heat = max(0, s.heat - spec.cooling)
        notes.append(f"-{spec.cooling} Heat")
    if kind == Kind.LOADER:
        notes.append(_load(s))
    if kind == Kind.MAGNET:
        notes.append(_magnet(s, slot))
    _log(s, f"  {label} triggers ({direction}): {', '.join(notes)} -> Heat {s.heat}")

    if s.enemy_hp <= 0:
        _close_turn_stats(s)
        _finish(s, "win", "enemy hp")
        return False
    if _check_overheat(s):
        return False

    if kind == Kind.SPRING:
        stack.append(("crank", direction))
    elif kind == Kind.COUPLER:
        left, right = (slot - 1) % n, (slot + 1) % n
        # Depth-first, left then right: push right first so left resolves (fully) first.
        for nb, d in ((right, CCW), (left, CW)):
            if s.gear[nb] is not None:
                stack.append(("trigger", nb, d, True, s.gear[nb].uid))
    return True


def _check_overheat(s: State) -> bool:
    if s.heat < s.rules.overheat_at:
        return False
    s.stats.overheats += 1
    s.heat = 0
    s.locked = True
    s.overheat_pending = True
    _log(s, "  OVERHEAT: turn stops, Heat -> 0, next turn is dead")
    return True


def _adjacent_amplifiers(s: State, slot: int) -> int:
    n = len(s.gear)
    return sum(1 for nb in ((slot - 1) % n, (slot + 1) % n)
               if s.gear[nb] is not None and s.gear[nb].kind == Kind.AMPLIFIER)


def _load(s: State) -> str:
    empty = [i for i, p in enumerate(s.gear) if p is None]
    if not empty:
        return "no empty slot"
    if not s.queue:
        _recycle(s)
    if not s.queue:
        return "nothing to load"
    part = s.queue.pop(0)                 # the next part in the queue
    slot = s.rng.choice(empty)
    s.gear[slot] = part
    return f"loads {part} into slot {slot}"


def _magnet(s: State, slot: int) -> str:
    n = len(s.gear)
    moved = []
    for step in (-1, 1):    # left side first, then right
        near, far = (slot + step) % n, (slot + 2 * step) % n
        if far != slot and s.gear[near] is None and s.gear[far] is not None:
            s.gear[near], s.gear[far] = s.gear[far], None
            moved.append(f"{s.gear[near]} {far}->{near}")
    return "pulls " + ", ".join(moved) if moved else "pulls nothing"


# ---------------------------------------------------------------------------

def _require(ok: bool, action) -> None:
    if not ok:
        raise ValueError(f"illegal action {action}")


def _log(s: State, msg: str) -> None:
    if s.log is not None:
        s.log.append(msg)
