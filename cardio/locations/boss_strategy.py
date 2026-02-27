"""Computer strategy for boss fights.

Boss fights use a specialized strategy that places a single powerful
boss card with potential minion reinforcements.
"""
from typing import List

from cardio import Grid, GridPos, GridPosAndCard
from cardio.computer_strategies import ComputerStrategy
from cardio.fightcard import FightCard

from .boss_card import BossCard
from .boss_catalog import BossDefinition, create_boss_card


class BossStrategy(ComputerStrategy):
    """Strategy for boss encounters.
    
    Places the boss card in the center slot and handles any
    summoned minions through the standard waitlist mechanism.
    """

    def __init__(
        self,
        boss_definition: BossDefinition,
        rung: int,
        grid: Grid,
    ) -> None:
        super().__init__(grid)
        self.boss_definition = boss_definition
        self.rung = rung
        self.boss_card = create_boss_card(boss_definition, rung)
        self._boss_placed = False

    def cards_to_be_played(self, round_number: int) -> List[GridPosAndCard]:
        """Place the boss in round 0, nothing after."""
        if round_number == 0 and not self._boss_placed:
            center_slot = self.grid.width // 2
            return [GridPosAndCard(GridPos(1, center_slot), self.boss_card)]
        return []

    def play_cards(self, round_number: int) -> None:
        """Override to use BossCard instead of FightCard for the boss."""
        for pos, card in self._waitlist + self.cards_to_be_played(round_number):
            if round_number > 0 and pos.line != 0:
                continue
            
            if card and not isinstance(card, FightCard):
                if card.name == self.boss_definition.name:
                    card = BossCard.from_card(card)
                else:
                    card = FightCard.from_card(card)
            
            if self.grid.get_card(pos):
                self._waitlist.append(GridPosAndCard(pos, card))
            else:
                self.grid.set_card(pos, card)
                if card.name == self.boss_definition.name:
                    self._boss_placed = True
        
        self._waitlist = [
            item for item in self._waitlist 
            if self.grid.get_card(item.pos) is not None
        ]
