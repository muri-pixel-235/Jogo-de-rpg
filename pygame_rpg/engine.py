"""Regras de combate independentes da interface Pygame."""
from __future__ import annotations

from dataclasses import dataclass, field
import random
from copy import deepcopy
from typing import Any

from batalha import (ATAQUES, CHANCE_RELIQUIA_INIMIGO, CLASSES, CLIMAS, CONTRATOS, EFEITOS, ELEMENTOS,
                     ESQUIVA, INIMIGOS, ITENS, RELIQUIAS, RELIQUIAS_INIMIGO)


@dataclass
class Fighter:
    name: str
    side: str
    kind: str
    data: dict[str, Any]
    max_hp: int = 0
    hp: int = 0
    max_energy: int = 0
    energy: int = 0
    shield: int = 0
    speed: int = 0
    element: str = "neutro"
    effects: dict[str, int] = field(default_factory=dict)
    relic: str = "nenhum"
    form: str | None = None
    contract: str | None = None
    defending: bool = False
    fled: bool = False
    alive: bool = True
    cooldowns: dict[str, int] = field(default_factory=dict)
    elixir_used: bool = False
    max_hp_bonus_turns: int = 0
    vulnerability: dict[str, float] = field(default_factory=dict)
    summon: bool = False
    restrictions: set[str] = field(default_factory=set)
    original_max_hp: int = 0
    charging: dict[str, Any] | None = None
    attack_count: int = 0
    elemental_marks: set[str] = field(default_factory=set)
    buffs: dict[str, int] = field(default_factory=dict)

    @classmethod
    def create(cls, name: str, side: str, kind: str, data: dict[str, Any], relic: str = "nenhum") -> "Fighter":
        base_hp = int(data.get("vida", 100))
        base_energy = int(data.get("energia", 100))
        if kind in INIMIGOS:
            relic_data = RELIQUIAS_INIMIGO.get(relic, {})
        else:
            relic_data = RELIQUIAS.get(relic, {})
        mods = relic_data.get("mods", {})
        hp = round(base_hp * (1 + relic_data.get("vida_max", 0)))
        base_energy = round(base_energy * (1 + mods.get("energia_max", 0)))
        speed = round(int(data.get("velocidade", 30)) * mods.get("velocidade_mult", 1)) + mods.get("velocidade", 0)
        shield = round(int(data.get("escudo", 0)) * mods.get("escudo_mult", 1))
        fighter = cls(name, side, kind, deepcopy(data), hp, hp, base_energy, base_energy,
                      shield, speed, data.get("elemento", "neutro"), relic=relic)
        fighter.original_max_hp = hp
        if relic == "pingente da rejeição":
            fighter.restrictions.update({"fugir", "cura", "arremessavel"})
            fighter.shield = 0
        if relic == "amuleto da lua de sangue":
            fighter.data["dano_global_mult"] = 1.2
            fighter.data["defesa"] = round(fighter.data.get("defesa", 0) * 1.2)
            fighter.data["critico"] = round(fighter.data.get("critico", 0) * 1.2)
        return fighter

    @property
    def is_player(self) -> bool:
        return self.side == "player"

    def available_attacks(self) -> list[str]:
        names = list(self.data.get("ataques", []))
        if self.form:
            form = next((f for f in self.data.get("formas", []) if f.get("nome") == self.form), {})
            names += form.get("ataques", [])
        return [name for name in names if name in ATAQUES]

    def damage_multiplier(self) -> float:
        mult = 1.0
        if self.effects.get("medo", 0):
            mult *= 0.7
        if self.buffs.get("forca", 0):
            mult *= 1.25
        if self.contract:
            mult *= CONTRATOS.get(self.contract, {}).get("mods", {}).get("dano", 1)
        if self.relic != "nenhum":
            relics = RELIQUIAS_INIMIGO if self.kind in INIMIGOS else RELIQUIAS
            mult *= relics.get(self.relic, {}).get("mods", {}).get("dano", 1)
        if self.data.get("maximadora_mult"):
            mult *= self.data["maximadora_mult"]
        mult *= self.data.get("dano_global_mult", 1) * self.data.get("terrain_damage_mult", 1)
        mult *= self.data.get("habilidade", {}).get("mods", {}).get("dano", 1)
        if self.form:
            form = next((form for form in self.data.get("formas", []) if form.get("nome") == self.form), {})
            mult *= form.get("bonus", {}).get("dano", 1)
        return mult


