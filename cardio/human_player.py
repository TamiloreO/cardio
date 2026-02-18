from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional
from .deck import Deck
from .run_stats import RunHistory, RunStats

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
    current_run_stats: Optional[RunStats] = field(default=None, repr=False)

    def __post_init__(self):
        self.reset_lives()

        from cardio.blueprints import thecatalog

        if not self.hamster_blueprint:
            self.hamster_blueprint = thecatalog.get("Hamster")

        if self.run_history is None:
            self.run_history = RunHistory()

    def reset_lives(self) -> None:
        self.lives = 2

    def start_run(self, base_seed: str) -> RunStats:
        """Start tracking a new run.

        Args:
            base_seed: The seed for the run being started.

        Returns:
            The RunStats object for tracking this run.

        Raises:
            ValueError: If base_seed is empty.
        """
        if not base_seed:
            raise ValueError("base_seed cannot be empty")
        self.current_run_stats = RunStats(base_seed=base_seed, final_rung=0)
        return self.current_run_stats

    def end_run(self, final_rung: int) -> Optional[RunStats]:
        """End the current run and add it to history.

        Args:
            final_rung: The final rung reached in this run.

        Returns:
            The completed RunStats, or None if no run was active.

        Raises:
            ValueError: If final_rung is negative.
        """
        if final_rung < 0:
            raise ValueError("final_rung cannot be negative")
        if self.current_run_stats is None:
            return None
        self.current_run_stats.final_rung = final_rung
        self.current_run_stats.complete()
        self.run_history.add_run(self.current_run_stats)
        completed_stats = self.current_run_stats
        self.current_run_stats = None
        return completed_stats

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
