"""Boss fight location implementation.

Boss fights occur every 10 rungs and feature a single powerful boss
with unique abilities and enhanced rewards.
"""
from typing import Protocol, Type

from cardio import Grid
from cardio.human_player import HumanPlayer
from cardio.locations.location import Location, BOSS_FIGHT_INTERVAL
from cardio.locations.baseview import BaseLocationView
from cardio.computer_strategies import ComputerStrategy

from .boss_catalog import BossDefinition, get_boss_for_rung
from .boss_strategy import BossStrategy


class BossFightView(BaseLocationView, Protocol):
    """Protocol for boss fight views."""
    
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
        ...

    def handle_fight(self) -> None:
        ...


class BossFightLocation(Location):
    """A location featuring a boss encounter.
    
    Boss fights provide:
    - A single powerful enemy with unique skills
    - Enhanced gem rewards on victory
    - Scaling difficulty based on rung number
    """
    
    marker = "👑B"
    grid: Grid
    computerstrategy: BossStrategy
    boss_definition: BossDefinition

    def generate(self) -> None:
        super().generate()
        self.boss_definition = get_boss_for_rung(self.rung, self.seed)
        self.grid = Grid(4)
        self.computerstrategy = BossStrategy(
            boss_definition=self.boss_definition,
            rung=self.rung,
            grid=self.grid,
        )
        self.description = f"BOSS: {self.boss_definition.name}! {self.boss_definition.description}"

    def handle(self, view_class: Type[BossFightView], humanplayer: HumanPlayer) -> bool:
        vnc = view_class(
            computerstrategy=self.computerstrategy,
            grid=self.grid,
            humanplayer=humanplayer,
            boss_definition=self.boss_definition,
            debug=False,
            description=self.description,
        )
        vnc.handle_fight()
        vnc.close()
        return humanplayer.lives > 0
