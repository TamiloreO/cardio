"""TUI view for boss fights.

Extends the standard fight view with boss-specific UI elements
and enhanced victory/defeat messaging.
"""
from cardio import Grid
from cardio.human_player import HumanPlayer
from cardio.computer_strategies import ComputerStrategy
from cardio.tui.locations.fightview import TUIFightVnC

from .boss_catalog import BossDefinition


class TUIBossFightVnC(TUIFightVnC):
    """TUI view controller for boss fight encounters.
    
    Provides boss-specific messaging and reward handling.
    """

    def __init__(
        self,
        computerstrategy: ComputerStrategy,
        grid: Grid,
        humanplayer: HumanPlayer,
        boss_definition: BossDefinition,
        debug: bool = False,
        *args,
        **kwargs
    ) -> None:
        self.boss_definition = boss_definition
        super().__init__(
            computerstrategy=computerstrategy,
            grid=grid,
            humanplayer=humanplayer,
            debug=debug,
            *args,
            **kwargs
        )

    def fight_ends(self, msg: str) -> None:
        """Override to show boss-specific victory message with bonus rewards."""
        if "win" in msg.lower():
            bonus_gems = self.boss_definition.reward_gems
            self.humanplayer.gems += bonus_gems
            boss_msg = (
                f"You defeated {self.boss_definition.name}! 🏆 "
                f"Boss reward: {'💎' * bonus_gems} "
                f"(+{bonus_gems} bonus gems)"
            )
            self.message(boss_msg)
        else:
            defeat_msg = (
                f"The {self.boss_definition.name} has bested you! 💀 "
                f"{msg}"
            )
            self.message(defeat_msg)
