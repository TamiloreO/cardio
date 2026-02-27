"""Boss fight location.

Special encounter that occurs every 10 rungs, featuring a powerful boss
with unique abilities and rewarding special loot upon victory.
"""
from typing import Protocol, Type
from cardio import Grid
from cardio.human_player import HumanPlayer
from cardio.boss_cards import BossCard, get_random_boss
from cardio.boss_strategy import BossStrategy
from cardio.computer_strategies import ComputerStrategy
from .location import Location
from .baseview import BaseLocationView


class BossFightView(BaseLocationView, Protocol):
    def __init__(
        self,
        computerstrategy: ComputerStrategy,
        grid: Grid,
        humanplayer: HumanPlayer,
        boss: BossCard,
        debug: bool = False,
        *args,
        **kwargs
    ) -> None:
        ...

    def handle_fight(self) -> None:
        ...


class BossFightLocation(Location):
    """A boss fight location that appears every 10 rungs."""
    marker = "👹👹👹"
    description = "BOSS FIGHT!"
    grid: Grid
    computerstrategy: BossStrategy
    boss: BossCard

    def generate(self) -> None:
        super().generate()
        self.grid = Grid(4)
        self.boss = get_random_boss(self.rung, self.seed)
        self.computerstrategy = BossStrategy(boss=self.boss, grid=self.grid)

    def handle(self, view_class: Type[BossFightView], humanplayer: HumanPlayer) -> bool:
        vnc = view_class(
            computerstrategy=self.computerstrategy,
            grid=self.grid,
            humanplayer=humanplayer,
            boss=self.boss,
            debug=False,
            description=f"⚔️ BOSS: {self.boss.name} - {self.boss.boss_title} ⚔️",
        )
        vnc.handle_fight()
        vnc.close()
        return humanplayer.lives > 0


def is_boss_rung(rung: int) -> bool:
    """Check if a rung should be a boss fight."""
    return rung > 0 and rung % 10 == 0
