"""Run statistics tracking for player history."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class RunStats:
    """Statistics for a completed run."""

    base_seed: str
    final_rung: int
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    ended_at: Optional[str] = None
    cards_collected: int = 0
    fights_won: int = 0
    fights_lost: int = 0

    def complete(self) -> None:
        """Mark the run as completed with the current timestamp."""
        self.ended_at = datetime.utcnow().isoformat()

    def record_fight_won(self) -> None:
        """Record a won fight."""
        self.fights_won += 1

    def record_fight_lost(self) -> None:
        """Record a lost fight."""
        self.fights_lost += 1

    def record_card_collected(self, count: int = 1) -> None:
        """Record cards collected during the run."""
        if count < 0:
            raise ValueError("Card count cannot be negative")
        self.cards_collected += count

    def get_summary(self) -> str:
        """Return a human-readable summary of the run statistics."""
        lines = [
            f"Run Summary (Seed: {self.base_seed})",
            f"  Final Rung: {self.final_rung}",
            f"  Fights Won: {self.fights_won}",
            f"  Fights Lost: {self.fights_lost}",
            f"  Cards Collected: {self.cards_collected}",
        ]
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "base_seed": self.base_seed,
            "final_rung": self.final_rung,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "cards_collected": self.cards_collected,
            "fights_won": self.fights_won,
            "fights_lost": self.fights_lost,
        }

    @classmethod
    def from_dict(cls, data: dict) -> RunStats:
        """Create RunStats from a dictionary."""
        return cls(
            base_seed=data["base_seed"],
            final_rung=data["final_rung"],
            started_at=data.get("started_at", datetime.utcnow().isoformat()),
            ended_at=data.get("ended_at"),
            cards_collected=data.get("cards_collected", 0),
            fights_won=data.get("fights_won", 0),
            fights_lost=data.get("fights_lost", 0),
        )


@dataclass
class RunHistory:
    """Collection of completed runs for a player."""

    runs: List[RunStats] = field(default_factory=list)

    def add_run(self, stats: RunStats) -> None:
        """Add a completed run to the history."""
        if stats is None:
            raise ValueError("Cannot add None run stats")
        self.runs.append(stats)

    def total_runs(self) -> int:
        """Return total number of runs."""
        return len(self.runs)

    def best_rung(self) -> int:
        """Return the best (highest) rung achieved across all runs."""
        if not self.runs:
            return 0
        return max(run.final_rung for run in self.runs)

    def total_fights_won(self) -> int:
        """Return total fights won across all runs."""
        return sum(run.fights_won for run in self.runs)

    def total_fights_lost(self) -> int:
        """Return total fights lost across all runs."""
        return sum(run.fights_lost for run in self.runs)

    def get_summary(self) -> str:
        """Return a human-readable summary of all runs."""
        if not self.runs:
            return "No runs completed yet."
        lines = [
            "Run History",
            f"  Total Runs: {self.total_runs()}",
            f"  Best Rung: {self.best_rung()}",
            f"  Total Fights Won: {self.total_fights_won()}",
            f"  Total Fights Lost: {self.total_fights_lost()}",
        ]
        return "\n".join(lines)

    def to_list(self) -> List[dict]:
        """Convert to list of dictionaries for serialization."""
        return [run.to_dict() for run in self.runs]

    @classmethod
    def from_list(cls, data: Optional[List[dict]]) -> RunHistory:
        """Create RunHistory from a list of dictionaries."""
        if data is None:
            return cls()
        return cls(runs=[RunStats.from_dict(d) for d in data])
