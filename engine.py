"""Regras de combate independentes da interface Pygame."""
from __future__ import annotations

from dataclasses import dataclass, field
import random
from copy import deepcopy
from typing import Any

from batalha import (ATAQUES, CHANCE_RELIQUIA_INIMIGO, CLASSES, CLIMAS, CONTRATOS, CONTRATOS_PERSONAGEM,
                     DIFICULDADES, DOMINIOS, EFEITOS, ELEMENTOS, ESCUDO, ESQUIVA, FORMAS, INIMIGOS, ITENS, RELIQUIAS,
                     RELIQUIAS_INIMIGO)


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
    turns_taken: int = 0
    bravery_streak: int = 0
    last_attack: str | None = None
    repeated_attack_bonus: int = 0
    guaranteed_next_critical: bool = False
    forced_target: "Fighter | None" = None
    domain_pending: int = 0
    domain_turns: int = 0
    domain_name: str | None = None
    domain_used: bool = False
    worm_turns: int = 0
    crystal_broken: bool = False
    revive_used: bool = False
    action_disabled_turns: int = 0
    contract_turns: int = 0
    contract_used: bool = False
    base_element: str = "neutro"
    form_turns: int = 0
    form_started_at_turn: int = 0
    transform_used: bool = False
    max_shield: int = 0
    shield_recharge: int = 0
    substitute_turns: int = 0
    substitute_used: bool = False

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
        fighter.max_shield = shield
        fighter.base_element = fighter.element
        if mods.get("elemento"):
            fighter.element = fighter.base_element = mods["elemento"]
        if relic == "pingente da rejeição":
            fighter.restrictions.update({"fugir", "cura", "arremessavel"})
            fighter.shield = 0
            fighter.max_shield = 0
        if relic == "wonder-guard":
            fighter.max_hp = fighter.hp = 1
            fighter.original_max_hp = 1
        if relic == "amuleto da lua de sangue":
            fighter.data["dano_global_mult"] = 1.2
            fighter.data["defesa"] = round(fighter.data.get("defesa", 0) * 1.2)
            fighter.data["critico"] = round(fighter.data.get("critico", 0) * 1.2)
        if relic == "máscara de esqueleto":
            fighter.data["ataques"] = ["olhos especiais", "corte dimensional", "queimar", "corte flamejante"]
            fighter.data["formas"] = [
                {"letra": "X", "nome": "Hollow das chamas", "elemento": "fogo", "ataques": ["corte flamejante"]},
                {"letra": "Y", "nome": "King hollow", "elemento": "sombra", "bonus": {"dano": 1.2}, "ataques": ["corte dimensional"]},
                {"letra": "Z", "nome": "Hollow chifrudo", "elemento": "fogo", "bonus": {"critico": 25}, "ataques": ["queimar"]},
            ]
            fighter.data["contratos"] = ["contrato das chamas hollow"]
            fighter.restrictions.update({"itens_normais", "contratos_normais"})
        if relic == "colar de ouro da lua protetora":
            fighter.data["reducao_lua_azul"] = 0.9
        if mods.get("tipagem_climatica"):
            fighter.data["tipagem_climatica"] = True
        if mods.get("lua_azul"):
            fighter.data["reducao_lua_azul"] = 0.9
        if relic == "corrente do sofrimento":
            fighter.effects["sangramento"] = 999
            fighter.data["contratos"] = ["sofrimento contínuo"]
        fighter.restrictions.update(relic_data.get("restringe", []))
        if mods.get("substituto"):
            fighter.data["substituto"] = True
        return fighter

    @property
    def is_player(self) -> bool:
        return self.side == "player"

    def available_attacks(self) -> list[str]:
        if self.relic == "máscara de esqueleto":
            names = ["olhos especiais", "corte dimensional", "queimar", "corte flamejante"]
            if self.form:
                form = next((f for f in self.data.get("formas", []) if f.get("nome") == self.form), {})
                names += form.get("ataques", [])
            return list(dict.fromkeys(name for name in names if name in ATAQUES))
        names = list(self.data.get("ataques", []))
        if self.form:
            form = next((f for f in self.data.get("formas", []) if f.get("nome") == self.form), {})
            names += form.get("ataques", [])
        return list(dict.fromkeys(name for name in names if name in ATAQUES))

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
        mult *= self.data.get("bravura_dano", 1)
        if self.domain_turns > 0:
            mult *= 1.2
        if self.relic == "vaso ganancioso":
            mult *= 1 + .1 * int(self.data.get("vaso_acertos", 0))
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
        # O cronômetro é configurado pela preparação e só conta no turno de jogador.
        self.turn_time_limit = 60
        self.weather = random.choice([name for name in CLIMAS if name not in ("limpo", "lua_sangue", "lua_azul")])
        self.weather_turns = 5
        self.weather_locked = False
        self.weather_source: str | None = None
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
                self.set_terrain("Terreno magmático")
        if any(f.relic in ("amuleto da lua de sangue", "olho vermelho escuro") for f in all_fighters):
            self.set_weather("lua_sangue", from_item=True)
        elif any(f.relic in ("colar de ouro da lua protetora", "amuleto cúbico") for f in all_fighters):
            self.set_weather("lua_azul", from_item=True)
            if any(f.relic == "amuleto cúbico" for f in all_fighters):
                self.set_terrain("Terreno Synthwave Azul")
        elif any((RELIQUIAS_INIMIGO if f.kind in INIMIGOS else RELIQUIAS)
                 .get(f.relic, {}).get("mods", {}).get("terreno_infernal") for f in all_fighters):
            self.set_weather("sol", from_item=True)
        for carrier in all_fighters:
            if carrier.relic != "corrente de ligação":
                continue
            opponents = self.living(self.enemies if carrier.side in ("player", "rival") else self.players)
            if not opponents:
                continue
            linked = random.choice(opponents)
            for current_attr, max_attr in (("hp", "max_hp"), ("energy", "max_energy"), ("shield", "max_shield")):
                shared_max = round((getattr(carrier, max_attr) + getattr(linked, max_attr)) / 2)
                shared_current = min(shared_max, round((getattr(carrier, current_attr) + getattr(linked, current_attr)) / 2))
                setattr(carrier, max_attr, shared_max)
                setattr(linked, max_attr, shared_max)
                setattr(carrier, current_attr, shared_current)
                setattr(linked, current_attr, shared_current)
            self.say(f"A corrente ligou {carrier.name} a {linked.name}; vida, escudo e energia máximos foram igualados pela média.")

    @staticmethod
    def living(team: list[Fighter]) -> list[Fighter]:
        return [f for f in team if f.alive and f.hp > 0 and not f.fled]

    def _sort_turns(self) -> None:
        def initiative(fighter: Fighter):
            attack_priority = max((int(ATAQUES[name].get("prioridade", 0)) for name in fighter.available_attacks()), default=0)
            bonus = fighter.data.get("habilidade", {}).get("mods", {}).get("prioridade_suporte", 0)
            return (fighter.speed + 100 * max(attack_priority, bonus), fighter.speed)
        self.turn_order = sorted(self.living(self.players) + self.living(self.enemies), key=initiative, reverse=True)
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
            actor.turns_taken += 1
            if actor.relic == "corrente do sofrimento":
                actor.effects["sangramento"] = 999
            if actor.substitute_turns > 0:
                actor.substitute_turns -= 1
                if actor.substitute_turns == 0:
                    self.say(f"O boneco substituto de {actor.name} desapareceu.")
            if actor.relic == "porquinho estourável" and actor.turns_taken % 3 == 0:
                for target in self.living(self.players) + self.living(self.enemies):
                    target.hp = max(0, target.hp - 10)
                    self.damage_received[target.name] = self.damage_received.get(target.name, 0) + 10
                    self.say(f"O porquinho estourável causou 10 de dano em {target.name}.")
                    if target.hp <= 0:
                        self._defeat(target, actor, 10)
                self._check_winner()
                if self.winner:
                    return None
            if actor.side in ("player", "rival") and actor.max_shield > 0:
                if actor.shield_recharge > 0:
                    actor.shield_recharge -= 1
                    if actor.shield_recharge == 0:
                        actor.shield = max(1, round(actor.max_shield * ESCUDO["vida_ao_voltar"]))
                        self.say(f"O escudo de {actor.name} recarregou com {actor.shield}/{actor.max_shield} de proteção.")
                elif actor.shield < actor.max_shield:
                    actor.shield = min(actor.max_shield, actor.shield + ESCUDO["regeneracao"])
            if actor.form and actor.form_turns > 0 and actor.turns_taken > actor.form_started_at_turn:
                actor.form_turns -= 1
                if actor.form_turns <= 0:
                    expired_form = actor.form
                    actor.form = None
                    actor.element = actor.base_element
                    self.say(f"A transformação {expired_form} de {actor.name} terminou; ele voltou à forma normal.")
            if actor.domain_pending:
                actor.domain_pending -= 1
                if actor.domain_pending == 0:
                    self._activate_domain(actor)
            actor.energy = min(actor.max_energy, actor.energy + 15)
            for effect in ("veneno", "queima", "sangramento"):
                if actor.effects.get(effect, 0):
                    damage = EFEITOS[effect]["dano"]
                    actor.hp = max(0, actor.hp - damage)
                    self.say(f"{actor.name} sofreu {damage} de dano por {EFEITOS[effect]['estado']}.")
                    self.damage_received[actor.name] = self.damage_received.get(actor.name, 0) + damage
                    if actor.hp == 0:
                        self._defeat(actor)
                if effect == "queima" and actor.relic in {"fruto de fogo", "fruto elétrico", "fruto gelado"} and actor.alive:
                    heal = min(actor.max_hp - actor.hp, EFEITOS[effect]["dano"])
                    actor.hp += heal
                    self.say(f"{actor.name} usou o fruto e recuperou {heal} de vida durante a queimadura.")
            if actor.effects.get("engasgado", 0) and actor.alive:
                burn = max(1, int(EFEITOS["engasgado"].get("dano", 4)))
                actor.hp = max(0, actor.hp - burn)
                self.say(f"{actor.name} sofreu {burn} de dano por estar engasgado.")
                if actor.hp == 0:
                    self._defeat(actor)
            if not actor.alive:
                self._check_winner()
                self._advance()
                continue
            if actor.action_disabled_turns:
                actor.action_disabled_turns -= 1
                self.say(f"{actor.name} está incapacitado e perde este turno.")
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
            slowed = any(actor.effects.get(name, 0) for name in ("lento", "engasgado")) and random.randint(1, 100) <= EFEITOS["lento"]["chance"]
            if blocked or slowed:
                reason = "paralisado/congelado" if blocked else "lento"
                self.say(f"{actor.name} perdeu o turno por estar {reason}.")
                self._advance()
                continue
            return actor
        return None

    def say(self, line: str) -> None:
        self.log.append(line)

    def _activate_domain(self, actor: Fighter) -> None:
        form_data = next((f for f in actor.data.get("formas", []) if f.get("nome") == actor.form), {})
        domain = form_data.get("dominio") or actor.data.get("dominio") or DOMINIOS.get(actor.kind, {}).get("normal")
        if not domain:
            domain = f"Domínio de {actor.element}"
        foes = self.living(self.enemies if actor.side == "player" else self.players)
        clash_owners = [f for f in foes if f.domain_turns > 0]
        if clash_owners:
            if random.random() < .5:
                for owner in clash_owners:
                    owner.domain_turns = 0
                    owner.domain_name = None
                self.say(f"{actor.name} venceu a disputa de expansões; {domain} prevaleceu!")
            else:
                winner = random.choice(clash_owners)
                for owner in clash_owners:
                    owner.domain_turns = 0
                    owner.domain_name = None
                winner.domain_turns = 4
                winner.domain_name = winner.data.get("dominio") or DOMINIOS.get(winner.kind, {}).get("normal") or f"Domínio de {winner.element}"
                self.say(f"{winner.name} venceu a disputa de expansões; {winner.domain_name} prevaleceu!")
                return
        actor.domain_name = domain
        actor.domain_turns = 4
        self.say(f"A expansão {domain} foi ativada e fortalece {actor.name} por 3 rodadas.")

    def _record_action(self, actor: Fighter, action: str) -> None:
        if actor.kind != "boxeador":
            return
        if action in {"defender", "item", "flee"}:
            actor.bravery_streak = 0
            if actor.data.pop("prova_bravura_ativa", False):
                actor.data.pop("bravura_dano", None)
                self.say("A Prova de Bravura foi interrompida.")
            return
        if action == "transform" and actor.bravery_streak < 5:
            return
        actor.bravery_streak += 1
        if actor.bravery_streak == 5:
            actor.data["prova_bravura_ativa"] = True
            actor.data["bravura_dano"] = 1.25
            self.say(f"{actor.name} completou 5 turnos de bravura: dano +25% e megaforma liberada!")
        if actor.bravery_streak == 10:
            self.say(f"{actor.name} provou sua bravura por 10 turnos e liberou seu contrato exclusivo.")

    @staticmethod
    def contract_options(actor: Fighter) -> list[str]:
        if actor.relic == "máscara de esqueleto":
            return ["contrato das chamas hollow"]
        if actor.kind == "boxeador":
            return ["contrato das correntes igualitárias de fogo"] if actor.bravery_streak >= 10 else []
        return list(actor.data.get("contratos") or CONTRATOS_PERSONAGEM.get(actor.kind, list(CONTRATOS)))

    def _restore_worm(self, fighter: Fighter) -> None:
        snapshot = fighter.data.pop("worm_snapshot", None)
        if not snapshot:
            return
        fighter.kind = snapshot["kind"]
        fighter.data = snapshot["data"]
        fighter.max_hp, fighter.hp = snapshot["max_hp"], max(1, snapshot["hp"])
        fighter.max_energy, fighter.energy = snapshot["max_energy"], snapshot["energy"]
        fighter.shield, fighter.speed, fighter.element = snapshot["shield"], snapshot["speed"], snapshot["element"]
        fighter.worm_turns = 0
        fighter.alive = True
        self.say(f"{fighter.name} voltou à forma original.")

    def _defeat(self, fighter: Fighter, attacker: Fighter | None = None, damage: int = 0) -> bool:
        """Resolve relíquias de sobrevivência; retorna True se a queda foi evitada."""
        mods = RELIQUIAS_INIMIGO.get(fighter.relic, {}).get("mods", {})
        if fighter.worm_turns:
            fighter.hp = 1
            fighter.data["worm_damage_received"] = fighter.data.get("worm_damage_received", 0) + damage
            if fighter.data["worm_damage_received"] >= 100:
                self._restore_worm(fighter)
            return True
        if (mods.get("reviver_cristal") or mods.get("reviver")) and not fighter.revive_used:
            fighter.revive_used = True
            if random.randint(1, 100) <= int(mods.get("reviver_cristal", 100)):
                fighter.hp = max(1, round(fighter.max_hp * float(mods.get("vida_retorno", 1))))
                fighter.alive = True
                fighter.relic = "nenhum"
                fighter.crystal_broken = True
                self.say(f"O coração de cristal de {fighter.name} quebrou e o reviveu com vida completa!")
                return True
        if (mods.get("verme_sacrificio") and not fighter.data.get("worm_used") and not fighter.form
                and not fighter.contract and not fighter.data.get("healed_in_battle")
                and not fighter.data.get("formed_in_battle") and not fighter.data.get("contracted_in_battle")):
            fighter.data["worm_used"] = True
            fighter.data["worm_snapshot"] = {"kind": fighter.kind, "data": deepcopy(fighter.data), "max_hp": fighter.max_hp,
                "hp": max(1, round(fighter.max_hp * .3)), "max_energy": fighter.max_energy, "energy": fighter.energy,
                "shield": fighter.shield, "speed": fighter.speed, "element": fighter.element}
            fighter.kind = "verme sacrificial"
            fighter.data = {"ataques": ["bater"], "vida": 1, "defesa": 0, "velocidade": 1200, "escudo": 100, "energia": 0}
            fighter.max_hp = fighter.hp = 1
            fighter.max_energy = fighter.energy = 0
            fighter.shield, fighter.speed, fighter.worm_turns = 100, 1200, 6
            fighter.alive = True
            self.say(f"{fighter.name} virou um Verme Sacrificial: 1 HP, 100 de escudo e 5 rodadas de proteção!")
            return True
        fighter.hp = 0
        fighter.alive = False
        self.say(f"{fighter.name} foi derrotado.")
        return False

    def _use_attack_utility(self, actor: Fighter, target: Fighter, util: dict[str, Any], attack_name: str) -> None:
        own_team = self.players if actor.side == "player" else self.enemies
        opposing_team = self.enemies if actor.side == "player" else self.players
        recipients = [actor]
        if util.get("equipe"):
            recipients = self.living(own_team)
        elif util.get("alvos"):
            recipients = [target, *[f for f in self.living(own_team) if f is not target]][:int(util["alvos"])]
        if "cura" in util:
            for recipient in recipients:
                healed = min(recipient.max_hp - recipient.hp, int(util["cura"]))
                recipient.hp += healed
                self.say(f"{recipient.name} recuperou {healed} de vida.")
        if "energia" in util:
            target.energy = min(target.max_energy, target.energy + int(util["energia"]))
            self.say(f"{target.name} recuperou energia.")
        if "protecao" in util:
            for recipient in recipients:
                recipient.shield += int(util["protecao"])
                self.say(f"{recipient.name} recebeu barreira de {util['protecao']}.")
        if "imunidade" in util:
            actor.buffs["imunidade"] = max(actor.buffs.get("imunidade", 0), int(util["imunidade"]))
            self.say(f"{actor.name} se protegeu contra dano e efeitos por {actor.buffs['imunidade']} turnos.")
        if "buff" in util:
            for recipient in recipients:
                buff = util["buff"]
                recipient.buffs[buff] = max(recipient.buffs.get(buff, 0), int(util.get("duracao", 2)))
                if buff == "velocidade":
                    previous_bonus = int(recipient.data.get("velocidade_buff", 0))
                    recipient.data["velocidade_buff"] = int(util.get("valor", 25))
                    recipient.speed += recipient.data["velocidade_buff"] - previous_bonus
                self.say(f"{recipient.name} recebeu bônus de {buff} por {util.get('duracao', 2)} turnos.")
        if "defesa" in util:
            for recipient in recipients:
                recipient.buffs["defesa"] = max(recipient.buffs.get("defesa", 0), int(util.get("duracao", 2)))
                recipient.data["defesa_buff"] = int(util["defesa"])
                self.say(f"{recipient.name} recebeu +{util['defesa']} de defesa por {util.get('duracao', 2)} turnos.")
        if "critico" in util:
            actor.buffs["critico"] = max(actor.buffs.get("critico", 0), int(util.get("duracao", 2)))
            actor.data["critico_buff"] = int(util["critico"])
        if "provocar" in util:
            for foe in self.living(opposing_team):
                foe.forced_target = actor
                foe.buffs["provocado"] = int(util["provocar"])
            self.say(f"Os inimigos foram atraídos para atacar {actor.name}.")
        if "sacrificio" in util:
            if self.mode not in ("dupla", "bots"):
                self.say("Sacrifício só pode ser usado no modo Dupla ou Grupo vs bots.")
                return
            if target is actor:
                self.say("Escolha outro combatente para o sacrifício.")
                return
            target.hp = 0
            survived = self._defeat(target, actor)
            if survived:
                self.say("O alvo sobreviveu ao sacrifício; os atributos não foram aumentados.")
                return
            actor.max_hp = max(actor.max_hp, round(actor.max_hp * 1.25))
            actor.hp = min(actor.max_hp, round(actor.hp * 1.25))
            actor.max_energy = round(actor.max_energy * 1.25)
            actor.energy = min(actor.max_energy, round(actor.energy * 1.25))
            actor.shield = round(actor.shield * 1.25)
            actor.speed = round(actor.speed * 1.25)
            actor.data["defesa"] = round(actor.data.get("defesa", 0) * 1.25)
            self.say(f"{target.name} foi sacrificado; os atributos de {actor.name} aumentaram em 25%.")
        if util.get("roubar"):
            choices = [name for name, amount in self.inventory.items() if amount > 0]
            if choices:
                stolen = random.choice(choices)
                self.inventory[stolen] -= 1
                actor.data.setdefault("inventario", {})[stolen] = actor.data.setdefault("inventario", {}).get(stolen, 0) + 1
                self.say(f"{actor.name} roubou {stolen}.")
            else:
                self.say("Não havia consumíveis para roubar.")
        if util.get("ligacao_igualitaria"):
            for attr in ("hp", "energy", "shield"):
                avg = round((getattr(actor, attr) + getattr(target, attr)) / 2)
                setattr(actor, attr, avg)
                setattr(target, attr, avg)
            self.say(f"{actor.name} e {target.name} compartilharam vida, energia e escudo igualmente.")
        if util.get("dominio"):
            if actor.domain_used or actor.domain_turns or actor.domain_pending:
                self.say("Este combatente já iniciou uma expansão nesta batalha.")
            else:
                actor.domain_pending = 1
                actor.domain_used = True
                self.say(f"{actor.name} começou a expandir o domínio; ele se abrirá no próximo turno.")
        if util.get("clima"):
            self.set_weather(util["clima"])
        if util.get("terreno"):
            self.set_terrain(util["terreno"], actor)
        if util.get("alternar_forma"):
            forms = actor.data.get("formas", [])
            if forms:
                if "forma_base_stats" not in actor.data:
                    actor.data["forma_base_stats"] = {
                        "vida": actor.max_hp, "energia": actor.max_energy, "escudo": actor.max_shield,
                        "velocidade": actor.speed, "defesa": actor.data.get("defesa", 0), "elemento": actor.base_element,
                    }
                current_index = next((i for i, form in enumerate(forms) if form.get("nome") == actor.form), -1)
                next_index = current_index + 1
                if next_index >= len(forms):
                    actor.form = None
                    stats = actor.data["forma_base_stats"]
                    self.say(f"{actor.name} voltou à configuração normal.")
                else:
                    form = forms[next_index]
                    actor.form = form.get("nome")
                    stats = form
                    self.say(f"{actor.name} mudou para {actor.form}.")
                hp_ratio = actor.hp / max(1, actor.max_hp)
                energy_ratio = actor.energy / max(1, actor.max_energy)
                shield_ratio = actor.shield / max(1, actor.max_shield)
                actor.max_hp = int(stats.get("vida", actor.max_hp))
                actor.hp = max(1, round(actor.max_hp * hp_ratio))
                actor.max_energy = int(stats.get("energia", actor.max_energy))
                actor.energy = round(actor.max_energy * energy_ratio)
                actor.max_shield = int(stats.get("escudo", actor.max_shield))
                actor.shield = round(actor.max_shield * shield_ratio)
                actor.speed = int(stats.get("velocidade", actor.speed))
                actor.data["defesa"] = int(stats.get("defesa", actor.data.get("defesa", 0)))
                actor.element = stats.get("elemento", actor.base_element)

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
                    if buff == "velocidade":
                        fighter.speed = max(1, fighter.speed - int(fighter.data.pop("velocidade_buff", 0)))
                    if buff == "provocado":
                        fighter.forced_target = None
                    if buff == "critico":
                        fighter.data.pop("critico_buff", None)
                    if buff == "defesa":
                        fighter.data.pop("defesa_buff", None)
                    self.say(f"O efeito {buff} de {fighter.name} acabou.")
            if fighter.domain_turns > 0:
                fighter.domain_turns -= 1
                if fighter.domain_turns == 0:
                    self.say(f"O domínio {fighter.domain_name} de {fighter.name} se desfez.")
                    fighter.domain_name = None
            if fighter.contract_turns > 0:
                fighter.contract_turns -= 1
                if fighter.contract_turns == 0:
                    fighter.contract = None
                    self.say(f"O contrato temporário de {fighter.name} terminou.")
                    if fighter.kind == "boxeador":
                        fighter.action_disabled_turns = max(fighter.action_disabled_turns, 1)
                        self.say(f"{fighter.name} ficou exausto após o contrato.")
            if fighter.worm_turns > 0:
                fighter.worm_turns -= 1
                if fighter.worm_turns == 0:
                    self._restore_worm(fighter)
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
                self.damage_received[target.name] = self.damage_received.get(target.name, 0) + int(weather_cfg["raio"])
                if target.hp == 0:
                    self._defeat(target, damage=int(weather_cfg["raio"]))
        if self.weather_turns > 0:
            self.weather_turns -= 1
            if self.weather_turns == 0:
                self.weather = "limpo"
                self.weather_locked = False
                self.weather_source = None
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
                if fighter.hp == 0:
                    self._defeat(fighter, damage=damage)
        elif "magmático" in terrain or "magmatico" in terrain:
            if fighter.element not in ("fogo", "rocha"):
                fighter.hp = max(0, fighter.hp - 8)
                self.apply_effect(fighter, "queima", 1)
                self.say(f"O terreno magmático causou 8 de dano em {fighter.name}.")
                if fighter.hp == 0:
                    self._defeat(fighter, damage=8)

    def _check_winner(self) -> None:
        if not self.living(self.enemies):
            self.winner = "player" if self.living(self.players) else "escape"
        elif not self.living(self.players):
            self.winner = "escape" if self.players and all(f.fled for f in self.players) else "enemy"

    def _element_multiplier(self, defender: Fighter, element: str) -> float:
        profile = ELEMENTOS.get(defender.element, {})
        weather_element = {"chuva": "agua", "sol": "fogo", "neve": "gelo", "tempestade": "raio", "chuva_trovoada": "raio", "lua_azul": "luz"}.get(self.weather)
        extra = ELEMENTOS.get(weather_element, {}) if defender.data.get("tipagem_climatica") else {}
        if element in profile.get("anula", []) or element in extra.get("anula", []) or ("rochoso" in self.terrain.casefold() and element in ("raio", "eletrico")):
            return 0
        defender_relics = RELIQUIAS_INIMIGO if defender.kind in INIMIGOS else RELIQUIAS
        defender_mods = defender_relics.get(defender.relic, {}).get("mods", {})
        if element in profile.get("fraco_a", []) or element in extra.get("fraco_a", []):
            if defender_mods.get("imune_fraquezas"):
                return 1
            return 1.5
        if element in profile.get("resiste", []) or element in extra.get("resiste", []):
            return 0.5
        if defender.effects.get("encharcado", 0) and element in ("raio", "eletrico"):
            return 1.5
        return 1

    def _weather_multiplier(self, element: str) -> float:
        return CLIMAS.get(self.weather, {}).get("elementos", {}).get(element, 1)

    def attack(self, actor: Fighter, attack_name: str, target: Fighter, _release: bool = False) -> None:
        attack = ATAQUES[attack_name]
        if actor.side == "player" and "fugir" in actor.restrictions:
            self.say(f"{actor.name} não pode atacar: o elixir da negação está em vigor.")
            return
        if attack.get("util", {}).get("sacrificio") and self.mode not in ("dupla", "bots"):
            self.say("Sacrifício só pode ser usado no modo Dupla.")
            return
        if actor.relic == "máscara de esqueleto" and attack_name not in actor.available_attacks():
            self.say("A máscara limita os ataques às técnicas Hollow.")
            return
        if attack.get("primeiro_turno") and actor.turns_taken > 1:
            self.say(f"{attack_name} só funciona no primeiro turno de quem o usa.")
            return
        required = int(attack.get("requer", 0))
        if required and actor.attack_count < required:
            self.say(f"{attack_name} precisa de {required} ataques anteriores; progresso {actor.attack_count}.")
            return
        actor_relic_table = RELIQUIAS_INIMIGO if actor.kind in INIMIGOS else RELIQUIAS
        actor_relic_mods = actor_relic_table.get(actor.relic, {}).get("mods", {})
        charge_turns = 0 if actor_relic_mods.get("remove_carregamento") else int(
            attack.get("carrega", 0) or (1 if actor.relic == "grande espada" and int(attack.get("dano", 0)) >= 35 else 0))
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
        if util and int(attack.get("dano", 0)) <= 0:
            self._use_attack_utility(actor, target, util, attack_name)
            self._record_action(actor, "attack")
            self._advance()
            return
        targets = (self.living(self.enemies if actor.side == "player" else self.players)
                   if attack.get("area") else [target])
        if (not attack.get("area") and actor.forced_target
                and any(actor.forced_target is foe for foe in self.living(self.enemies if actor.side == "player" else self.players))):
            targets = [actor.forced_target]
        repeated_bonus = 0
        forced_critical = actor.guaranteed_next_critical
        if actor.relic == "soco inglês sequente":
            if actor.last_attack == attack_name:
                actor.repeated_attack_bonus = min(100, actor.repeated_attack_bonus + 20)
            else:
                actor.repeated_attack_bonus = 0
            actor.last_attack = attack_name
            repeated_bonus = actor.repeated_attack_bonus
            forced_critical = forced_critical or repeated_bonus >= 100
            if repeated_bonus >= 100:
                actor.repeated_attack_bonus = 0
        for defender in targets:
            if not defender.alive:
                continue
            if (defender.relic == "boneco substituto" and not defender.substitute_used
                    and defender.hp / max(1, defender.max_hp) <= .3):
                defender.substitute_turns = 4  # conta os próximos três turnos completos do portador
                defender.substitute_used = True
                self.say(f"O boneco substituto protegeu {defender.name} por 3 turnos.")
            if defender.substitute_turns > 0:
                self.say(f"O boneco substituto recebeu o ataque de {actor.name} no lugar de {defender.name}.")
                continue
            if defender.buffs.get("imunidade", 0):
                self.say(f"A proteção de {defender.name} bloqueou o ataque de {actor.name}.")
                continue
            evade = min(ESQUIVA["maximo"], defender.speed / ESQUIVA["divisor"])
            actor_table = RELIQUIAS_INIMIGO if actor.kind in INIMIGOS else RELIQUIAS
            actor_precision_mods = actor_table.get(actor.relic, {}).get("mods", {})
            actor_accuracy = actor_precision_mods.get("precisao", 0)
            if int(attack.get("carrega", 0)) > 0:
                actor_accuracy += actor_precision_mods.get("precisao_carregados", 0)
            evade = max(0, evade - actor_accuracy)
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
            ability_mods = actor.data.get("habilidade", {}).get("mods", {})
            if ability_mods.get("hell_adaptive") and (self.weather == "sol" or "magmático" in terrain_text or "magmatico" in terrain_text):
                terrain_bonus *= 1.5
            strikes = int(attack.get("golpes", 1))
            if attack.get("golpes_aleatorios"):
                low, high = attack["golpes_aleatorios"]
                strikes = random.randint(int(low), int(high))
            base = float(attack.get("dano", 0)) * max(1, strikes) * actor.damage_multiplier() * terrain_bonus
            dice = random.randint(0, 10)
            base *= 1 + dice / 10
            crit_chance = float(actor.data.get("critico", 5))
            crit_chance += actor_relic_mods.get("critico", 0)
            crit_chance += actor.data.get("habilidade", {}).get("mods", {}).get("critico", 0)
            if actor.form:
                current_form = next((f for f in actor.data.get("formas", []) if f.get("nome") == actor.form), {})
                crit_chance += current_form.get("bonus", {}).get("critico", 0)
                crit_chance += current_form.get("habilidade", {}).get("mods", {}).get("critico", 0)
            if actor.contract and "critico" in CONTRATOS.get(actor.contract, {}).get("mods", {}):
                crit_chance += CONTRATOS[actor.contract]["mods"]["critico"]
            crit_chance += actor.data.get("critico_buff", 0)
            base *= 1 + repeated_bonus / 100
            if forced_critical:
                crit_chance = 100
                actor.guaranteed_next_critical = False
            critical = random.random() < (crit_chance / 100)
            if critical:
                base *= 1.5
                self.say(f"Dado: {dice}/10 · crítico! Dano calculado com buffs: {round(base)}.")
            else:
                self.say(f"Dado: {dice}/10 · dano calculado com buffs: {round(base)}.")
            if self.weather == "nevoa":
                base *= .5
            damage = round(base * self._element_multiplier(defender, element) * self._weather_multiplier(element))
            if defender.relic == "amuleto de absorção elemental":
                weather_element = {"chuva": "agua", "sol": "fogo", "neve": "gelo", "tempestade": "raio", "trovoada": "raio", "chuva_trovoada": "raio", "chuva_tempestade": "agua", "lua_azul": "luz"}.get(self.weather)
                if weather_element == element:
                    heal = min(defender.max_hp - defender.hp, round(damage * .2))
                    defender.hp += heal
                    self.say(f"{defender.name} absorveu o elemento e recuperou {heal} de vida.")
                    continue
            actor_relics = RELIQUIAS_INIMIGO if actor.kind in INIMIGOS else RELIQUIAS
            actor_mods = actor_relics.get(actor.relic, {}).get("mods", {})
            if actor_mods.get("dano_espadas") and any(token in defender.kind for token in ("espad", "samurai", "cavaleiro negro")):
                damage = round(damage * actor_mods["dano_espadas"])
            damage = round(damage * defender.vulnerability.get(element, 1))
            defender_relics = RELIQUIAS_INIMIGO if defender.kind in INIMIGOS else RELIQUIAS
            defender_mods = defender_relics.get(defender.relic, {}).get("mods", {})
            damage = round(damage * (1 - defender_mods.get("reducao", 0)))
            damage = round(damage * (1 - defender.data.get("reducao_lua_azul", .8 if self.weather == "lua_azul" else 0)))
            damage = round(damage * (1 + float(defender.data.get("vaso_vulnerabilidade", 0))))
            if defender.domain_turns > 0:
                damage = round(damage * .8)
            defense = max(0, int(defender.data.get("defesa", 0)) + int(defender.data.get("defesa_buff", 0)) + int(defender_mods.get("defesa", 0)))
            defense = round(defense * (1 - min(1, float(attack.get("perfura", 0)))))
            damage = max(0, damage - defense)
            if (defender_mods.get("wonder_guard") and defender.hp - damage <= 0
                    and self._element_multiplier(defender, element) <= 1):
                damage = max(0, defender.hp - 1)
                self.say(f"Wonder-Guard protegeu {defender.name}; apenas um golpe efetivo pode derrotá-lo.")
            if defender.defending and defender.side in ("player", "rival") and defender.max_shield > 0 and defender.shield > 0:
                absorbed = min(defender.shield, round(damage * ESCUDO["absorcao"], 2))
                defender.shield = round(defender.shield - absorbed, 2)
                damage = round(damage - absorbed, 2)
                self.say(f"O escudo de {defender.name} absorveu {absorbed:g} de dano.")
                if defender.shield <= 0:
                    defender.shield = 0
                    defender.shield_recharge = ESCUDO["recarga"]
                    defender.defending = False
                    self.say(f"O escudo de {defender.name} quebrou; recarrega em {defender.shield_recharge} turnos.")
            defender.hp = max(0, round(defender.hp - damage, 2))
            defender.data["last_damage"] = damage
            if critical and defender.hp == 0 and defender.kind == "gojo":
                self.say(f"Pra que dar crítico no {defender.name} Arrogante!")
            self.damage_dealt[actor.name] = round(self.damage_dealt.get(actor.name, 0) + damage, 2)
            self.damage_received[defender.name] = round(self.damage_received.get(defender.name, 0) + damage, 2)
            self.say(f"{actor.name} usou {attack_name}: {defender.name} recebeu {damage:g} de dano.")
            reflected = round(damage * defender_mods.get("espinhos", 0))
            if reflected > 0 and actor.alive:
                actor.hp = max(0, actor.hp - reflected)
                self.damage_received[actor.name] = round(self.damage_received.get(actor.name, 0) + reflected, 2)
                self.say(f"A armadura de espinhos refletiu {reflected} de dano em {actor.name}.")
                if actor.hp <= 0:
                    self._defeat(actor, defender, reflected)
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
            if actor.relic == "vaso ganancioso":
                actor.data["vaso_acertos"] = int(actor.data.get("vaso_acertos", 0)) + 1
                actor.data["vaso_vulnerabilidade"] = min(.5, .1 * actor.data["vaso_acertos"])
            if util:
                self._use_attack_utility(actor, defender, util, attack_name)
            effect = attack.get("efeito")
            if effect and random.randint(1, 100) <= int(attack.get("chance", 100)):
                self.apply_effect(defender, effect, int(attack.get("duracao", 1)))
            if actor.buffs.get("aleatorio", 0):
                self.apply_effect(defender, random.choice(list(EFEITOS)), 2)
            on_hit = actor.data.get("habilidade", {}).get("mods", {}).get("on_hit", {})
            if on_hit and random.randint(1, 100) <= int(on_hit.get("chance", 100)):
                self.apply_effect(defender, on_hit["efeito"], int(on_hit.get("duracao", 1)))
            relic_on_hit = actor_relic_mods.get("on_hit", {})
            if relic_on_hit and random.randint(1, 100) <= int(relic_on_hit.get("chance", 100)):
                effects = relic_on_hit.get("efeitos", [relic_on_hit.get("efeito")])
                for relic_effect in filter(None, effects):
                    self.apply_effect(defender, relic_effect, int(relic_on_hit.get("duracao", 1)))
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
                self._defeat(defender, actor, damage)
                if actor.worm_turns and (defender.hp <= 0 or damage >= 100):
                    self._restore_worm(actor)
        self._record_action(actor, "attack")
        self._check_winner()
        self._advance()

    def apply_effect(self, target: Fighter, effect: str, duration: int = 2) -> None:
        if effect not in EFEITOS:
            return
        if target.buffs.get("imunidade", 0):
            self.say(f"{target.name} está protegido e não recebeu {EFEITOS[effect]['estado']}.")
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
        if "defender" in actor.restrictions or (actor.contract and "defender" in CONTRATOS.get(actor.contract, {}).get("restringe", [])):
            self.say(f"{actor.name} não pode defender por causa de sua relíquia/efeito.")
            return
        if actor.side not in ("player", "rival") or actor.max_shield <= 0 or actor.shield_recharge > 0 or actor.shield <= 0:
            self.say(f"O escudo de {actor.name} está indisponível; não é possível defender agora.")
            return
        actor.defending = True
        self._record_action(actor, "defender")
        self.say(f"{actor.name} levantou o escudo ({actor.shield}/{actor.max_shield}); ele absorve {round(ESCUDO['absorcao'] * 100)}% do próximo dano até a próxima rodada.")
        self._advance()

    def use_item(self, actor: Fighter, item_name: str, target: Fighter, inventory: dict[str, int], choice: str | None = None) -> None:
        if item_name == "alma" and actor.relic != "máscara de esqueleto":
            self.say("A alma só pode ser usada por quem equipa a máscara de esqueleto.")
            return
        if actor.relic == "máscara de esqueleto" and item_name not in {"pedra de chamas", "alma", "bomba de chamas azuis"}:
            self.say("A máscara permite apenas os consumíveis de chamas Hollow.")
            return
        if inventory.get(item_name, 0) <= 0:
            self.say(f"{item_name}: sem unidades disponíveis.")
            return
        item = ITENS[item_name]
        kind = item.get("tipo")
        if ("itens" in actor.restrictions
                or ("itens" in CONTRATOS.get(actor.contract, {}).get("restringe", []))
                or ("itens_normais" in actor.restrictions and item_name not in {"pedra de chamas", "alma", "bomba de chamas azuis"})):
            self.say(f"{actor.name} não pode usar este item por causa de uma restrição ativa.")
            return
        item_weather = item.get("clima")
        if item_weather and item_weather not in CLIMAS:
            self.say(f"O clima configurado para {item_name} não é válido.")
            return
        if item_weather and self.weather_locked and item_weather != self.weather:
            self.set_weather(item_weather, from_item=True)
            return
        if kind == "vinho":
            inventory[item_name] -= 1
            target.hp = target.max_hp
            target.data["healed_in_battle"] = True
            target.action_disabled_turns = max(target.action_disabled_turns, 2)
            self.say(f"{target.name} bebeu o barril de vinho, recuperou toda a vida e ficará 2 turnos sem agir.")
            self._record_action(actor, "item")
            self._advance()
            return
        if kind == "barril":
            contents = actor.data.setdefault("barril_conteudo", [])
            if choice and choice.startswith("retirar:"):
                stored = choice.split(":", 1)[1]
                if stored not in contents:
                    self.say("Esse item não está guardado no barril.")
                    return
                contents.remove(stored)
                inventory[stored] = inventory.get(stored, 0) + 1
                self.say(f"{actor.name} retirou {stored} do barril ({len(contents)}/3).")
            else:
                stored = choice
                if len(contents) >= 3:
                    self.say("O barril já está cheio (máximo de 3 itens).")
                    return
                if not stored or inventory.get(stored, 0) <= 0:
                    self.say("Escolha um item disponível para guardar no barril.")
                    return
                stored_data = ITENS.get(stored, {})
                if stored_data.get("tipo") in {"cura", "energia", "forca", "aleatorio", "velocidade", "alma", "pedra"} or "poção" in stored.casefold() or "pocao" in stored.casefold():
                    self.say("Poções e pedras não podem ser armazenadas no barril.")
                    return
                inventory[stored] -= 1
                contents.append(stored)
                self.say(f"{actor.name} guardou {stored} no barril ({len(contents)}/3).")
            self._record_action(actor, "item")
            self._advance()
            return
        if kind == "troca_atributos":
            inventory[item_name] -= 1
            before_actor = (actor.hp, actor.energy, actor.shield)
            before_target = (target.hp, target.energy, target.shield)
            for attr in ("hp", "energy", "shield"):
                first, second = getattr(actor, attr), getattr(target, attr)
                setattr(actor, attr, min(actor.max_hp if attr == "hp" else actor.max_energy if attr == "energy" else 10**9, second))
                setattr(target, attr, min(target.max_hp if attr == "hp" else target.max_energy if attr == "energy" else 10**9, first))
            self.say(
                f"{actor.name} trocou vida, energia e escudo com {target.name}: "
                f"HP {before_actor[0]}↔{before_target[0]}, EN {before_actor[1]}↔{before_target[1]}, "
                f"ESC {before_actor[2]}↔{before_target[2]}."
            )
            self._record_action(actor, "item")
            self._advance()
            return
        if kind == "alma":
            inventory[item_name] -= 1
            choice = choice or "forca"
            if choice == "forca":
                target.buffs["forca"] = max(target.buffs.get("forca", 0), 3)
            elif choice == "defesa":
                target.buffs["defesa"] = max(target.buffs.get("defesa", 0), 3)
                target.data["defesa_buff"] = 10
            elif choice == "energia":
                target.energy = target.max_energy
            else:
                inventory[item_name] += 1
                self.say("Escolha ataque, defesa ou energia para usar a alma.")
                return
            self.say(f"A alma concedeu bônus de {choice} a {target.name}.")
            self._record_action(actor, "item")
            self._advance()
            return
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
        if item_weather:
            # Climas invocados por consumíveis ficam protegidos durante sua duração.
            self.set_weather(item_weather, from_item=True)
        if kind == "cura":
            if "cura" in actor.restrictions:
                inventory[item_name] += 1
                self.say("O elixir da negação impede o uso de cura.")
                return
            value = int(item.get("cura", 0))
            target.hp = min(target.max_hp, target.hp + value)
            target.data["healed_in_battle"] = True
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
            if target.hp == 0:
                self._defeat(target, actor, value)
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
                    self._defeat(defender, actor, value)
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
        self._record_action(actor, "item")
        self._advance()

    def transform(self, actor: Fighter, form_name: str | None = None) -> None:
        if actor.transform_used:
            self.say(f"{actor.name} já usou sua única transformação nesta batalha.")
            return
        if "transformar" in actor.restrictions:
            self.say("O elixir da negação impede a transformação.")
            return
        if actor.contract or actor.contract_used:
            self.say("Quem fez um contrato não pode usar mega forma.")
            return
        if actor.kind == "boxeador" and actor.bravery_streak < 5:
            self.say("A megaforma do Boxeador só é liberada após 5 turnos de bravura.")
            return
        required_attacks = int(actor.data.get("transform_requer_ataques", 0))
        if actor.attack_count < required_attacks:
            self.say(f"A transformação exige {required_attacks} ataques feitos; {actor.name} fez {actor.attack_count}.")
            return
        forms = actor.data.get("formas", [])
        if not forms:
            self.say(f"{actor.name} não possui transformação.")
            return
        form = next((entry for entry in forms if entry.get("nome") == form_name), None) if form_name else forms[0]
        if form is None:
            self.say(f"Transformação inválida: {form_name}.")
            return
        actor.form = form.get("nome")
        actor.transform_used = True
        actor.form_turns = int(FORMAS["duracao"]) + 1
        actor.form_started_at_turn = actor.turns_taken
        actor.energy = max(0, actor.energy - 40)
        if form.get("elemento"):
            actor.element = form["elemento"]
        if actor.relic == "lâmina do sacrifício":
            actor.data["formed_in_battle"] = True
        transform_effect = form.get("ao_transformar", {})
        if transform_effect.get("clima"):
            self.set_weather(transform_effect["clima"])
        if transform_effect.get("terreno"):
            self.set_terrain(transform_effect["terreno"], actor)
        self.say(f"{actor.name} se transformou em {actor.form}!")
        self._record_action(actor, "transform")
        self._advance()

    def sign_contract(self, actor: Fighter, name: str, target: Fighter | None = None) -> None:
        if name not in self.contract_options(actor):
            self.say("Contrato inválido ou ainda bloqueado para este personagem.")
            return
        if "contrato" in actor.restrictions:
            self.say("O elixir da negação impede contratos.")
            return
        if actor.contract or actor.contract_used:
            self.say("Este combatente já assinou um contrato.")
            return
        if actor.form:
            self.say("Quem se transformou não pode assinar um contrato.")
            return
        if actor.kind == "boxeador" and actor.bravery_streak < 10:
            self.say("O contrato exclusivo exige 10 turnos de bravura.")
            return
        required_attacks = int(actor.data.get("contrato_requer_ataques", 0))
        if actor.attack_count < required_attacks:
            self.say(f"O contrato exige {required_attacks} ataques feitos; {actor.name} fez {actor.attack_count}.")
            return
        if name == "contrato das correntes igualitárias de fogo":
            opponents = self.living(self.enemies if actor.side in ("player", "rival") else self.players)
            if target not in opponents:
                self.say("Escolha um combatente adversário para receber as correntes.")
                return
            for current_attr, maximum_attr in (("hp", "max_hp"), ("energy", "max_energy"), ("shield", "max_shield")):
                shared_maximum = round((getattr(actor, maximum_attr) + getattr(target, maximum_attr)) / 2)
                shared_current = round((getattr(actor, current_attr) + getattr(target, current_attr)) / 2)
                setattr(actor, maximum_attr, shared_maximum)
                setattr(target, maximum_attr, shared_maximum)
                setattr(actor, current_attr, min(shared_maximum, shared_current))
                setattr(target, current_attr, min(shared_maximum, shared_current))
            self.say(f"As Correntes Igualitárias de Fogo ligaram {actor.name} a {target.name}; os máximos e valores atuais de vida, energia e escudo foram combinados pela fórmula (A + B) ÷ 2.")
        if actor.relic == "máscara de esqueleto":
            if "contratos_normais" in actor.restrictions and name != "contrato das chamas hollow":
                self.say("A máscara permite apenas o contrato das chamas Hollow.")
                return
            for item_name in list(self.inventory):
                self.inventory[item_name] = 0
            actor.data["dano_global_mult"] = actor.data.get("dano_global_mult", 1) * 1.25
            actor.data["defesa"] = actor.data.get("defesa", 0) + 10
            actor.energy = actor.max_energy
        if actor.relic == "lâmina do sacrifício":
            actor.data["contracted_in_battle"] = True
        actor.contract_turns = int(CONTRATOS[name].get("duracao", 0))
        actor.contract = name
        actor.contract_used = True
        self.say(f"{actor.name} assinou {name}.")
        self._record_action(actor, "contract")
        self._advance()

    def rest(self, actor: Fighter) -> None:
        if actor.contract and "descansar" in CONTRATOS.get(actor.contract, {}).get("restringe", []):
            self.say(f"{actor.name} não pode descansar durante este contrato.")
            return
        actor.energy = min(actor.max_energy, actor.energy + 30)
        actor.hp = min(actor.max_hp, actor.hp + round(actor.max_hp * 0.05))
        self.say(f"{actor.name} descansou e recuperou recursos.")
        self._record_action(actor, "rest")
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
        if "fugir" in actor.restrictions or (actor.contract and "fugir" in CONTRATOS.get(actor.contract, {}).get("restringe", [])):
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

    def set_weather(self, weather: str, *, from_item: bool = False) -> None:
        if self.weather_locked and weather != self.weather:
            source = "item" if self.weather_source == "item" else "efeito"
            self.say(f"O clima de {CLIMAS[self.weather]['nome']} foi gerado por {source} e está protegido contra substituição.")
            return
        if self.weather == "chuva" and weather == "tempestade":
            weather = "chuva_tempestade"
        elif self.weather == "chuva" and weather == "trovoada":
            weather = "chuva_trovoada"
        if weather not in CLIMAS:
            return
        self.weather, self.weather_turns = weather, 5
        self.weather_locked = from_item
        self.weather_source = "item" if from_item else None
        if weather == "lua_sangue":
            self.weather_turns = 999
            self.weather_locked = True
            self.weather_source = "item" if from_item else "efeito"
        elif weather == "lua_azul":
            self.weather_turns = 999
            self.weather_locked = True
            self.weather_source = "item" if from_item else "efeito"
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
        target = actor.forced_target if any(actor.forced_target is foe for foe in foes) else min(foes, key=lambda f: f.hp / max(1, f.max_hp))
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
        if actor.kind == "project the fake human" and actor.turns_taken in (2, 5, 8, 11):
            self.attack(actor, "disco ressonance", target)
            return
        utility_attacks = [name for name in actor.available_attacks()
                           if ATAQUES[name].get("util") and int(ATAQUES[name].get("dano", 0)) <= 0
                           and actor.energy >= int(ATAQUES[name].get("energia", 0))
                           and actor.attack_count >= int(ATAQUES[name].get("requer", 0))
                           and (not ATAQUES[name].get("primeiro_turno") or actor.turns_taken <= 1)]
        domain_attack = next((name for name in utility_attacks if ATAQUES[name].get("util", {}).get("dominio")), None)
        if domain_attack and not actor.domain_turns and not actor.domain_pending:
            self.attack(actor, domain_attack, target)
            return
        for attack_name in actor.available_attacks():
            attack = ATAQUES[attack_name]
            if (attack.get("dano", 0) > 0 and actor.energy >= attack.get("energia", 0)
                    and actor.attack_count >= int(attack.get("requer", 0))
                    and (not attack.get("primeiro_turno") or actor.turns_taken <= 1)):
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
