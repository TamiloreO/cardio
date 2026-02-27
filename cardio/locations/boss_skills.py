"""Boss-specific skills.

These skills are exclusive to boss cards and provide unique mechanics
that differentiate boss encounters from regular fights.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from dataclasses import dataclass, field
import random
import logging

from cardio.skills import Skill, ForWhom

if TYPE_CHECKING:
    from cardio import FightCard, GridPos


@dataclass
class Evasion(Skill):
    """Boss can move horizontally to evade attacks."""
    name: str = "Evasion"
    symbol: str = "💨"
    description: str = (
        "This boss can move horizontally to an adjacent empty slot to evade attacks. "
        "Has a 40% chance to evade each incoming attack."
    )
    potency: int = 8
    forwhom: ForWhom = ForWhom.COMPUTER
    _evasion_chance: float = 0.4

    def try_evade(self, carrier: FightCard) -> bool:
        """Attempt to evade by moving to an adjacent slot. Returns True if evaded."""
        if random.random() > self._evasion_chance:
            return False

        pos = carrier.get_grid_pos()
        grid = carrier.grid
        
        possible_slots = []
        if pos.slot > 0 and grid.get_card(pos._replace(slot=pos.slot - 1)) is None:
            possible_slots.append(pos.slot - 1)
        if pos.slot < grid.width - 1 and grid.get_card(pos._replace(slot=pos.slot + 1)) is None:
            possible_slots.append(pos.slot + 1)
        
        if not possible_slots:
            return False
        
        new_slot = random.choice(possible_slots)
        new_pos = pos._replace(slot=new_slot)
        grid.move_card(carrier, new_pos)
        logging.debug("%s evades to slot %s", carrier.name, new_slot)
        return True


@dataclass
class Rampage(Skill):
    """Boss gains power each round it survives."""
    name: str = "Rampage"
    symbol: str = "🔥"
    description: str = (
        "This boss gains +1 power at the end of each round it survives."
    )
    potency: int = 7
    forwhom: ForWhom = ForWhom.COMPUTER

    def post_round(self, carrier: FightCard) -> None:
        carrier.power += 1
        logging.debug("%s rampages, power now %s", carrier.name, carrier.power)


@dataclass
class LifeSteal(Skill):
    """Boss heals for a portion of damage dealt."""
    name: str = "Life Steal"
    symbol: str = "🧛"
    description: str = (
        "This boss heals for half of the damage it deals (rounded down)."
    )
    potency: int = 6
    forwhom: ForWhom = ForWhom.COMPUTER
    _damage_dealt_this_attack: int = 0

    def pre_fight(self, carrier: FightCard) -> None:
        self._damage_dealt_this_attack = 0

    def pre_attack(self, carrier: FightCard) -> None:
        self._damage_dealt_this_attack = 0

    def register_damage(self, damage: int) -> None:
        """Called when the boss deals damage."""
        self._damage_dealt_this_attack += damage

    def post_attack(self, carrier: FightCard) -> None:
        heal_amount = self._damage_dealt_this_attack // 2
        if heal_amount > 0:
            carrier.heal_damage(heal_amount)
            logging.debug("%s steals %s life", carrier.name, heal_amount)
        self._damage_dealt_this_attack = 0


@dataclass
class Summon(Skill):
    """Boss summons minions periodically."""
    name: str = "Summon"
    symbol: str = "👥"
    description: str = (
        "This boss summons a 1/1 minion to an empty adjacent slot every 2 rounds."
    )
    potency: int = 8
    forwhom: ForWhom = ForWhom.COMPUTER
    _rounds_until_summon: int = 2

    def pre_fight(self, carrier: FightCard) -> None:
        self._rounds_until_summon = 2

    def post_round(self, carrier: FightCard) -> None:
        self._rounds_until_summon -= 1
        if self._rounds_until_summon <= 0:
            self._try_summon(carrier)
            self._rounds_until_summon = 2

    def _try_summon(self, carrier: FightCard) -> None:
        from cardio import Card
        from cardio.fightcard import FightCard as FC
        
        pos = carrier.get_grid_pos()
        grid = carrier.grid
        
        possible_slots = []
        if pos.slot > 0 and grid.get_card(pos._replace(slot=pos.slot - 1)) is None:
            possible_slots.append(pos.slot - 1)
        if pos.slot < grid.width - 1 and grid.get_card(pos._replace(slot=pos.slot + 1)) is None:
            possible_slots.append(pos.slot + 1)
        
        if not possible_slots:
            logging.debug("%s cannot summon - no empty slots", carrier.name)
            return
        
        slot = random.choice(possible_slots)
        minion_card = Card(
            name="Minion",
            power=1,
            health=1,
            costs_fire=0,
            costs_spirits=0,
            has_fire=0,
            has_spirits=0,
        )
        minion = FC.from_card(minion_card)
        grid.set_card(pos._replace(slot=slot), minion)
        logging.debug("%s summons a minion at slot %s", carrier.name, slot)


@dataclass
class Reflective(Skill):
    """Boss reflects a portion of damage back to attacker."""
    name: str = "Reflective"
    symbol: str = "🪞"
    description: str = (
        "This boss reflects 1 damage back to any card that attacks it."
    )
    potency: int = 5
    forwhom: ForWhom = ForWhom.COMPUTER


@dataclass
class Enrage(Skill):
    """Boss becomes stronger when damaged below half health."""
    name: str = "Enrage"
    symbol: str = "😡"
    description: str = (
        "When this boss falls below half health, it permanently gains +2 power."
    )
    potency: int = 6
    forwhom: ForWhom = ForWhom.COMPUTER
    _has_enraged: bool = False
    _original_health: int = 0

    def pre_fight(self, carrier: FightCard) -> None:
        self._has_enraged = False
        self._original_health = carrier.health

    def check_enrage(self, carrier: FightCard) -> bool:
        """Check if enrage should trigger. Returns True if it triggered."""
        if self._has_enraged:
            return False
        
        if carrier.health <= self._original_health // 2:
            carrier.power += 2
            self._has_enraged = True
            logging.debug("%s enrages! Power now %s", carrier.name, carrier.power)
            return True
        return False


def get_boss_skill_types():
    """Return all boss-specific skill types."""
    return [Evasion, Rampage, LifeSteal, Summon, Reflective, Enrage]
