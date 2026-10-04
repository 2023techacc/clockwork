"""Run logic for the playtest prototype (Run-Design.md, "Decisions").

A district is a corridor of door choices (map option C), then the boss. Each door leads to a
fight, an elite, a Workshop or a rest site. Cogs are looted from enemies; part rewards can be
scrapped for cogs. Attachments are items with a rarity that sit in the inventory until attached
to a part copy (permanent; up to rules.max_attachments per part, no duplicates).

Everything here is plain data so the playtest page (docs/play.py) and simulated runs share it.
Fights themselves are played by the caller with engine.new_fight(run.fight_deck(), ...).
"""
import random
from dataclasses import replace

from .config import DEFAULT_RULES, RulesConfig
from .decks import DECKS, deck_list
from .enemies import BOSSES, ELITES, ENEMIES, NORMAL
from .parts import MOD_RARITY, Kind, Mod, fits

STOPS = 9                       # door choices before the boss
DOOR_WEIGHTS = {"fight": 4.0, "elite": 2.0, "workshop": 1.5, "rest": 1.5}

PART_TIER = {
    Kind.SPRING: "common", Kind.COOLANT: "common", Kind.MIRROR: "common",
    Kind.AMPLIFIER: "uncommon", Kind.COUPLER: "uncommon", Kind.LOADER: "uncommon", Kind.MAGNET: "uncommon",
    Kind.SLIDER: "uncommon", Kind.PRIMER: "uncommon", Kind.ASSEMBLY: "uncommon",
    Kind.HAMMER: "rare",
}
TIER_WEIGHT = {"common": 5, "uncommon": 4, "rare": 1}
PART_PRICE = {"common": 30, "uncommon": 45, "rare": 65}
MOD_PRICE = {"common": 30, "uncommon": 55, "rare": 90}
SCRAP_VALUE = 10
REST_HEAL = 15
REPAIR = (15, 25)               # HP, price
REMOVE_PRICE, REMOVE_STEP = 40, 15
MACHINE = {
    "flywheel": ("Flywheel", "+1 Crank Power per turn", 120),
    "heat_housing": ("Heat Housing", "+2 Heat before Overheat", 110),
    "extra_hands": ("Extra Hands", "+1 install per turn", 130),
    "bigger_gear": ("Bigger Gear", "8 gear slots instead of 6", 120),
}


class RunError(ValueError):
    pass


