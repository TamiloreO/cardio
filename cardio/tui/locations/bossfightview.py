"""TUI view for boss fights.

Extends the standard fight view with boss-specific visuals and mechanics.
"""
import logging
from typing import Callable, Optional
from asciimatics.screen import Screen

from cardio import FightCard, GridPos
from cardio.boss_cards import BossCard
from cardio.boss_skills import Evasion, Rampage, SoulDrain, Enrage, Multiattack
from cardio.boss_strategy import BossStrategy
from cardio.fightvnc import EndOfFightException
from cardio.placement_manager import PlacementManager
from cardio.skills import InstantDeath, LuckyStrike
from ..card_primitives import (
    move_card,
    redraw_card,
    shake_card,
    clear_card,
)
from ..utils import show_text, get_keycode
from ..constants import Color, GRID_MARGIN_LEFT, BOX_WIDTH
from .fightview import TUIFightVnC


class TUIBossFightVnC(TUIFightVnC):
    """Boss fight view with special mechanics."""

    def __init__(self, boss: BossCard, *args, **kwargs) -> None:
        self.boss = boss
        super().__init__(*args, **kwargs)

    def redraw_view(self, *args, **kwargs) -> None:
        super().redraw_view(*args, **kwargs)
        self._show_boss_info()

    def _show_boss_info(self) -> None:
        """Display boss name and title at the top of the screen."""
        x = GRID_MARGIN_LEFT
        y = 1
        boss_text = f"👹 {self.boss.name} - {self.boss.boss_title} 👹"
        show_text(self.screen, (x, y), boss_text, color=Color.RED)
        
        # Show boss description on the right side
        x_desc = GRID_MARGIN_LEFT + (BOX_WIDTH + 3) * self.grid.width + 5
        show_text(self.screen, (x_desc, y), self.boss.boss_description[:50], color=Color.YELLOW)

    def _show_boss_ability_triggered(self, ability_name: str) -> None:
        """Flash a message when a boss ability activates."""
        x = GRID_MARGIN_LEFT
        y = 2
        msg = f"⚡ {ability_name}! ⚡"
        show_text(self.screen, (x, y), msg, color=Color.MAGENTA)
        self.screen.refresh()
        import time
        time.sleep(0.3)

    def _handle_boss_evasion(self) -> None:
        """Handle boss evasion at the start of each round."""
        if not isinstance(self.computerstrategy, BossStrategy):
            return

        old_pos = self.computerstrategy.get_boss_position()
        if old_pos is None:
            return

        boss_card = self.computerstrategy.boss_card
        if boss_card is None:
            return

        if self.computerstrategy.handle_boss_turn_start(self.round_num):
            new_pos = self.computerstrategy.get_boss_position()
            if new_pos and old_pos != new_pos:
                self._show_boss_ability_triggered("Evasion")
                clear_card(self.screen, old_pos)
                move_card(self.screen, boss_card, old_pos, new_pos, steps=5)
                self.redraw_view()

    def _handle_rampage(self, target: FightCard) -> None:
        """Handle Rampage skill when boss kills a card."""
        if not isinstance(self.computerstrategy, BossStrategy):
            return
        boss_card = self.computerstrategy.boss_card
        if boss_card is None or Rampage not in boss_card.skills:
            return
        
        rampage_skill = boss_card.skills.get(Rampage)
        rampage_skill.on_kill(boss_card)
        self._show_boss_ability_triggered(f"Rampage! Power now {boss_card.power}")

    def _handle_soul_drain(self, damage_dealt: int) -> None:
        """Handle SoulDrain skill when boss deals damage."""
        if not isinstance(self.computerstrategy, BossStrategy):
            return
        boss_card = self.computerstrategy.boss_card
        if boss_card is None or SoulDrain not in boss_card.skills:
            return
        
        drain_skill = boss_card.skills.get(SoulDrain)
        healed = drain_skill.heal_from_damage(boss_card, damage_dealt)
        if healed > 0:
            self._show_boss_ability_triggered(f"Soul Drain! +{healed} HP")

    def _handle_enrage(self) -> None:
        """Handle Enrage skill when boss takes damage."""
        if not isinstance(self.computerstrategy, BossStrategy):
            return
        boss_card = self.computerstrategy.boss_card
        if boss_card is None or Enrage not in boss_card.skills:
            return
        
        enrage_skill = boss_card.skills.get(Enrage)
        enrage_skill.on_damaged(boss_card)
        self._show_boss_ability_triggered(f"Enrage! Power now {boss_card.power}")

    def card_died(self, card: FightCard, pos: GridPos) -> None:
        """Override to handle Rampage when boss kills a card."""
        super().card_died(card, pos)
        
        # Check if this was a human card killed by the boss
        if card.is_human():
            self._handle_rampage(card)

    def show_card_getting_attacked(self, target: FightCard, attacker: FightCard) -> None:
        """Override to handle boss skills during attacks."""
        super().show_card_getting_attacked(target, attacker)
        
        # Handle SoulDrain for boss attacks
        if not target.is_human():
            return
        
        if isinstance(self.computerstrategy, BossStrategy):
            boss_card = self.computerstrategy.boss_card
            if boss_card is attacker:
                # Calculate damage that will be dealt
                damage = attacker.power
                if target.health > 0:
                    self._handle_soul_drain(min(damage, target.health))

    def _handle_multiattack(self, attacker: FightCard) -> None:
        """Handle Multiattack skill."""
        if Multiattack not in attacker.skills:
            return
        
        multiattack_skill = attacker.skills.get(Multiattack)
        extra_slots = multiattack_skill.get_extra_targets(attacker)
        
        for slot in extra_slots:
            target_pos = GridPos(2, slot)
            target = self.grid.get_card(target_pos)
            if target is not None:
                self._show_boss_ability_triggered(f"Multiattack on slot {slot}!")
                shake_card(self.screen, target, target_pos, "h")
                # Deal reduced damage to adjacent targets
                reduced_damage = max(1, attacker.power // 2)
                target.take_damage(reduced_damage)
                self.redraw_view()

    def _handle_round_of_fight(self) -> None:
        """Override to add boss-specific mechanics."""
        logging.debug("----- Start of round %s -----", self.round_num)
        self.stateslogger.log_current_state()
        self.decks.log()

        # Handle boss evasion at the start of each round
        self._handle_boss_evasion()

        # Play computer cards and animate how they appear:
        for pos, card in self.computerstrategy.cards_to_be_played(self.round_num):
            self.show_computer_plays_card(card, pos)
        self.computerstrategy.play_cards(self.round_num)

        # Let human draw a card:
        deck = self.handle_human_choose_deck_to_draw_from()
        if deck is not None:
            card = deck.draw_card()
            self.show_human_draws_new_card(self.decks.hand, card, deck)
            self.decks.hand.add_card(card)

        # Let human play card(s):
        self.handle_human_plays_cards(place_card_callback=self._place_card)

        self.decks.log()
        self.grid.log()

        # Activate all cards line by line:
        for linei in [2, 1, 0]:
            for slot_idx, card in enumerate(self.grid.lines[linei]):
                if card is None:
                    continue
                if linei == 0:
                    if not card.prepare():
                        continue

                # Handle multiattack for boss
                if linei == 1 and isinstance(self.computerstrategy, BossStrategy):
                    boss_card = self.computerstrategy.boss_card
                    if card is boss_card and Multiattack in card.skills:
                        self._handle_multiattack(card)

                # Track boss health before attack to detect enrage
                boss_health_before = None
                if isinstance(self.computerstrategy, BossStrategy):
                    boss_card = self.computerstrategy.boss_card
                    if boss_card:
                        boss_health_before = boss_card.health

                card.attack(self.grid.get_opposing_card(card))

                # Check for enrage
                if boss_health_before is not None:
                    boss_card = self.computerstrategy.boss_card
                    if boss_card and boss_card.health < boss_health_before:
                        self._handle_enrage()

            self._check_for_end_of_fight()

        self.damagestate.add_to_history(self.round_num)
        self._check_for_end_of_fight()

        # Call post-round hook:
        cards = [card for line in reversed(self.grid.lines) for card in line if card]
        cards += (
            self.decks.draw.cards + self.decks.hand.cards + self.decks.hamster.cards
        )
        for card in cards:
            card.skills.call("post_round", card)

        self.grid.log()
        logging.debug("----- End of round %s -----", self.round_num)

    def fight_ends(self, msg: str) -> None:
        """Override to add boss-specific rewards."""
        # Check if player won
        winner = self.damagestate.who_won()
        if winner == "human":
            # Boss victory rewards
            bonus_gems = 5 + (self.boss.health // 5)
            self.humanplayer.gems += bonus_gems
            msg = f"🏆 BOSS DEFEATED! 🏆\n\n{self.boss.name} has fallen!\n\nBonus reward: {'💎' * min(bonus_gems, 10)} ({bonus_gems} gems)"
        
        self.message(msg)
