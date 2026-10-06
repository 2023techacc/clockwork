"""Run logic for the playtest prototype (Run-Design.md and Acts-Design.md, "Decisions").

A run is ACTS acts. Each act is a corridor of door choices (map option C, the playtest map) and
then the act's boss. Each door leads to a fight, an elite, a Workshop or a rest site. Cogs are
looted from enemies; part rewards can be scrapped for cogs. Attachments are items with a rarity
that sit in the inventory until attached to a part copy (permanent; up to rules.max_attachments per
part, no duplicates).

Machine upgrades (v18) are chosen, not bought: 1 of MACHINE_CHOICES at the start of the run and
after every boss but the last (the boss's exclusive reward). Workshops sell level-ups for the
upgrades you have. Between acts, half of the missing HP is healed.

Acts 2 and 3 use "veteran" placeholder enemies: the act-1 enemies, scaled up and armored (Acts-Design
option 3B) until themed districts are designed. Bosses are split by act (option 3D).

Everything here is plain data so the playtest page (docs/play.py) and simulated runs share it.
Fights themselves are played by the caller with engine.new_fight(run.fight_deck(), ...).
"""
import random
from dataclasses import replace

from .config import DEFAULT_RULES, RulesConfig
from .decks import DECKS, deck_list
from .enemies import ELITES, ENEMIES, NORMAL, scaled
from .parts import MOD_RARITY, Kind, Mod, fits

ACTS = 3
STOPS = 9                       # door choices before each boss
# Enemies grow stronger through each act: HP and attacks are scaled by
# ACT_SCALE[act] * (1 + GROWTH * stop / STOPS), so each boss gets the act's full growth.
GROWTH = 0.30                   # tuned (v15) for one act; 0.318+ rounds the Clock Tower chime up to 15
ACT_SCALE = [1.0, 1.35, 1.7]    # veteran strength per act (placeholder; tuned in v18)
ACT_ARMOR = [0, 1, 2]           # veteran trait: armor on normal enemies and elites in acts 2 and 3
ACT_BOSSES = [["clock_tower", "pendulum"], ["furnace", "dismantler"], ["iron_colossus"]]
BETWEEN_ACTS_HEAL = 0.5         # share of the missing HP healed when an act ends (Acts-Design 2B)
DOOR_WEIGHTS = {"fight": 4.0, "elite": 2.0, "workshop": 1.5, "rest": 1.5}

PART_TIER = {
    Kind.SPRING: "common", Kind.COOLANT: "common", Kind.MIRROR: "common",
    Kind.AMPLIFIER: "uncommon", Kind.COUPLER: "uncommon", Kind.LOADER: "uncommon", Kind.MAGNET: "uncommon",
    Kind.SLIDER: "uncommon", Kind.PRIMER: "uncommon", Kind.ASSEMBLY: "uncommon",
    Kind.HAMMER: "rare", Kind.BOILER: "rare",
}
# Reward and Workshop part weights per act: rarer parts later (Acts-Design 3, rarity across acts).
ACT_TIER_WEIGHT = [{"common": 5, "uncommon": 4, "rare": 1},
                   {"common": 3, "uncommon": 4, "rare": 2},
                   {"common": 2, "uncommon": 4, "rare": 3}]
TIER_WEIGHT = ACT_TIER_WEIGHT[0]
PART_PRICE = {"common": 30, "uncommon": 45, "rare": 65}
MOD_PRICE = {"common": 30, "uncommon": 55, "rare": 90}
# Elites: high risk, high return. No machine upgrades (v18); their loot leans rare instead: a part from
# the uncommon/rare tiers (rare weight x ELITE_RARE_PART), and 1 of ELITE_ATTACHMENTS uncommon/rare
# attachments (rare weight ELITE_RARE_WEIGHT against 3 for an uncommon).
ELITE_PART_TIERS = ("uncommon", "rare")
ELITE_RARE_PART = 2
ELITE_ATTACHMENTS = 3
ELITE_RARE_WEIGHT = 3
ELITE_COG_BONUS = 0
ELITE_SCALE = 0.9               # elites' HP and attacks are multiplied by this (on top of growth)
SCRAP_VALUE = 10
REST_HEAL = 8                   # v16 (was 15): healing and tinkering within 5 points
REPAIR = (15, 25)               # HP, price
REMOVE_PRICE, REMOVE_STEP = 40, 15

