"""Bridge between the browser page and the Clockwork simulator (runs inside Pyodide).

Every call returns a JSON string describing the whole screen, so the page never keeps game
state of its own and always follows the simulator's rules exactly.
"""
import json

from clockwork import engine
from clockwork.config import DEFAULT_RULES as R
from clockwork.decks import DECKS, deck_list
from clockwork.enemies import ENEMIES
from clockwork.engine import CCW, CW, apply, legal_actions, new_fight
from clockwork.parts import SPECS, Kind, Mod

STATE = None
SETUP = {}
ACTIONS = []        # every action taken, so a fight can be replayed exactly in the simulator
LOG_SEEN = 0


def _describe_parts():
    s = {k: SPECS[k] for k in Kind}
    pct = lambda x: f"{round(x * 100)}%"
    return {
        "Striker": f"Deal {s[Kind.STRIKER].damage} damage.",
        "Plate": f"Gain {s[Kind.PLATE].block} Block.",
        "Spring": "Crank again for free, continuing in the direction the trigger came from. "
                  "Extra Heat: +1 for the 1st Spring in a chain, +2 for the 2nd, +3 for the 3rd...",
        "Mirror": "Acts exactly as the part directly opposite it (attachment included). Can't copy a Mirror.",
        "Amplifier": f"Passive: neighbours' damage and Block +{pct(R.amplifier_bonus)}. Never triggers.",
        "Coupler": f"Triggers its left neighbour, then its right one. Can't trigger a Coupler. "
                   f"+{s[Kind.COUPLER].extra_heat} Heat.",
        "Loader": f"Installs the next {R.loader_loads} queue parts into empty slots. If the gear is full, "
                  "one replaces the part opposite the Loader.",
        "Coolant": f"Remove {s[Kind.COOLANT].cooling} Heat.",
        "Hammer": f"Deal {s[Kind.HAMMER].damage} damage. +{s[Kind.HAMMER].extra_heat} Heat.",
        "Magnet": f"Pulls the parts 2 slots away into the slots next to it (swapping if occupied). "
                  f"{R.magnet_block_per_pull} Block per part pulled.",
        "Primer": f"Deal {s[Kind.PRIMER].damage} damage, or {s[Kind.PRIMER].fresh_damage} if it was "
                  "installed this turn.",
        "Assembly": f"Deal {s[Kind.ASSEMBLY].per_install_damage} damage per part installed this turn.",
        "Slider": f"Deal {s[Kind.SLIDER].damage} damage, +{s[Kind.SLIDER].moved_bonus} if a Magnet moved "
                  "it this turn.",
        "+Coil": f"(Spring) The part this Spring's crank triggers also deals {R.coil_damage} damage.",
        "+Polish": f"(Mirror) The copy's damage and Block +{pct(R.polish_bonus)}.",
        "+Clamp": f"(Magnet) The first part it pulls is triggered.",
        "+Feeder": "(Loader) Loads into the next slot to come up instead of a random one.",
    }


def options():
    decks = {name: [f"{k.value}{'+' + m.value if m else ''}" for k, m in deck_list(d)]
             for name, d in DECKS.items()}
    enemies = {name: {"hp": e.hp, "crank_limit": e.crank_limit, "chime_every": e.chime_every,
                      "chime_damage": e.chime_damage} for name, e in ENEMIES.items()}
    return json.dumps({"decks": decks, "enemies": enemies, "parts": _describe_parts(),
                       "rules": {"overheat_at": R.overheat_at, "crank_power": R.crank_power,
                                 "installs": R.installs_per_turn, "player_hp": R.player_hp,
                                 "hp_jitter": R.enemy_hp_jitter}})


def start(deck, enemy, seed):
    global STATE, ACTIONS, LOG_SEEN, SETUP
    SETUP = {"deck": deck, "enemy": enemy, "seed": int(seed)}
    STATE = new_fight(DECKS[deck], enemy, seed=int(seed), trace=True)
    ACTIONS, LOG_SEEN = [], 0
    return view()


def _act(action):
    ACTIONS.append(list(action))
    apply(STATE, tuple(action))
    return view()


def install(hand_index, slot):
    """Install a hand part. Identical parts are interchangeable, so use the first copy."""
    part = STATE.hand[hand_index]
    first = next(i for i, p in enumerate(STATE.hand) if (p.kind, p.mod) == (part.kind, part.mod))
    return _act(("install", first, int(slot)))


def end_install(direction):
    acts = [a for a in legal_actions(STATE) if a[0] == "end_install"]
    if len(acts) == 1:          # dead turn after an Overheat: no direction to pick
        return _act(acts[0])
    return _act(("end_install", CW if direction == "cw" else CCW))


def crank():
    return _act(("crank",))


def end_turn():
    return _act(("end_turn",))


def _part(p, slot=None):
    if p is None:
        return None
    d = {"kind": p.kind.value, "mod": p.mod.value if p.mod else None}
    if slot is not None:
        d["jammed"] = slot in STATE.jams
    return d


def _intent_text(act):
    if act[0] == "attack":
        return f"Attack {act[1]}"
    if act[0] == "jam":
        p = STATE.gear[act[1]]
        return f"Jam {p.kind.value if p else 'an empty slot'} ({act[2]} turns)"
    if act[0] == "wind_back":
        return "Wind Back (gear turns 1 step counter-clockwise)"
    if act[0] == "unscrew":
        p = STATE.gear[act[1]]
        return f"Unscrew {p.kind.value if p else 'a part'}"
    return str(act)


def view():
    global LOG_SEEN
    s = STATE
    legal = legal_actions(s)
    new_log = s.log[LOG_SEEN:]
    LOG_SEEN = len(s.log)
    n = len(s.gear)
    return json.dumps({
        "setup": SETUP,
        "turn": s.turn, "phase": s.phase, "result": s.result, "reason": s.reason,
        "hp": s.hp, "max_hp": s.rules.player_hp, "block": s.block,
        "heat": s.heat, "overheat_at": s.rules.overheat_at,
        "crank_power": s.crank_power, "installs_left": s.installs_left,
        "dead_turn": s.dead_turn, "locked": s.locked, "turn_direction": s.turn_direction,
        "enemy": {"name": s.enemy.name, "hp": max(0, s.enemy_hp), "max_hp": s.enemy_max_hp,
                  "intent": [_intent_text(a) for a in s.intent],
                  "crank_limit": s.enemy.crank_limit, "cranks_used": s.cranks_used,
                  "chime_every": s.enemy.chime_every, "chime_damage": s.enemy.chime_damage},
        "gear": [_part(p, i) for i, p in enumerate(s.gear)],
        "top": s.top,
        "arrival": [(s.top - k) % n for k in range(n)],
        "hand": [_part(p) for p in s.hand],
        "next": [_part(p) for p in s.visible_queue()],
        "queue_size": len(s.queue), "discard_size": len(s.discard),
        "can_install": any(a[0] == "install" for a in legal),
        "can_pick_direction": ("end_install", CW) in legal,
        "can_end_install": any(a[0] == "end_install" for a in legal),
        "can_crank": ("crank",) in legal,
        "can_end_turn": ("end_turn",) in legal,
        "new_log": new_log,
        "summary": engine.summary(s) if s.result else None,
        "actions": ACTIONS,
    })