class Run:
    def __init__(self, deck="starter", seed=0, rules: RulesConfig = DEFAULT_RULES, stops=STOPS):
        self.seed, self.base_rules, self.stops = int(seed), rules, stops
        self.rng = random.Random(self.seed * 7919 + 17)
        self.deck_name = deck
        self.cards = [{"id": i, "kind": k, "mods": list(m)} for i, (k, m) in enumerate(deck_list(DECKS[deck]))]
        self.next_id = len(self.cards)
        self.inventory = []             # unattached attachments (Mod)
        self.machine = []               # machine upgrade keys
        self.hp = rules.player_hp
        self.cogs = 0
        self.stop = 0                   # index of the next door choice; == stops means the boss
        self.phase = "doors"            # doors | fight | reward | rest | workshop | won | lost
        self.node = None                # current node type
        self.enemy = None
        self.offer = {}                 # what the current phase offers
        self.removals = 0
        self.history = []
        self.seen_elites = []
        self.doors = self._make_doors()

    # ------------------------------------------------------------------ derived
    def rules(self) -> RulesConfig:
        r = self.base_rules
        if "flywheel" in self.machine:
            r = replace(r, crank_power=r.crank_power + 1)
        if "heat_housing" in self.machine:
            r = replace(r, overheat_at=r.overheat_at + 2)
        if "extra_hands" in self.machine:
            r = replace(r, installs_per_turn=r.installs_per_turn + 1)
        if "bigger_gear" in self.machine:
            r = replace(r, gear_size=8)
        return r

    def fight_deck(self) -> dict:
        deck = {}
        for c in self.cards:
            key = (c["kind"], tuple(c["mods"]))
            deck[key] = deck.get(key, 0) + 1
        return deck

    def fight_seed(self) -> int:
        return self.seed * 100 + self.stop

    def max_hp(self) -> int:
        return self.base_rules.player_hp

    # ------------------------------------------------------------------ map
    def _make_doors(self):
        if self.stop >= self.stops:
            return ["boss"]
        if self.stop < 2:
            return ["fight"]
        if self.stop == self.stops - 1:
            return ["rest", "workshop"]
        types = list(DOOR_WEIGHTS)
        weights = [DOOR_WEIGHTS[t] for t in types]
        doors = []
        while len(doors) < 3:
            t = self.rng.choices(types, weights)[0]
            if t not in doors:
                doors.append(t)
        return doors

    def choose_door(self, index: int):
        self._need("doors")
        node = self.doors[int(index)]
        self.node = node
        if node in ("fight", "elite", "boss"):
            self.enemy = self._pick_enemy(node)
            self.phase = "fight"
        elif node == "rest":
            self.phase = "rest"
            self.offer = {"attachments": [m.value for m in self._roll_mods(["common"], 2)]}
        elif node == "workshop":
            self.phase = "workshop"
            self.offer = self._stock()
        return self

    def _pick_enemy(self, node):
        if node == "boss":
            return BOSSES[0]
        if node == "elite":
            fresh = [e for e in ELITES if e not in self.seen_elites] or ELITES
            e = self.rng.choice(fresh)
            self.seen_elites.append(e)
            return e
        last = self.history[-1]["enemy"] if self.history and "enemy" in self.history[-1] else None
        return self.rng.choice([e for e in NORMAL if e != last])

    def _advance(self):
        self.stop += 1
        self.node, self.enemy, self.offer = None, None, {}
        self.doors = self._make_doors()
        self.phase = "doors"

    # ------------------------------------------------------------------ fights
    def finish_fight(self, result: str, hp: int, turns: int = 0, actions=None):
        """Record the fight played with fight_deck()/rules()/fight_seed() against self.enemy."""
        self._need("fight")
        entry = {"stop": self.stop, "node": self.node, "enemy": self.enemy, "result": result,
                 "hp_start": self.hp, "hp_end": max(0, hp), "turns": turns}
        if actions is not None:
            entry["actions"] = actions
        self.history.append(entry)
        if result != "win":
            self.phase = "lost"
            return self
        spec = ENEMIES[self.enemy]
        loot = max(1, round(spec.cogs * self.rng.uniform(0.9, 1.1)))
        self.cogs += loot
        entry["cogs"] = loot
        if self.node == "boss":
            self.hp = max(0, hp)
            self.phase = "won"
            return self
        self.hp = min(self.max_hp(), max(0, hp) + self.base_rules.heal_between_fights)
        self.offer = {"parts": [k.value for k in self._roll_parts(3)]}
        if self.node == "elite":
            self.offer["attachments"] = [m.value for m in self._roll_mods(["uncommon", "rare"], 2)]
        self.phase = "reward"
        return self

    def take_reward(self, part: str = "", attachment: str = "", scrap: bool = False):
        """After a win: take one offered part (or scrap the reward for cogs, or skip), and for an
        elite one offered attachment into the inventory."""
        self._need("reward")
        entry = self.history[-1]
        if part:
            self._check_offer("parts", part)
            self._add_card(Kind(part))
            entry["reward"] = part
        elif scrap:
            self.cogs += SCRAP_VALUE
            entry["reward"] = "scrapped"
        if attachment:
            self._check_offer("attachments", attachment)
            self.inventory.append(Mod(attachment))
            entry["attachment"] = attachment
        self._advance()
        return self

    # ------------------------------------------------------------------ rest
    def rest(self, choice: str, attachment: str = ""):
        """choice 'heal' (+REST_HEAL HP) or 'tinker' (take one offered common attachment)."""
        self._need("rest")
        if choice == "heal":
            self.hp = min(self.max_hp(), self.hp + REST_HEAL)
        elif choice == "tinker":
            self._check_offer("attachments", attachment)
            self.inventory.append(Mod(attachment))
        else:
            raise RunError(f"unknown rest choice {choice}")
        self.history.append({"stop": self.stop, "node": "rest", "choice": choice, "attachment": attachment or None})
        self._advance()
        return self

    # ------------------------------------------------------------------ workshop
    def _stock(self):
        parts = [{"kind": k.value, "price": PART_PRICE[PART_TIER[k]], "sold": False} for k in self._roll_parts(3)]
        mods = [{"mod": m.value, "price": MOD_PRICE[MOD_RARITY[m]], "sold": False}
                for m in self._roll_mods(["uncommon", "rare"], 2)]
        free = [k for k in MACHINE if k not in self.machine]
        machine = None
        if free and self.rng.random() < 0.5:
            k = self.rng.choice(free)
            machine = {"key": k, "name": MACHINE[k][0], "text": MACHINE[k][1], "price": MACHINE[k][2], "sold": False}
        return {"parts": parts, "attachments": mods, "machine": machine}

    def remove_price(self):
        return REMOVE_PRICE + REMOVE_STEP * self.removals

    def buy(self, what: str, index: int = 0):
        """what: 'part', 'attachment', 'machine' or 'repair'."""
        self._need("workshop")
        if what == "repair":
            self._pay(REPAIR[1])
            self.hp = min(self.max_hp(), self.hp + REPAIR[0])
            return self
        if what == "machine":
            item = self.offer.get("machine")
            if not item or item["sold"]:
                raise RunError("no machine upgrade for sale")
            self._pay(item["price"])
            item["sold"] = True
            self.machine.append(item["key"])
            return self
        shelf = self.offer["parts" if what == "part" else "attachments"]
        item = shelf[int(index)]
        if item["sold"]:
            raise RunError("already sold")
        self._pay(item["price"])
        item["sold"] = True
        if what == "part":
            self._add_card(Kind(item["kind"]))
        else:
            self.inventory.append(Mod(item["mod"]))
        return self

    def remove_card(self, card_id: int):
        self._need("workshop")
        card = self._card(card_id)
        if card["mods"]:
            raise RunError("can't remove a part with attachments")
        if len(self.cards) <= 6:
            raise RunError("the deck can't go below 6 parts")
        self._pay(self.remove_price())
        self.removals += 1
        self.cards.remove(card)
        return self

    def sell_attachment(self, inventory_index: int):
        self._need("workshop")
        mod = self.inventory.pop(int(inventory_index))
        self.cogs += MOD_PRICE[MOD_RARITY[mod]] // 2
        return self

    def leave_workshop(self):
        self._need("workshop")
        self.history.append({"stop": self.stop, "node": "workshop", "cogs_left": self.cogs})
        self._advance()
        return self

    # ------------------------------------------------------------------ attachments
    def can_attach(self, mod: Mod, card) -> bool:
        return (fits(mod, card["kind"]) and mod not in card["mods"]
                and len(card["mods"]) < self.base_rules.max_attachments)

    def attach(self, inventory_index: int, card_id: int):
        """Permanently attach an inventory attachment to a part copy (not during a fight)."""
        if self.phase == "fight":
            raise RunError("can't attach during a fight")
        mod = self.inventory[int(inventory_index)]
        card = self._card(card_id)
        if not self.can_attach(mod, card):
            raise RunError(f"{mod.value} can't go on that {card['kind'].value}")
        self.inventory.pop(int(inventory_index))
        card["mods"] = sorted(card["mods"] + [mod], key=lambda m: m.value)
        return self

    # ------------------------------------------------------------------ helpers
    def _roll_parts(self, n):
        kinds = list(PART_TIER)
        weights = [TIER_WEIGHT[PART_TIER[k]] for k in kinds]
        out = []
        while len(out) < n:
            k = self.rng.choices(kinds, weights)[0]
            if k not in out:
                out.append(k)
        return out

    def _roll_mods(self, rarities, n):
        pool = [m for m in Mod if MOD_RARITY[m] in rarities]
        weights = [3 if MOD_RARITY[m] != "rare" else 1 for m in pool]
        out = []
        while len(out) < min(n, len(pool)):
            m = self.rng.choices(pool, weights)[0]
            if m not in out:
                out.append(m)
        return out

    def _add_card(self, kind):
        self.cards.append({"id": self.next_id, "kind": kind, "mods": []})
        self.next_id += 1

    def _card(self, card_id):
        for c in self.cards:
            if c["id"] == int(card_id):
                return c
        raise RunError(f"no part {card_id}")

    def _pay(self, price):
        if self.cogs < price:
            raise RunError("not enough cogs")
        self.cogs -= price

    def _need(self, phase):
        if self.phase != phase:
            raise RunError(f"not in {phase} (now {self.phase})")

    def _check_offer(self, key, value):
        if value not in self.offer.get(key, []):
            raise RunError(f"{value} was not offered")

    # ------------------------------------------------------------------ view
    def view(self) -> dict:
        return {
            "deck_name": self.deck_name, "seed": self.seed, "phase": self.phase, "stop": self.stop,
            "stops": self.stops, "doors": self.doors if self.phase == "doors" else [],
            "node": self.node, "enemy": self.enemy, "hp": self.hp, "max_hp": self.max_hp(),
            "cogs": self.cogs, "offer": self.offer, "remove_price": self.remove_price(),
            "repair": {"hp": REPAIR[0], "price": REPAIR[1]}, "rest_heal": REST_HEAL, "scrap": SCRAP_VALUE,
            "heal_after_fight": self.base_rules.heal_between_fights,
            "cards": [{"id": c["id"], "kind": c["kind"].value, "mods": [m.value for m in c["mods"]]}
                      for c in self.cards],
            "inventory": [{"mod": m.value, "rarity": MOD_RARITY[m],
                           "fits": [c["id"] for c in self.cards if self.can_attach(m, c)]}
                          for m in self.inventory],
            "machine": [{"key": k, "name": MACHINE[k][0], "text": MACHINE[k][1]} for k in self.machine],
            "history": self.history,
        }