# Machine upgrades (v18): a pool with levels. Chosen at the start and after bosses; Workshops sell
# level-ups. Prices are placeholders until the economy is tuned across all three acts.
MACHINE = {
    "flywheel": {"name": "Flywheel", "text": "+1 Crank Power per turn", "max": 2},
    "heat_housing": {"name": "Heat Housing", "text": "+2 Heat before Overheat", "max": 2},
    "extra_hands": {"name": "Extra Hands", "text": "+1 install per turn", "max": 2},
    "bigger_gear": {"name": "Bigger Gear", "text": "8 gear slots instead of 6, and +1 Crank Power to turn it",
                    "max": 1},
    "frame": {"name": "Reinforced Frame", "text": "+8 max HP", "max": 3},
    "hopper": {"name": "Wide Hopper", "text": "+1 part offered (and shown) each turn", "max": 2},
    "cooling_fins": {"name": "Cooling Fins", "text": "1 Heat drains away at the start of each turn", "max": 2},
}
MACHINE_CHOICES = 3             # choose 1 of this many at the start and after a boss
LEVEL_PRICE = {2: 90, 3: 130}   # Workshop price of a level-up, by the level it reaches


class RunError(ValueError):
    pass


class Run:
    def __init__(self, deck="starter", seed=0, rules: RulesConfig = DEFAULT_RULES, stops=STOPS, growth=None,
                 boss=None, acts=ACTS):
        self.seed, self.base_rules, self.stops, self.acts = int(seed), rules, stops, acts
        self.growth = GROWTH if growth is None else growth
        self.rng = random.Random(self.seed * 7919 + 17)
        # Every act's boss is picked up front and shown, so players can plan; `boss` fixes act 1's.
        boss_rng = random.Random(self.seed * 31 + 5)
        self.bosses = [boss_rng.choice(ACT_BOSSES[min(a, len(ACT_BOSSES) - 1)]) for a in range(acts)]
        if boss:
            self.bosses[0] = boss
        self.deck_name = deck
        self.cards = [{"id": i, "kind": k, "mods": list(m)} for i, (k, m) in enumerate(deck_list(DECKS[deck]))]
        self.next_id = len(self.cards)
        self.inventory = []             # unattached attachments (Mod)
        self.machine = []               # machine upgrade keys; a key appears once per level
        self.hp = rules.player_hp
        self.cogs = 0
        self.act = 0                    # 0-based
        self.stop = 0                   # index of the next door choice; == stops means the boss
        self.node = None                # current node type
        self.enemy = None
        self.removals = 0
        self.history = []
        self.seen_elites = []
        self.doors = []
        # start | doors | fight | reward | rest | workshop | boss_reward | won | lost
        self.phase = "start"
        self.offer = {"machines": self._roll_machines()}

    @property
    def boss(self):
        return self.bosses[self.act]

    # ------------------------------------------------------------------ derived
    def level(self, key) -> int:
        return self.machine.count(key)

    def rules(self) -> RulesConfig:
        r, lv = self.base_rules, self.level
        return replace(
            r,
            crank_power=r.crank_power + lv("flywheel") + lv("bigger_gear"),
            overheat_at=r.overheat_at + 2 * lv("heat_housing"),
            installs_per_turn=r.installs_per_turn + lv("extra_hands"),
            gear_size=8 if lv("bigger_gear") else r.gear_size,
            player_hp=r.player_hp + 8 * lv("frame"),
            offered_per_turn=r.offered_per_turn + lv("hopper"),
            queue_visible=r.queue_visible + lv("hopper"),
            heat_decay=r.heat_decay + lv("cooling_fins"),
        )

    def fight_deck(self) -> dict:
        deck = {}
        for c in self.cards:
            key = (c["kind"], tuple(c["mods"]))
            deck[key] = deck.get(key, 0) + 1
        return deck

    def enemy_scale(self) -> float:
        return ACT_SCALE[min(self.act, len(ACT_SCALE) - 1)] * (1 + self.growth * min(self.stop, self.stops) / self.stops)

    def enemy_spec(self):
        """The current enemy, grown for the act and how far into it the run is. In acts 2 and 3, normal
        enemies and elites are veterans: scaled and armored."""
        spec = ENEMIES[self.enemy]
        f = self.enemy_scale()
        if spec.elite:
            f *= ELITE_SCALE
        if f != 1:
            spec = scaled(spec, f)
        armor = ACT_ARMOR[min(self.act, len(ACT_ARMOR) - 1)]
        if armor and self.node != "boss":
            spec = replace(spec, armor=spec.armor + armor)
        return spec

    def fight_seed(self) -> int:
        return self.seed * 1000 + self.act * 100 + self.stop

    def max_hp(self) -> int:
        return self.rules().player_hp

    # ------------------------------------------------------------------ machine upgrades
    def _roll_machines(self):
        free = [k for k in MACHINE if k not in self.machine]
        return self.rng.sample(free, min(MACHINE_CHOICES, len(free)))

    def choose_start(self, key: str = ""):
        """Pick the starting machine upgrade (1 of the offered; '' takes none)."""
        self._need("start")
        if key:
            self._check_offer("machines", key)
            self._install_machine(key)
        self.history.append({"act": self.act, "stop": -1, "node": "start", "machine": key or None})
        self.offer = {}
        self.phase = "doors"
        self.doors = self._make_doors()
        return self

    def choose_boss_reward(self, key: str = ""):
        """After a boss (not the last): the boss's exclusive reward, 1 of the offered machine upgrades
        ('' takes none); then half of the missing HP heals and the next act begins."""
        self._need("boss_reward")
        if key:
            self._check_offer("machines", key)
            self._install_machine(key)
        self.history[-1]["boss_reward"] = key or None
        self.hp += int((self.max_hp() - self.hp) * BETWEEN_ACTS_HEAL)
        self.act += 1
        self.stop = -1
        self._advance()
        return self

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
            return self.boss
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
        entry = {"act": self.act, "stop": self.stop, "node": self.node, "enemy": self.enemy, "result": result,
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
            if self.act + 1 >= self.acts:
                self.phase = "won"
            else:
                self.phase = "boss_reward"
                self.offer = {"machines": self._roll_machines()}
            return self
        self.hp = min(self.max_hp(), max(0, hp) + self.base_rules.heal_between_fights)
        if self.node == "elite":
            self.cogs += ELITE_COG_BONUS
            entry["cogs"] = loot + ELITE_COG_BONUS
            self.offer = {"parts": [k.value for k in self._roll_parts(3, ELITE_PART_TIERS, ELITE_RARE_PART)],
                          "attachments": [m.value for m in self._roll_mods(["uncommon", "rare"], ELITE_ATTACHMENTS,
                                                                           ELITE_RARE_WEIGHT)]}
        else:
            self.offer = {"parts": [k.value for k in self._roll_parts(3)]}
        self.phase = "reward"
        return self

    def take_reward(self, part: str = "", attachment: str = "", scrap: bool = False):
        """After a win: take one offered part (or scrap the reward for cogs, or skip); after an
        elite, one offered attachment into the inventory."""
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
        """choice 'heal' (+REST_HEAL HP) or 'tinker' (take both offered common attachments)."""
        self._need("rest")
        if choice == "heal":
            self.hp = min(self.max_hp(), self.hp + REST_HEAL)
        elif choice == "tinker":
            attachment = ", ".join(self.offer["attachments"])
            self.inventory += [Mod(m) for m in self.offer["attachments"]]
        else:
            raise RunError(f"unknown rest choice {choice}")
        self.history.append({"act": self.act, "stop": self.stop, "node": "rest", "choice": choice,
                             "attachment": attachment or None})
        self._advance()
        return self

    # ------------------------------------------------------------------ workshop
    def _stock(self):
        parts = [{"kind": k.value, "price": PART_PRICE[PART_TIER[k]], "sold": False} for k in self._roll_parts(3)]
        mods = [{"mod": m.value, "price": MOD_PRICE[MOD_RARITY[m]], "sold": False}
                for m in self._roll_mods(["uncommon", "rare"], 2)]
        # Level-ups for the machine upgrades you have (new upgrades only come from the start and bosses).
        machines = []
        for k in dict.fromkeys(self.machine):
            lv = self.level(k)
            if lv < MACHINE[k]["max"]:
                machines.append({"key": k, "name": MACHINE[k]["name"], "text": MACHINE[k]["text"], "level": lv + 1,
                                 "price": LEVEL_PRICE[lv + 1], "sold": False})
        return {"parts": parts, "attachments": mods, "machines": machines}

    def remove_price(self):
        return REMOVE_PRICE + REMOVE_STEP * self.removals

    def buy(self, what: str, index: int = 0):
        """what: 'part', 'attachment', 'machine' (a level-up) or 'repair'."""
        self._need("workshop")
        if what == "repair":
            self._pay(REPAIR[1])
            self.hp = min(self.max_hp(), self.hp + REPAIR[0])
            return self
        shelf = self.offer["parts" if what == "part" else "attachments" if what == "attachment" else "machines"]
        item = shelf[int(index)]
        if item["sold"]:
            raise RunError("already sold")
        self._pay(item["price"])
        item["sold"] = True
        if what == "part":
            self._add_card(Kind(item["kind"]))
        elif what == "attachment":
            self.inventory.append(Mod(item["mod"]))
        else:
            self._install_machine(item["key"])
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
        self.history.append({"act": self.act, "stop": self.stop, "node": "workshop", "cogs_left": self.cogs})
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
    def _roll_parts(self, n, tiers=None, rare_bonus=1):
        weight = ACT_TIER_WEIGHT[min(self.act, len(ACT_TIER_WEIGHT) - 1)]
        kinds = [k for k in PART_TIER if tiers is None or PART_TIER[k] in tiers]
        weights = [weight[PART_TIER[k]] * (rare_bonus if PART_TIER[k] == "rare" else 1) for k in kinds]
        out = []
        while len(out) < min(n, len(kinds)):
            k = self.rng.choices(kinds, weights)[0]
            if k not in out:
                out.append(k)
        return out

    def _roll_mods(self, rarities, n, rare_weight=1):
        pool = [m for m in Mod if MOD_RARITY[m] in rarities]
        weights = [3 if MOD_RARITY[m] != "rare" else rare_weight for m in pool]
        out = []
        while len(out) < min(n, len(pool)):
            m = self.rng.choices(pool, weights)[0]
            if m not in out:
                out.append(m)
        return out

    def _install_machine(self, key):
        if self.level(key) >= MACHINE[key]["max"]:
            raise RunError(f"{MACHINE[key]['name']} is at its highest level")
        before = self.max_hp()
        self.machine.append(key)
        self.hp += self.max_hp() - before      # a max-HP upgrade also adds that much HP

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
            "deck_name": self.deck_name, "seed": self.seed, "boss": self.boss, "bosses": self.bosses,
            "act": self.act, "acts": self.acts, "phase": self.phase, "stop": self.stop,
            "stops": self.stops, "doors": self.doors if self.phase == "doors" else [],
            "node": self.node, "enemy": self.enemy, "enemy_scale": round(self.enemy_scale(), 3),
            "hp": self.hp, "max_hp": self.max_hp(),
            "cogs": self.cogs, "offer": self.offer, "remove_price": self.remove_price(),
            "repair": {"hp": REPAIR[0], "price": REPAIR[1]}, "rest_heal": REST_HEAL, "scrap": SCRAP_VALUE,
            "heal_after_fight": self.base_rules.heal_between_fights, "between_acts_heal": BETWEEN_ACTS_HEAL,
            "cards": [{"id": c["id"], "kind": c["kind"].value, "mods": [m.value for m in c["mods"]]}
                      for c in self.cards],
            "inventory": [{"mod": m.value, "rarity": MOD_RARITY[m],
                           "fits": [c["id"] for c in self.cards if self.can_attach(m, c)]}
                          for m in self.inventory],
            "machine": [{"key": k, "name": MACHINE[k]["name"], "text": MACHINE[k]["text"], "level": self.level(k),
                         "max": MACHINE[k]["max"]} for k in dict.fromkeys(self.machine)],
            "history": self.history,
        }