class Battle:
    def __init__(self, players: list[Fighter], enemies: list[Fighter], mode: str = "solo"):
        self.players = players
        self.enemies = enemies
        self.mode = mode
        self.weather = random.choice([name for name in CLIMAS if name not in ("limpo", "lua_sangue")])
        self.weather_turns = 5
        self.terrain = "Campo comum"
        self.terrain_turns = 0
        self.terrain_creator: Fighter | None = None
        self.terrain_weather_override = False
        self.summon_count = 0
        self.round = 1
        self.log: list[str] = [f"A batalha começou sob {CLIMAS[self.weather]['nome']}!"]
        self.turn_order: list[Fighter] = []
        self.turn_index = 0
        self.winner: str | None = None
        self.damage_dealt: dict[str, int] = {}
        self.damage_received: dict[str, int] = {}
        self._summoned_this_battle = False
        self.inventory: dict[str, int] = {}
        self._last_prepared: tuple[int, int] | None = None
        self._sort_turns()
        all_fighters = players + enemies
        for fighter in all_fighters:
            table = RELIQUIAS_INIMIGO if fighter.kind in INIMIGOS else RELIQUIAS
            mods = table.get(fighter.relic, {}).get("mods", {})
            if mods.get("terreno_infernal"):
                self.weather = "sol"
                self.set_terrain("Terreno magmático")
        if any(f.relic == "amuleto da lua de sangue" for f in all_fighters):
            self.weather = "lua_sangue"
            self.weather_turns = 999

    @staticmethod
    def living(team: list[Fighter]) -> list[Fighter]:
        return [f for f in team if f.alive and f.hp > 0 and not f.fled]

    def _sort_turns(self) -> None:
        self.turn_order = sorted(self.living(self.players) + self.living(self.enemies), key=lambda f: f.speed, reverse=True)
        self.turn_index = 0
        self._last_prepared = None

    @property
    def current(self) -> Fighter | None:
        if self.winner:
            return None
        if not self.turn_order:
            self.finish_round()
        while self.turn_order and not self.winner:
            self.turn_index %= len(self.turn_order)
            key = (self.round, self.turn_index)
            actor = self.turn_order[self.turn_index]
            if self._last_prepared == key:
                return actor
            self._last_prepared = key
            actor.energy = min(actor.max_energy, actor.energy + 15)
            for effect in ("veneno", "queima", "sangramento"):
                if actor.effects.get(effect, 0):
                    damage = EFEITOS[effect]["dano"]
                    actor.hp = max(0, actor.hp - damage)
                    self.say(f"{actor.name} sofreu {damage} de dano por {EFEITOS[effect]['estado']}.")
                    self.damage_received[actor.name] = self.damage_received.get(actor.name, 0) + damage
                    if actor.hp == 0:
                        actor.alive = False
                        self.say(f"{actor.name} foi derrotado.")
            if not actor.alive:
                self._check_winner()
                self._advance()
                continue
            if actor.charging:
                actor.charging["remaining"] -= 1
                if actor.charging["remaining"] <= 0:
                    charge = actor.charging
                    actor.charging = None
                    self.say(f"{actor.name} liberou {charge['attack']} após carregar!")
                    self.attack(actor, charge["attack"], charge["target"], _release=True)
                else:
                    self.say(f"{actor.name} continua carregando {actor.charging['attack']}.")
                    self._advance()
                continue
            if self.weather == "ventania" and actor.side == "enemy" and actor.element != "ar":
                actor.effects["lento"] = max(1, actor.effects.get("lento", 0))
            blocked = any(actor.effects.get(effect, 0) for effect in ("paralisado", "congelado", "aprisionado"))
            slowed = "lento" in actor.effects and random.randint(1, 100) <= EFEITOS["lento"]["chance"]
            if blocked or slowed:
                reason = "paralisado/congelado" if blocked else "lento"
                self.say(f"{actor.name} perdeu o turno por estar {reason}.")
                self._advance()
                continue
            return actor
        return None

    def say(self, line: str) -> None:
        self.log.append(line)
        self.log = self.log[-120:]

    def _advance(self) -> None:
        if self.winner:
            return
        self.turn_index += 1
        self._last_prepared = None
        if self.turn_index >= len(self.turn_order):
            self.finish_round()

    def finish_round(self) -> None:
        for fighter in self.living(self.players) + self.living(self.enemies):
            fighter.defending = False
            self._apply_terrain_round(fighter)
            for effect in list(fighter.effects):
                fighter.effects[effect] -= 1
                if fighter.effects[effect] <= 0:
                    del fighter.effects[effect]
            for buff in list(fighter.buffs):
                fighter.buffs[buff] -= 1
                if fighter.buffs[buff] <= 0:
                    del fighter.buffs[buff]
                    self.say(f"O efeito {buff} de {fighter.name} acabou.")
        weather_cfg = CLIMAS.get(self.weather, {})
        for effect in weather_cfg.get("apaga", []):
            for fighter in self.living(self.players) + self.living(self.enemies):
                if fighter.effects.pop(effect, 0):
                    self.say(f"{weather_cfg['nome']} removeu {effect} de {fighter.name}.")
        if weather_cfg.get("raio"):
            targets = self.living(self.players) + self.living(self.enemies)
            if targets:
                target = random.choice(targets)
                target.hp = max(0, target.hp - int(weather_cfg["raio"]))
                self.say(f"Um raio atingiu {target.name} e causou {weather_cfg['raio']} de dano.")
                if target.hp == 0:
                    target.alive = False
        if self.weather_turns > 0:
            self.weather_turns -= 1
            if self.weather_turns == 0:
                self.weather = "limpo"
                self.say("O clima voltou ao normal.")
        if self.terrain_turns > 0:
            self.terrain_turns -= 1
            if self.terrain_turns == 0:
                self.terrain = "Campo comum"
                self.terrain_creator = None
                self.say("O terreno perdeu o efeito.")
        for fighter in self.living(self.players) + self.living(self.enemies):
            if fighter.max_hp_bonus_turns:
                fighter.max_hp_bonus_turns -= 1
                if fighter.max_hp_bonus_turns == 0:
                    fighter.max_hp = fighter.original_max_hp
                    fighter.hp = min(fighter.hp, fighter.max_hp)
                    fighter.data.pop("maximadora_mult", None)
                    self.say(f"O efeito maximador de {fighter.name} acabou.")
            fighter.elemental_marks.clear()
        self._check_winner()
        if not self.winner:
            self.round += 1
            self._sort_turns()

    def _apply_terrain_round(self, fighter: Fighter) -> None:
        terrain = self.terrain.casefold()
        if "planta" in terrain or "grass" in terrain:
            if fighter.element == "planta" or self.terrain_creator is fighter:
                heal = max(1, round(fighter.max_hp * 0.02))
                fighter.hp = min(fighter.max_hp, fighter.hp + heal)
                self.say(f"{fighter.name} recuperou {heal} de vida no terreno de planta.")
        elif "terreno elétrico" in terrain or "electric terrain" in terrain:
            if fighter.element == "raio":
                fighter.speed = round(fighter.data.get("velocidade", fighter.speed) * 1.12)
            elif fighter.element != "eletrico" and random.random() < .1:
                self.apply_effect(fighter, "paralisado", 1)
        elif "lama" in terrain or "mud" in terrain:
            if fighter.element != "terra":
                self.apply_effect(fighter, "lento", 1)
        elif "terreno de fogo" in terrain or "burn terrain" in terrain:
            if fighter.element != "fogo":
                self.apply_effect(fighter, "queima", 1)
        if "gas venenoso" in terrain:
            if fighter.element == "veneno":
                fighter.hp = min(fighter.max_hp, fighter.hp + max(1, round(fighter.max_hp * .04)))
            else:
                self.apply_effect(fighter, "veneno", 1)
        elif "gas inflamavel" in terrain:
            if fighter.element == "fogo":
                fighter.hp = min(fighter.max_hp, fighter.hp + max(1, round(fighter.max_hp * .04)))
            else:
                self.apply_effect(fighter, "queima", 1)
        elif "névoa" in terrain or "nevoa" in terrain:
            self.say(f"A névoa reduz a precisão de {fighter.name}.")
        elif "sombroso" in terrain or "assombrado" in terrain:
            if fighter.element not in ("sombra", "fantasma"):
                self.apply_effect(fighter, "medo", 1)
                self.apply_effect(fighter, "paralisado", 1)
        elif "rochoso" in terrain or "rocky" in terrain:
            if fighter.element not in ("rocha", "raio", "eletrico"):
                self.apply_effect(fighter, "lento", 1)
        elif "cemitério" in terrain or "cemiterio" in terrain:
            if fighter.kind != "necromante":
                damage = max(1, round(fighter.max_hp * 0.03))
                fighter.hp = max(0, fighter.hp - damage)
                self.say(f"O terreno assombrado drenou {damage} de vida de {fighter.name}.")
        elif "magmático" in terrain or "magmatico" in terrain:
            if fighter.element not in ("fogo", "rocha"):
                fighter.hp = max(0, fighter.hp - 8)
                self.apply_effect(fighter, "queima", 1)
                self.say(f"O terreno magmático causou 8 de dano em {fighter.name}.")

    def _check_winner(self) -> None:
        if not self.living(self.enemies):
            self.winner = "player" if self.living(self.players) else "escape"
        elif not self.living(self.players):
            self.winner = "escape" if self.players and all(f.fled for f in self.players) else "enemy"

    def _element_multiplier(self, defender: Fighter, element: str) -> float:
        profile = ELEMENTOS.get(defender.element, {})
        if element in profile.get("anula", []) or ("rochoso" in self.terrain.casefold() and element in ("raio", "eletrico")):
            return 0
        if element in profile.get("fraco_a", []):
            return 1.5
        if element in profile.get("resiste", []):
            return 0.5
        return 1

    def _weather_multiplier(self, element: str) -> float:
        return CLIMAS.get(self.weather, {}).get("elementos", {}).get(element, 1)

    def attack(self, actor: Fighter, attack_name: str, target: Fighter, _release: bool = False) -> None:
        attack = ATAQUES[attack_name]
        required = int(attack.get("requer", 0))
        if required and actor.attack_count < required:
            self.say(f"{attack_name} precisa de {required} ataques anteriores; progresso {actor.attack_count}.")
            return
        charge_turns = int(attack.get("carrega", 0) or (1 if actor.relic == "grande espada" and int(attack.get("dano", 0)) >= 35 else 0))
        if charge_turns and not _release:
            cost = int(attack.get("energia", 0))
            if actor.energy < cost:
                self.say(f"{actor.name} não tem energia suficiente para {attack_name}.")
                return
            actor.energy -= cost
            actor.charging = {"attack": attack_name, "target": target, "remaining": charge_turns}
            self.say(f"{actor.name} começou a carregar {attack_name}; dispara em {charge_turns} turno(s).")
            self._advance()
            return
        cost = int(attack.get("energia", 0))
        if actor.energy < cost and not _release:
            self.say(f"{actor.name} não tem energia suficiente para {attack_name}.")
            return
        if not _release:
            actor.energy -= cost
        actor.attack_count += 1
        if required:
            actor.attack_count = 0
        util = attack.get("util", {})
        if util:
            if "cura" in util:
                amount = int(util["cura"])
                actor.hp = min(actor.max_hp, actor.hp + amount)
                self.say(f"{actor.name} recuperou {amount} de vida com {attack_name}.")
            elif "protecao" in util:
                actor.shield += int(util["protecao"])
                self.say(f"{actor.name} criou uma barreira de {util['protecao']}.")
            elif "clima" in util:
                self.set_weather(util["clima"])
            elif "terreno" in util:
                self.set_terrain(util["terreno"])
            self._advance()
            return
        targets = (self.living(self.enemies if actor.side == "player" else self.players)
                   if attack.get("area") else [target])
        if actor.side == "player" and "fugir" in actor.restrictions:
            self.say(f"{actor.name} não pode atacar: o elixir da negação está em vigor.")
            return
        for defender in targets:
            if not defender.alive:
                continue
            evade = min(ESQUIVA["maximo"], defender.speed / ESQUIVA["divisor"])
            evade += defender.data.get("habilidade", {}).get("mods", {}).get("esquiva", 0)
            if defender.form:
                current_form = next((f for f in defender.data.get("formas", []) if f.get("nome") == defender.form), {})
                evade += current_form.get("bonus", {}).get("esquiva", 0)
                evade += current_form.get("habilidade", {}).get("mods", {}).get("esquiva", 0)
            if defender.effects.get("lento", 0):
                evade /= 2
            if self.weather == "neblina":
                evade += CLIMAS[self.weather].get("esquiva_bonus", 0)
            if "nevoa" in self.terrain.casefold():
                evade += 35
            if defender.kind == "atiradora" and "nevoa" in self.weather:
                evade += 35
            if random.random() * 100 < min(ESQUIVA["limite"], evade):
                self.say(f"{defender.name} esquivou do ataque de {actor.name}.")
                continue
            if actor.relic == "espada elemental":
                actor.element = {"chuva": "agua", "sol": "fogo", "neve": "gelo", "tempestade": "raio", "chuva_trovoada": "raio", "chuva_tempestade": "ar", "ventania": "ar"}.get(self.weather, actor.element)
            element = attack.get("elemento", actor.element)
            terrain_text = self.terrain.casefold()
            terrain_bonus = 1.1 if (("planta" in terrain_text and actor.element == "planta") or ("eletrico" in terrain_text and actor.element in ("raio", "eletrico")) or (("ground terrain" in terrain_text or "terreno comum" in terrain_text) and actor.element == "terra")) else 1
            base = float(attack.get("dano", 0)) * max(1, int(attack.get("golpes", 1))) * actor.damage_multiplier() * terrain_bonus
            dice = random.randint(0, 10)
            base *= 1 + dice / 10
            crit_chance = float(actor.data.get("critico", 5))
            crit_chance += actor.data.get("habilidade", {}).get("mods", {}).get("critico", 0)
            if actor.form:
                current_form = next((f for f in actor.data.get("formas", []) if f.get("nome") == actor.form), {})
                crit_chance += current_form.get("bonus", {}).get("critico", 0)
                crit_chance += current_form.get("habilidade", {}).get("mods", {}).get("critico", 0)
            if actor.contract and "critico" in CONTRATOS.get(actor.contract, {}).get("mods", {}):
                crit_chance += CONTRATOS[actor.contract]["mods"]["critico"]
            critical = random.random() < (crit_chance / 100)
            if critical:
                base *= 1.5
                self.say(f"Dado: {dice}/10 · crítico! Dano calculado com buffs: {round(base)}.")
            else:
                self.say(f"Dado: {dice}/10 · dano calculado com buffs: {round(base)}.")
            if self.weather == "nevoa":
                base *= .5
            damage = round(base * self._element_multiplier(defender, element) * self._weather_multiplier(element))
            actor_relics = RELIQUIAS_INIMIGO if actor.kind in INIMIGOS else RELIQUIAS
            actor_mods = actor_relics.get(actor.relic, {}).get("mods", {})
            if actor_mods.get("dano_espadas") and any(token in defender.kind for token in ("espad", "samurai", "cavaleiro negro")):
                damage = round(damage * actor_mods["dano_espadas"])
            damage = round(damage * defender.vulnerability.get(element, 1))
            defender_relics = RELIQUIAS_INIMIGO if defender.kind in INIMIGOS else RELIQUIAS
            defender_mods = defender_relics.get(defender.relic, {}).get("mods", {})
            damage = round(damage * (1 - defender_mods.get("reducao", 0)))
            damage = max(0, damage - int(defender.data.get("defesa", 0)) - int(defender_mods.get("defesa", 0)))
            if defender.defending:
                damage = round(damage * 0.5)
            absorbed = min(defender.shield, damage)
            defender.shield -= absorbed
            damage -= absorbed
            defender.hp = max(0, defender.hp - damage)
            if critical and defender.hp == 0 and defender.kind == "gojo":
                self.say(f"Pra que dar crítico no {defender.name} Arrogante!")
            self.damage_dealt[actor.name] = self.damage_dealt.get(actor.name, 0) + damage
            self.damage_received[defender.name] = self.damage_received.get(defender.name, 0) + damage
            self.say(f"{actor.name} usou {attack_name}: {defender.name} recebeu {round(damage)} de dano.")
            if element not in ("neutro", "none"):
                mark = {"sombra": "sombrio", "raio": "eletrico"}.get(element, element)
                defender.elemental_marks.add(mark)
                combos = {
                    frozenset(("agua", "gelo")): "agua + gelo", frozenset(("agua", "eletrico")): "agua + eletrico",
                    frozenset(("planta", "fogo")): "planta + fogo", frozenset(("gas", "fogo")): "gas + fogo",
                    frozenset(("gas", "veneno")): "gas + veneno", frozenset(("gas", "agua")): "gas + agua",
                    frozenset(("terra", "agua")): "terra + agua", frozenset(("gas", "eletrico")): "gas + eletrico",
                    frozenset(("fantasma", "sombrio")): "fantasma + sombrio", frozenset(("ar", "fogo")): "ar + fogo",
                    frozenset(("ar", "terra")): "ar + terra", frozenset(("ar", "gas", "veneno")): "ar + gas + veneno",
                    frozenset(("ar", "gas", "fogo")): "ar + gas + fogo", frozenset(("ar", "gas", "agua")): "ar + gas + agua",
                }
                combo = next((name for required_types, name in combos.items() if required_types.issubset(defender.elemental_marks)), None)
                if combo:
                    self.apply_combination(combo, [defender])
            vamp = 0
            if actor.relic != "nenhum":
                relic_table = RELIQUIAS_INIMIGO if actor.kind in INIMIGOS else RELIQUIAS
                vamp += relic_table.get(actor.relic, {}).get("mods", {}).get("vampirismo", 0)
            if actor.contract:
                vamp += CONTRATOS.get(actor.contract, {}).get("mods", {}).get("vampirismo", 0)
            if vamp and damage:
                healed = min(actor.max_hp - actor.hp, round(damage * vamp))
                actor.hp += healed
                self.say(f"{actor.name} recuperou {healed} de vida pelo dano causado.")
            if actor.relic == "amuleto do roubo":
                choices = list(ITENS)
                if choices:
                    stolen_name = random.choice(choices)
                    if self.inventory.get(stolen_name, 0) > 0:
                        self.inventory[stolen_name] -= 1
                    stolen = actor.data.setdefault("inventario", {})
                    stolen[stolen_name] = stolen.get(stolen_name, 0) + 1
                    self.say(f"{actor.name} roubou {stolen_name} de {defender.name}.")
            effect = attack.get("efeito")
            if effect and random.randint(1, 100) <= int(attack.get("chance", 100)):
                self.apply_effect(defender, effect, int(attack.get("duracao", 1)))
            if actor.buffs.get("aleatorio", 0):
                self.apply_effect(defender, random.choice(list(EFEITOS)), 2)
            on_hit = actor.data.get("habilidade", {}).get("mods", {}).get("on_hit", {})
            if on_hit and random.randint(1, 100) <= int(on_hit.get("chance", 100)):
                self.apply_effect(defender, on_hit["efeito"], int(on_hit.get("duracao", 1)))
            if actor.data.get("habilidade", {}).get("mods", {}).get("terreno_rocha"):
                self.set_terrain("Terreno rochoso", actor)
            if actor.kind == "copiador" and not actor.form:
                actor.form = "Cópia de " + defender.kind
                actor.data["ataques"] = defender.available_attacks()[:4]
                actor.data["habilidade"] = deepcopy(defender.data.get("habilidade"))
                actor.data["formas"] = deepcopy(defender.data.get("formas", []))
                actor.max_hp = defender.max_hp
                actor.original_max_hp = defender.max_hp
                actor.hp = min(actor.hp, actor.max_hp)
                actor.max_energy = defender.max_energy
                actor.energy = min(actor.energy, actor.max_energy)
                actor.speed = defender.speed
                actor.element = defender.element
                actor.data["defesa"] = defender.data.get("defesa", 0)
                self.say(f"{actor.name} copiou {defender.name}!")
            if defender.hp <= 0:
                defender.alive = False
                self.say(f"{defender.name} foi derrotado.")
        self._check_winner()
        self._advance()

    def apply_effect(self, target: Fighter, effect: str, duration: int = 2) -> None:
        if effect not in EFEITOS:
            return
        mods = target.data.get("habilidade", {}).get("mods", {})
        table = RELIQUIAS_INIMIGO if target.kind in INIMIGOS else RELIQUIAS
        relic_mods = table.get(target.relic, {}).get("mods", {})
        resistance = mods.get("resist_status", 0) + relic_mods.get("resist_status", 0)
        if resistance and random.randint(1, 100) <= resistance:
            self.say(f"{target.name} resistiu ao efeito {EFEITOS[effect]['estado']}.")
            return
        target.effects[effect] = max(duration, target.effects.get(effect, 0))
        self.say(f"{target.name} recebeu {EFEITOS[effect]['estado']} por {duration} turno(s).")

    def defend(self, actor: Fighter) -> None:
        if "defender" in actor.restrictions:
            self.say(f"{actor.name} não pode defender por causa de sua relíquia/efeito.")
            return
        actor.defending = True
        self.say(f"{actor.name} assumiu posição defensiva.")
        self._advance()

    def use_item(self, actor: Fighter, item_name: str, target: Fighter, inventory: dict[str, int]) -> None:
        if inventory.get(item_name, 0) <= 0:
            self.say(f"{item_name}: sem unidades disponíveis.")
            return
        item = ITENS[item_name]
        kind = item.get("tipo")
        if kind == "negacao":
            if actor.elixir_used or actor.hp / max(1, actor.max_hp) >= .2:
                self.say("O elixir da negação só funciona uma vez, abaixo de 20% da vida.")
                return
            inventory[item_name] -= 1
            actor.hp = 1
            actor.elixir_used = True
            actor.restrictions.update({"defender", "contrato", "cura", "transformar", "fugir", "arremessavel"})
            self.say(f"{actor.name} negou a morte e permaneceu com 1 HP.")
            self._advance()
            return
        if kind == "vulnerabilidade":
            inventory[item_name] -= 1
            for element in item["elementos"]:
                target.vulnerability[element] = 1.25
            self.say(f"{target.name} ficou vulnerável: {', '.join(item['elementos'])}.")
            if item_name == "cruz sagrada" and actor.element == "luz" or item_name == "correntes sombrias" and actor.element in ("sombra", "fantasma"):
                actor.data["dano_global_mult"] = actor.data.get("dano_global_mult", 1) * 1.025
                actor.speed = round(actor.speed * 1.025)
                actor.data["defesa"] = round(actor.data.get("defesa", 0) * 1.025)
                actor.max_energy = round(actor.max_energy * 1.025)
                self.say(f"{actor.name} recebeu +2,5% nos atributos contra seu elemento oposto.")
            self._advance()
            return
        inventory[item_name] -= 1
        if kind == "cura":
            if "cura" in actor.restrictions:
                inventory[item_name] += 1
                self.say("O elixir da negação impede o uso de cura.")
                return
            value = int(item.get("cura", 0))
            target.hp = min(target.max_hp, target.hp + value)
            self.say(f"{actor.name} usou {item_name}; {target.name} recuperou {value} de vida.")
        elif kind == "energia":
            value = int(item.get("energia", 0))
            target.energy = min(target.max_energy, target.energy + value)
            self.say(f"{target.name} recuperou {value} de energia.")
        elif kind == "antidoto":
            target.effects.clear()
            self.say(f"Efeitos removidos de {target.name}.")
        elif kind == "climatica":
            bomb = CLIMAS.get(self.weather, CLIMAS["limpo"]).get("bomba", {"dano": 20})
            value = round(int(bomb.get("dano", 20)) * self._element_multiplier(target, bomb.get("elemento", "neutro")))
            target.hp = max(0, target.hp - value)
            self.say(f"A bomba climática causou {value} de dano sob {CLIMAS[self.weather]['nome']}.")
            if bomb.get("efeito"):
                self.apply_effect(target, bomb["efeito"], int(bomb.get("duracao", 1)))
        elif kind == "fumaca":
            if random.randint(0, 10) >= 5:
                actor.fled = True
                self.say(f"{actor.name} fugiu usando bomba de fumaça.")
            else:
                self.say("A bomba de fumaça foi gasta, mas a fuga falhou.")
        elif kind == "forca":
            target.buffs["forca"] = int(item.get("duracao", 3))
            self.say(f"{target.name} recebeu +25% de dano por {target.buffs['forca']} turnos.")
        elif kind == "aleatorio":
            target.buffs["aleatorio"] = int(item.get("duracao", 3))
            self.say(f"{target.name} aplicará efeitos aleatórios por {target.buffs['aleatorio']} turnos.")
        elif kind == "velocidade":
            target.speed += int(item.get("velocidade", 0))
            self.say(f"A velocidade de {target.name} aumentou em {item['velocidade']}.")
        elif kind in ("bomba", "pedra"):
            if "arremessavel" in actor.restrictions:
                inventory[item_name] += 1
                self.say("O elixir da negação impede consumíveis arremessáveis.")
                return
            enemies = self.living(self.enemies if actor.side == "player" else self.players)
            targets = enemies if item.get("area") else [target]
            for defender in targets:
                if item_name == "bomba fragmentada" and defender.element == "fantasma":
                    self.say(f"{defender.name} é imune à bomba fragmentada.")
                    continue
                value = int(item.get("dano", 0))
                value = round(value * self._element_multiplier(defender, item.get("elemento", actor.element)))
                defender.hp = max(0, defender.hp - value)
                if defender.hp == 0:
                    defender.alive = False
                self.say(f"{defender.name} recebeu {value} de dano de {item_name}.")
                if item.get("aplica"):
                    self.apply_effect(defender, item["aplica"], int(item.get("duracao", 1)))
                if item.get("elemento") == "gas":
                    defender.vulnerability.update({"fogo": 1.5, "raio": 1.5, "eletrico": 1.5, "planta": 1.5})
                    self.say(f"{defender.name} ficou vulnerável a combinações elementais.")
        elif kind == "tipagem":
            target.element = {"chuva": "agua", "sol": "fogo", "neve": "gelo", "tempestade": "raio", "chuva_trovoada": "raio", "chuva_tempestade": "ar", "ventania": "ar"}.get(self.weather, "neutro")
            self.say(f"{target.name} agora é do tipo {target.element} pelo clima.")
        elif kind == "maximizadora":
            if "cura" in actor.restrictions:
                inventory[item_name] += 1
                self.say("O pingente da rejeição impede poções de cura.")
                return
            if target.max_hp_bonus_turns:
                inventory[item_name] += 1
                self.say("A poção maximadora já está ativa.")
                return
            old_max = target.max_hp
            target.max_hp = round(old_max * 1.5)
            target.hp = min(target.max_hp, target.hp + target.max_hp - old_max)
            target.max_hp_bonus_turns = int(item.get("duracao", 3))
            target.data["maximadora_mult"] = 1.5
            self.say(f"A vida máxima de {target.name} aumentou por {target.max_hp_bonus_turns} turnos.")
        else:
            self.say(f"{item_name} ainda não tem efeito implementado na versão Pygame.")
        self._check_winner()
        self._advance()

    def transform(self, actor: Fighter) -> None:
        if "transformar" in actor.restrictions:
            self.say("O elixir da negação impede a transformação.")
            return
        if actor.contract:
            self.say("Quem fez um contrato não pode usar mega forma.")
            return
        forms = actor.data.get("formas", [])
        if not forms:
            self.say(f"{actor.name} não possui transformação.")
            return
        form = forms[0]
        actor.form = form.get("nome")
        actor.energy = max(0, actor.energy - 40)
        if form.get("elemento"):
            actor.element = form["elemento"]
        self.say(f"{actor.name} se transformou em {actor.form}!")
        self._advance()

    def sign_contract(self, actor: Fighter, name: str) -> None:
        if name not in CONTRATOS:
            self.say("Contrato inválido.")
            return
        if "contrato" in actor.restrictions:
            self.say("O elixir da negação impede contratos.")
            return
        if actor.contract:
            self.say("Este combatente já assinou um contrato.")
            return
        if actor.form:
            self.say("Quem se transformou não pode assinar um contrato.")
            return
        actor.contract = name
        self.say(f"{actor.name} assinou {name}.")
        self._advance()

    def rest(self, actor: Fighter) -> None:
        actor.energy = min(actor.max_energy, actor.energy + 30)
        actor.hp = min(actor.max_hp, actor.hp + round(actor.max_hp * 0.05))
        self.say(f"{actor.name} descansou e recuperou recursos.")
        self._advance()

    def quit_battle(self, actor: Fighter) -> None:
        self.winner = "quit"
        self.say(f"{actor.name} encerrou a batalha.")

    def summon(self, summoner: Fighter, name: str) -> None:
        if self._summoned_this_battle:
            self.say("O limite de uma invocação em campo já foi atingido.")
            return
        templates = {
            "morcego azul": ("sombra", 32, 4, 55, 25, ["morcego_mordida"]),
            "morcego rosa": ("sombra", 28, 3, 65, 25, ["mordida venenosa"]),
            "lobo alfa": ("neutro", 75, 12, 95, 45, ["mordida feroz"]),
            "espírito de fogo": ("fogo", 58, 8, 70, 45, ["lâmina flamejante"]),
        }
        element, hp, defense, speed, energy, attacks = templates[name]
        team = self.enemies if summoner.side in ("enemy", "rival") else self.players
        ally = Fighter.create(name.title(), summoner.side, "invocável", {
            "vida": hp, "defesa": defense, "velocidade": speed, "energia": energy,
            "elemento": element, "ataques": attacks, "critico": 4,
        })
        ally.summon = True
        team.append(ally)
        self._summoned_this_battle = True
        self.say(f"{summoner.name} invocou {ally.name}!")

    def flee(self, actor: Fighter) -> None:
        if "fugir" in actor.restrictions:
            self.say(f"{actor.name} não pode fugir por causa de um efeito ativo.")
            return
        opposing_speed = max((f.speed for f in self.living(self.enemies if actor.side == "player" else self.players)), default=0)
        condition_penalty = sum(25 for effect in ("lento", "aprisionado", "medo", "paralisado") if actor.effects.get(effect, 0))
        hp_penalty = round((1 - actor.hp / max(1, actor.max_hp)) * 45)
        chance = 100 if actor.speed > opposing_speed else max(0, min(95, 45 + (actor.speed - opposing_speed) // 3 - condition_penalty - hp_penalty))
        if random.randint(1, 100) <= chance:
            actor.fled = True
            self.say(f"{actor.name} conseguiu fugir.")
        else:
            self.say(f"{actor.name} tentou fugir, mas não conseguiu.")
        self._check_winner()
        self._advance()

    def set_weather(self, weather: str) -> None:
        if self.weather == "chuva" and weather == "tempestade":
            weather = "chuva_tempestade"
        elif self.weather == "chuva" and weather == "trovoada":
            weather = "chuva_trovoada"
        if weather not in CLIMAS:
            return
        self.weather, self.weather_turns = weather, 5
        if weather == "lua_sangue":
            self.weather_turns = 999
        self.say(f"O clima mudou para {CLIMAS[weather]['nome']}.")

    def set_terrain(self, terrain: str, creator: Fighter | None = None) -> None:
        self.terrain, self.terrain_turns = terrain, 5
        self.terrain_creator = creator
        self.say(f"Terreno ativo: {terrain} (5 rodadas).")

    def apply_combination(self, combination: str, targets: list[Fighter] | None = None) -> None:
        key = combination.casefold().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
        combinations = {
            "agua + gelo": ("congelado", None), "agua + eletrico": ("paralisado", None),
            "planta + fogo": ("queima", None), "gas + fogo": ("queima", None),
            "gas + veneno": ("veneno", None), "gas + agua": (None, "Terreno de névoa"),
            "terra + agua": ("afundado", "Terreno de lama"), "gas + eletrico": ("queima", None),
            "fantasma + sombrio": ("medo", None), "ar + fogo": ("queima", None),
            "ar + terra": (None, "Tempestade de terra"),
            "ar + gas + veneno": (None, "Terreno de gás venenoso"),
            "ar + gas + fogo": (None, "Terreno de gás inflamável"),
            "ar + gas + agua": (None, "Terreno de névoa"),
        }
        effect, terrain = combinations.get(key, (None, None))
        weather_combos = {"chuva + tempestade": "chuva_tempestade", "chuva + trovoada": "chuva_trovoada"}
        if key in weather_combos:
            self.set_weather(weather_combos[key])
            return
        if terrain:
            self.set_terrain(terrain)
        if effect:
            for target in targets or self.living(self.enemies):
                self.apply_effect(target, effect, 2)
        if not terrain and not effect:
            self.say(f"Combinação desconhecida: {combination}.")

    def ai_action(self, actor: Fighter) -> None:
        foes = self.living(self.players if actor.side == "enemy" else self.enemies)
        if not foes:
            self._check_winner()
            return
        target = min(foes, key=lambda f: f.hp / max(1, f.max_hp))
        stolen = actor.data.get("inventario", {})
        available_stolen = [name for name, count in stolen.items() if count > 0]
        if available_stolen:
            item_name = random.choice(available_stolen)
            item_type = ITENS[item_name].get("tipo")
            ally_types = {"cura", "energia", "antidoto", "ressusitador", "forca", "aleatorio", "velocidade", "tipagem", "maximizadora"}
            recipient = actor if item_type in ally_types else target
            self.use_item(actor, item_name, recipient, stolen)
            return
        if actor.kind in {"king kobra", "mestre mago", "necromante", "cavaleiro negro conquistador"} and not self._summoned_this_battle and random.random() < .12:
            self.summon(actor, random.choice(["morcego azul", "morcego rosa", "lobo alfa", "espírito de fogo"]))
            self._advance()
            return
        for attack_name in actor.available_attacks():
            attack = ATAQUES[attack_name]
            if attack.get("dano", 0) > 0 and actor.energy >= attack.get("energia", 0):
                self.attack(actor, attack_name, target)
                return
        self.rest(actor)


def make_enemy(name: str) -> Fighter:
    from batalha import INIMIGOS
    data = INIMIGOS[name]
    relic = random.choice(list(RELIQUIAS_INIMIGO)) if random.random() < CHANCE_RELIQUIA_INIMIGO / 100 else "nenhum"
    return Fighter.create(name.title(), "enemy", name, data, relic)


def make_player(name: str, class_name: str, relic: str = "nenhum") -> Fighter:
    return Fighter.create(name, "player", class_name, CLASSES[class_name], relic)
