"""Boss-specific skills.

These skills are exclusive to boss cards and provide unique combat abilities.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from dataclasses import dataclass, field
import random
import logging

from .skills import Skill, ForWhom

if TYPE_CHECKING:
    from cardio import FightCard


@dataclass
class Evasion(Skill):
    """Boss can move horizontally to evade attacks."""
    name: str = "Evasion"
    symbol: str = "💨"
    description: str = "At the start of each round, the boss may move to an adjacent empty slot, evading the card in its previous position."
    potency: int = 8
    forwhom: ForWhom = ForWhom.COMPUTER
    _last_evade_round: int = -1

    def pre_fight(self, carrier: FightCard) -> None:
        self._last_evade_round = -1

    def try_evade(self, carrier: FightCard, round_num: int) -> bool:
        """Attempt to evade. Returns True if evasion was successful."""
        if self._last_evade_round == round_num:
            return False

        pos = carrier.get_grid_pos()
        grid = carrier.grid

        # Find adjacent empty slots
        possible_slots = []
        if pos.slot > 0 and grid.get_card(pos._replace(slot=pos.slot - 1)) is None:
            possible_slots.append(pos.slot - 1)
        if pos.slot < grid.width - 1 and grid.get_card(pos._replace(slot=pos.slot + 1)) is None:
            possible_slots.append(pos.slot + 1)

        if possible_slots and random.random() < 0.4:
            new_slot = random.choice(possible_slots)
            grid.move_card(carrier, pos._replace(slot=new_slot))
            self._last_evade_round = round_num
            logging.debug("%s evades to slot %s", carrier.name, new_slot)
            return True
        return False


@dataclass
class Rampage(Skill):
    """Boss gains power for each card it kills."""
    name: str = "Rampage"
    symbol: str = "🔥"
    description: str = "Each time this boss destroys a card, it gains +1 power permanently."
    potency: int = 7
    forwhom: ForWhom = ForWhom.COMPUTER
    _kills: int = 0

    def pre_fight(self, carrier: FightCard) -> None:
        self._kills = 0

    def on_kill(self, carrier: FightCard) -> None:
        self._kills += 1
        carrier.power += 1
        logging.debug("%s rampages! Now at %s power", carrier.name, carrier.power)


@dataclass
class SoulDrain(Skill):
    """Boss heals when dealing damage."""
    name: str = "Soul Drain"
    symbol: str = "🩸"
    description: str = "When this boss deals damage to a card, it heals for half the damage dealt (rounded down)."
    potency: int = 6
    forwhom: ForWhom = ForWhom.COMPUTER

    def heal_from_damage(self, carrier: FightCard, damage_dealt: int) -> int:
        heal_amount = damage_dealt // 2
        if heal_amount > 0:
            carrier.heal_damage(heal_amount)
            logging.debug("%s drains %s health", carrier.name, heal_amount)
        return heal_amount


@dataclass
class Enrage(Skill):
    """Boss gains power when damaged."""
    name: str = "Enrage"
    symbol: str = "😤"
    description: str = "When this boss takes damage, it gains +1 power until the end of the fight."
    potency: int = 5
    forwhom: ForWhom = ForWhom.COMPUTER
    _rage_stacks: int = 0

    def pre_fight(self, carrier: FightCard) -> None:
        self._rage_stacks = 0

    def on_damaged(self, carrier: FightCard) -> None:
        self._rage_stacks += 1
        carrier.power += 1
        logging.debug("%s enrages! Now at %s power (%s stacks)", 
                      carrier.name, carrier.power, self._rage_stacks)


@dataclass
class Multiattack(Skill):
    """Boss attacks multiple slots."""
    name: str = "Multiattack"
    symbol: str = "⚔️"
    description: str = "This boss attacks all adjacent slots in addition to the slot directly in front of it."
    potency: int = 8
    forwhom: ForWhom = ForWhom.COMPUTER

    def get_extra_targets(self, carrier: FightCard) -> list:
        """Returns list of additional slot indices to attack."""
        pos = carrier.get_grid_pos()
        grid = carrier.grid
        extra = []
        if pos.slot > 0:
            extra.append(pos.slot - 1)
        if pos.slot < grid.width - 1:
            extra.append(pos.slot + 1)
        return extra


def get_boss_skilltypes():
    """Return all boss skill types."""
    return [Evasion, Rampage, SoulDrain, Enrage, Multiattack]
