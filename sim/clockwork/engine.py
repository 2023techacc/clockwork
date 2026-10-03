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
    ("end_install", "cw"|"ccw")     then the free crank happens automatically, in that direction.
                                    With the direction lock (default) this picks the turn's
                                    direction; ("end_install",) alone means clockwise.
    ("crank",)                      1 Crank Power, in the turn's direction (forward if unlocked)
    ("crank_back",)                 1 Crank Power, backward (only without the direction lock)
    ("end_turn",)
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .config import DEFAULT_RULES, RulesConfig
from .decks import deck_list
from .enemies import ENEMIES, EnemySpec, reveal_intent
from .parts import Kind, Mod, Part, specs_for
from .rng import Rng

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
    heat_overflow: int = 0          # Heat above the Overheat threshold, discarded by the reset
    overheats_by: Dict[str, int] = field(default_factory=dict)   # part kind that tipped it over
    runaway_turns: int = 0          # turns stopped by the simulator safety cap
    reshuffles: int = 0
    turns_over_turn_cap: int = 0    # turns with > REF_TURN_CAP triggers
    turns_over_part_cap: int = 0    # turns where some part triggered > REF_PART_CAP times
    damage_taken: int = 0


@dataclass
class State:
    rules: RulesConfig
    enemy: EnemySpec
    rng: Rng
    gear: List[Optional[Part]]
    queue: List[Part]
    discard: List[Part] = field(default_factory=list)
    hand: List[Part] = field(default_factory=list)
    top: int = 0
    jams: Dict[int, int] = field(default_factory=dict)   # slot -> player turns left
    fresh: set = field(default_factory=set)       # uids installed this turn, not triggered since (Primer)
    installed: set = field(default_factory=set)   # uids installed this turn (Assembly)
    moved: set = field(default_factory=set)   # uids a Magnet moved this turn (Slider)
    turn: int = 0
    phase: str = "install"          # install | crank | over
    hp: int = 0
    block: int = 0
    heat: int = 0
    crank_power: int = 0
    turn_direction: str = "cw"      # direction of this turn's player cranks
    installs_left: int = 0
    dead_turn: bool = False         # this turn follows an Overheat: no cranks at all
    overheat_pending: bool = False  # next turn will be dead
    locked: bool = False            # no more cranks this turn
    enemy_hp: int = 0
    enemy_max_hp: int = 0
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
        s.rng = self.rng.copy()
        for name in ("gear", "queue", "discard", "hand"):
            setattr(s, name, list(getattr(self, name)))
        s.jams = dict(self.jams)
        s.fresh = set(self.fresh)
        s.installed = set(self.installed)
        s.moved = set(self.moved)
        s.part_triggers = dict(self.part_triggers)
        st = Stats(**self.stats.__dict__)
        st.overheats_by = dict(st.overheats_by)
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
    rng = Rng(seed)
    parts = [Part(uid, kind, mod) for uid, (kind, mod) in enumerate(deck_list(deck))]
    rng.shuffle(parts)
    s = State(rules=rules, enemy=spec, rng=rng, gear=[None] * rules.gear_size, queue=parts,
              hp=rules.player_hp, enemy_hp=spec.hp, log=[] if trace else None)
    if rules.enemy_hp_jitter:   # HP range per fight, so results don't hinge on exact damage breakpoints
        s.enemy_hp += rng.randrange(2 * rules.enemy_hp_jitter + 1) - rules.enemy_hp_jitter
    s.enemy_max_hp = s.enemy_hp
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
                if (part.kind, part.mod) in seen:      # identical parts give identical results
                    continue
                seen.add((part.kind, part.mod))
                acts.extend(("install", i, slot) for slot in range(len(s.gear)))
        if s.rules.crank_direction_lock and not s.dead_turn:
            acts += [("end_install", CW), ("end_install", CCW)]
        else:
            acts.append(("end_install",))
        return acts
    acts = []
    if _can_crank(s):
        acts.append(("crank",))
        if not s.rules.crank_direction_lock:
            acts.append(("crank_back",))
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
        s.turn_direction = action[1] if len(action) > 1 else CW
        _require(s.turn_direction in (CW, CCW), action)
        _require(s.turn_direction == CW or s.rules.crank_direction_lock, action)
        if s.dead_turn:
            s.locked = True
            _log(s, "overheated: no cranks this turn")
        else:
            _player_crank(s, s.turn_direction, free=True)
    elif kind in ("crank", "crank_back"):
        _require(s.phase == "crank" and _can_crank(s), action)
        _require(kind == "crank" or not s.rules.crank_direction_lock, action)
        s.crank_power -= 1
        if kind == "crank_back":
            direction = CCW
        else:
            direction = s.turn_direction if s.rules.crank_direction_lock else CW
        _player_crank(s, direction, free=False)
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
        "overheats": st.overheats, "heat_overflow": st.heat_overflow,
        "runaway_turns": st.runaway_turns,
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
    s.moved = set()
    s.fresh = set()
    s.installed = set()
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
    s.fresh.add(part.uid)
    s.installed.add(part.uid)
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
    _resolve(s, [("crank", direction, 0)])


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
            stack.append(("trigger", s.top, task[1], False, None, task[2]))
        else:
            _, slot, direction, from_coupler, uid, bonus = task
            if uid is not None:     # Coupler targets are bound to the part, not the slot
                slot = next((i for i, p in enumerate(s.gear) if p is not None and p.uid == uid), None)
                if slot is None:
                    continue
            if not _trigger(s, slot, direction, from_coupler, stack, bonus):
                stack.clear()


