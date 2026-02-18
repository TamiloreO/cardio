from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from .deck import Deck
from .run_stats import RunHistory, RunStats

# from cardio.blueprints import thecatalog # Imported below to avoid circular imports

if TYPE_CHECKING:
    from .blueprints import Blueprint


@dataclass
class HumanPlayer:
    name: str
    lives: int = 0  # 💓
    gems: int = 0  # 💎
    spirits: int = 3  # 👻 (or droplets/essence? 💧)
    deck: Deck = field(default_factory=lambda: Deck("main"))
    collection: Deck = field(default_factory=lambda: Deck("collection"))
    hamster_blueprint: Blueprint = None  # type: ignore
    run_history: RunHistory = field(default_factory=RunHistory)

    def __post_init__(self):
        self.reset_lives()

        from cardio.blueprints import thecatalog

        if not self.hamster_blueprint:
            self.hamster_blueprint = thecatalog.get("Hamster")

    def reset_lives(self) -> None:
        self.lives = 2

    def add_run_to_history(self, rungs_completed: int, seed: str) -> RunStats:
        """Record a completed run in the player's history.

        Args:
            rungs_completed: How many rungs the player reached before the run ended.
            seed: The seed used for the run (for reproducibility).

        Returns:
            The RunStats object that was created and added to history.
        """
        stats = RunStats(rungs_completed=rungs_completed, seed=seed)
        self.run_history.add_run(stats)
        return stats

    @classmethod
    def create_new(cls, name: str) -> HumanPlayer:
        from cardio.blueprints import thecatalog

        p = cls(name=name)
        start_cards = thecatalog.find_by_potency(0, 5, which="human").instantiate()
        start_cards = [
            c
            for c in start_cards
            if c.costs_fire + c.costs_spirits <= 2 and c.has_fire + c.has_spirits <= 2
        ]
        p.collection.cards = start_cards
        return p
