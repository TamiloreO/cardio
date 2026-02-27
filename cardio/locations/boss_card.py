"""Boss card implementation.

BossCard extends FightCard with boss-specific behavior including
special skill interactions and modified attack/defense mechanics.
"""
from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Optional

from cardio import Card
from cardio.fightcard import FightCard
from cardio import skills as sk
from .boss_skills import Evasion, LifeSteal, Reflective, Enrage

if TYPE_CHECKING:
    from cardio import GridPos


class BossCard(FightCard):
    """A special card type for boss encounters.
    
    Boss cards have enhanced mechanics including:
    - Evasion: Can dodge attacks by moving horizontally
    - Life Steal: Heals when dealing damage
    - Reflective: Reflects damage to attackers
    - Enrage: Gains power when below half health
    """

    def take_damage(self, howmuch: int) -> int:
        """Override to handle boss-specific damage mechanics."""
        assert howmuch >= 0
        if howmuch == 0:
            return 0

        # Check for Evasion
        if Evasion in self.skills:
            evasion_skill = self.skills.get(Evasion)
            if evasion_skill.try_evade(self):
                logging.debug("%s evades the attack!", self.name)
                self.vnc.redraw_view()
                return howmuch  # All damage evaded

        damage_left = howmuch

        # Shield still works for bosses
        if sk.Shield in self.skills:
            damage_left -= self.skills.get(sk.Shield).absorbed_damage(
                damage_left, self.vnc.round_num
            )

        if damage_left >= self.health:
            damage_left -= self.health
            self.die()
        else:
            self.health -= damage_left
            damage_left = 0
            self.vnc.card_lost_health(self)
            
            # Check for Enrage after taking damage
            if Enrage in self.skills:
                enrage_skill = self.skills.get(Enrage)
                if enrage_skill.check_enrage(self):
                    self.vnc.redraw_view()

        logging.debug(
            "%s: -%sH (now at %sH)", self.name, howmuch - damage_left, self.health
        )
        return damage_left

    def attack(self, target: Optional[FightCard] = None) -> None:
        """Override to handle life steal damage tracking."""
        assert self.grid.find_card(self) is not None
        assert self.grid.find_card(self).line != 0
        attacker_player, target_player = ("computer", "human")

        attacker_power = self.power

        if sk.Underdog in self.skills and target and attacker_power < target.power:
            logging.debug("%s: +1 P (Underdog)", self.name)
            attacker_power += 1

        if attacker_power == 0:
            logging.debug("%s would attack but has 0 power, so doesn't", self.name)
            return

        if sk.Weakness in self.skills:
            attacker_power = self.skills.get(sk.Weakness).modify_damage(attacker_power)

        a_str = f"{attacker_player.upper()[0]}:{self.xname()}"
        t_str = f"{target_player.upper()[0]}:{target.xname() if target else '-'}"
        logging.debug("%s attacks %s", a_str, t_str)

        self.vnc.show_card_activate(self)
        self.skills.call("pre_attack", self)

        if (
            sk.LuckyStrike in self.skills
            and not self.skills.get(sk.LuckyStrike).is_lucky()
        ):
            self.die()
            logging.debug("%s gets unlucky with Lucky Strike", self.name)
            return

        attacker_touches_target = target is not None and (
            sk.Soaring not in self.skills or sk.Airdefense in target.skills
        )
        attacks_agent_directly = target is None or not attacker_touches_target

        if attacks_agent_directly:
            if sk.LuckyStrike in self.skills:
                attacker_power = self.skills.get(sk.LuckyStrike).power_up_against_agent(attacker_power)
            
            # Track damage for life steal
            if LifeSteal in self.skills:
                self.skills.get(LifeSteal).register_damage(attacker_power)
            
            self.vnc.handle_agent_damage(target_player, attacker_power)
            self.skills.call("post_attack", self)
            self.vnc.show_card_deactivate(self)
            return

        assert target is not None
        self.vnc.show_card_getting_attacked(target, self)

        target_dies_instantly = attacker_touches_target and (
            sk.InstantDeath in self.skills
            or sk.LuckyStrike in self.skills
        )
        if target_dies_instantly:
            # Track full target health for life steal
            if LifeSteal in self.skills:
                self.skills.get(LifeSteal).register_damage(target.health)
            target.die()
            logging.debug("%s dies from InstantDeath or LuckyStrike", target.name)
            self.skills.call("post_attack", self)
            self.vnc.show_card_deactivate(self)
            return

        attacker_to_lose = 0

        if sk.Spines in target.skills:
            logging.debug("%s -> %s: 1D (Spines)", target.name, self.name)
            attacker_to_lose += 1

        # Track actual damage dealt for life steal
        actual_damage = min(attacker_power, target.health)
        if LifeSteal in self.skills:
            self.skills.get(LifeSteal).register_damage(actual_damage)

        target_damage_left = target.take_damage(attacker_power)
        if target_damage_left > 0:
            if LifeSteal in self.skills:
                self.skills.get(LifeSteal).register_damage(target_damage_left)
            self.vnc.handle_agent_damage(target_player, target_damage_left)

        attacker_damage_left = self.take_damage(attacker_to_lose)
        if attacker_damage_left > 0:
            self.vnc.handle_agent_damage(attacker_player, attacker_damage_left)

        self.skills.call("post_attack", self)
        self.vnc.show_card_deactivate(self)

    @classmethod
    def from_card(cls, card: Card) -> BossCard:
        """Create a BossCard from a Card."""
        assert cls.vnc and cls.grid, "Call `init_fight` first."
        assert isinstance(card, Card)
        fc = card.copy()
        fc.__class__ = cls
        assert isinstance(fc, BossCard)
        fc._orig = card
        fc._orig._fc = fc
        return fc