def _effective_part(s: State, slot: int) -> Optional[Part]:
    """The part whose effect fires when `slot` triggers. A Mirror acts as the part opposite it,
    attachment included."""
    part = s.gear[slot]
    if part is None:
        return None
    if part.kind != Kind.MIRROR:
        return part
    n = len(s.gear)
    if n % 2:
        return None
    opp = s.gear[(slot + n // 2) % n]
    if opp is None or opp.kind == Kind.MIRROR:
        return None
    return opp


def _effective_kind(s: State, slot: int) -> Optional[Kind]:
    eff = _effective_part(s, slot)
    return eff.kind if eff is not None else None


def _trigger(s: State, slot: int, direction: str, from_coupler: bool, stack: list, bonus: int = 0) -> bool:
    """Trigger the part in `slot`. `bonus` is extra flat damage (a Coil Spring's crank).
    Returns False if resolution must stop."""
    r = s.rules
    n = len(s.gear)
    part = s.gear[slot]
    if part is None:
        _log(s, f"  slot {slot}: empty, nothing happens")
        return True
    if slot in s.jams:
        _log(s, f"  {part}: jammed")
        return True
    eff = _effective_part(s, slot)
    kind = eff.kind if eff is not None else None
    specs = specs_for(r.part_overrides)
    if kind is None or not specs[kind].triggers:
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

    spec = specs[kind]
    s.triggers_turn += 1
    s.part_triggers[part.uid] = s.part_triggers.get(part.uid, 0) + 1
    heat = r.heat_per_trigger + spec.extra_heat
    if kind == Kind.SPRING:
        s.chain_springs += 1
        heat += s.chain_springs * r.spring_heat_step
    s.heat += heat
    label = str(part) if part.kind == kind else f"{part} as {kind}"
    notes = [f"+{heat} Heat"]

    base = spec.damage
    if spec.fresh_damage and part.uid in s.fresh:
        base = spec.fresh_damage
    if spec.per_part_damage:
        base += spec.per_part_damage * sum(p is not None for p in s.gear)
    if spec.per_install_damage:
        base += spec.per_install_damage * sum(1 for p in s.gear if p is not None and p.uid in s.installed)
    if spec.moved_bonus and part.uid in s.moved:
        base += spec.moved_bonus
    s.fresh.discard(part.uid)
    mult = 1 + r.amplifier_bonus * _adjacent_amplifiers(s, slot)
    if part.kind == Kind.MIRROR and part.mod == Mod.POLISH:
        mult += r.polish_bonus
    if base or spec.block:
        if base:
            dmg = int(base * mult)
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
    if bonus:
        s.enemy_hp -= bonus
        s.damage_turn += bonus
        notes.append(f"+{bonus} damage (Coil)")
    if kind == Kind.LOADER:
        notes.append(_load(s, slot, feeder=eff.mod == Mod.FEEDER))
    pulled = []
    if kind == Kind.MAGNET:
        note, pulled = _magnet(s, slot)
        notes.append(note)
        if pulled and r.magnet_block_per_pull:
            blk = int(r.magnet_block_per_pull * len(pulled) * mult)
            s.block += blk
            notes.append(f"{blk} Block")
        if pulled and r.magnet_damage_per_pull:
            dmg = int(r.magnet_damage_per_pull * len(pulled) * mult)
            s.enemy_hp -= dmg
            s.damage_turn += dmg
            notes.append(f"{dmg} damage")
    _log(s, f"  {label} triggers ({direction}): {', '.join(notes)} -> Heat {s.heat}")

    if s.enemy_hp <= 0:
        _close_turn_stats(s)
        _finish(s, "win", "enemy hp")
        return False
    if _check_overheat(s):
        s.stats.overheats_by[kind.value] = s.stats.overheats_by.get(kind.value, 0) + 1
        return False

    if kind == Kind.SPRING:
        stack.append(("crank", direction, r.coil_damage if eff.mod == Mod.COIL else 0))
    elif kind == Kind.COUPLER:
        left, right = (slot - 1) % n, (slot + 1) % n
        # Depth-first, left then right: push right first so left resolves (fully) first.
        for nb, d in ((right, CCW), (left, CW)):
            if s.gear[nb] is not None:
                stack.append(("trigger", nb, d, True, s.gear[nb].uid, 0))
    elif kind == Kind.MAGNET and eff.mod == Mod.CLAMP:
        # Clamp: each pulled part triggers, left side first (pushed last).
        for near, uid, d in reversed(pulled[:r.clamp_max_triggers]):
            stack.append(("trigger", near, d, False, uid, 0))
    return True


def _check_overheat(s: State) -> bool:
    if s.heat < s.rules.overheat_at:
        return False
    s.stats.overheats += 1
    s.stats.heat_overflow += s.heat - s.rules.overheat_at
    s.heat = 0
    s.locked = True
    s.overheat_pending = True
    _log(s, "  OVERHEAT: turn stops, Heat -> 0, next turn is dead")
    return True


def _adjacent_amplifiers(s: State, slot: int) -> int:
    n = len(s.gear)
    return sum(1 for nb in ((slot - 1) % n, (slot + 1) % n)
               if s.gear[nb] is not None and s.gear[nb].kind == Kind.AMPLIFIER)


def _load(s: State, slot: int, feeder: bool = False) -> str:
    """Install the next parts in the queue (rules.loader_loads of them). Each goes into an empty
    slot; once the gear is full, one load per trigger replaces a part (the part opposite the Loader,
    or with Feeder the next part to come up), sending the old part to the discard pile."""
    n = len(s.gear)
    step = -1 if s.turn_direction == CW else 1
    notes, replaced, loaded = [], False, set()
    for _ in range(s.rules.loader_loads):
        empty = [i for i, p in enumerate(s.gear) if p is None]
        if empty:
            if feeder:      # the next empty slot to come up in this turn's direction
                target = next(((s.top + step * k) % n for k in range(1, n)
                               if s.gear[(s.top + step * k) % n] is None), s.top)
            else:
                target = s.rng.choice(empty)
        elif s.rules.loader_replaces and not replaced:
            target = (s.top + step) % n if feeder else ((slot + n // 2) % n if n % 2 == 0 else None)
            if target is None or target == slot or (s.gear[target] and s.gear[target].uid in loaded):
                break       # never replace the Loader itself or a part this trigger just loaded
            replaced = True
        else:
            notes.append("gear full")
            break
        notes.append(_load_into(s, target))
        if s.gear[target] is not None:
            loaded.add(s.gear[target].uid)
    return "; ".join(notes)


def _load_into(s: State, target: int) -> str:
    if not s.queue:
        _recycle(s)
    if not s.queue:
        return "nothing to load"
    part = s.queue.pop(0)                 # the next part in the queue
    old = s.gear[target]
    if old is not None:
        s.discard.append(old)
    s.gear[target] = part
    s.fresh.add(part.uid)
    s.installed.add(part.uid)
    return f"loads {part} into slot {target}" + (f", replacing {old}" if old else "")


def _magnet(s: State, slot: int):
    """Pull both parts 2 slots away into empty neighbouring slots. Returns (note, pulled) where
    pulled lists (new slot, uid, direction towards the Magnet's side) in left-then-right order."""
    n = len(s.gear)
    moved, pulled = [], []
    for step, d in ((-1, CW), (1, CCW)):    # left side first, then right
        near, far = (slot + step) % n, (slot + 2 * step) % n
        if far == slot or s.gear[far] is None:
            continue
        if s.gear[near] is None or s.rules.magnet_swaps:
            s.gear[near], s.gear[far] = s.gear[far], s.gear[near]
            for p in (s.gear[near], s.gear[far]):
                if p is not None:
                    s.moved.add(p.uid)
            moved.append(f"{s.gear[near]} {far}->{near}" + (f" (swapped with {s.gear[far]})" if s.gear[far] else ""))
            pulled.append((near, s.gear[near].uid, d))
    return ("pulls " + ", ".join(moved) if moved else "pulls nothing"), pulled


# ---------------------------------------------------------------------------

def _require(ok: bool, action) -> None:
    if not ok:
        raise ValueError(f"illegal action {action}")


def _log(s: State, msg: str) -> None:
    if s.log is not None:
        s.log.append(msg)
