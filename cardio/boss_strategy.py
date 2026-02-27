"""Boss fight computer strategy.

Handles the special mechanics of boss fights, including boss-specific skills.
"""
from typing import List, Optional
from cardio import Grid, GridPos, GridPosAndCard, FightCard
from cardio.computer_strategies import ComputerStrategy
from cardio.boss_cards import BossCard
from cardio.boss_skills import Evasion


class BossStrategy(ComputerStrategy):
    """Strategy for a single boss card.
    
    The boss is placed in the center slot and uses special abilities each round.
    """

    def __init__(self, boss: BossCard, grid: Grid) -> None:
        super().__init__(grid)
        self.boss = boss
        self.boss_card: Optional[FightCard] = None

    def cards_to_be_played(self, round_number: int) -> List[GridPosAndCard]:
        if round_number == 0:
            center_slot = self.grid.width // 2
            return [GridPosAndCard(GridPos(1, center_slot), self.boss)]
        return []

    def play_cards(self, round_number: int) -> None:
        """Play cards and track the boss FightCard."""
        super().play_cards(round_number)
        
        if round_number == 0:
            # Find and store the boss card reference
            for slot in range(self.grid.width):
                card = self.grid.get_card(GridPos(1, slot))
                if card is not None:
                    self.boss_card = card
                    break

    def handle_boss_turn_start(self, round_number: int) -> bool:
        """Handle boss abilities at the start of each turn.
        
        Returns True if the boss moved (for UI feedback).
        """
        if self.boss_card is None:
            return False

        # Handle Evasion skill
        if Evasion in self.boss_card.skills:
            evasion_skill = self.boss_card.skills.get(Evasion)
            return evasion_skill.try_evade(self.boss_card, round_number)
        
        return False

    def get_boss_position(self) -> Optional[GridPos]:
        """Get the current position of the boss."""
        if self.boss_card is not None:
            return self.boss_card.get_grid_pos()
        return None
