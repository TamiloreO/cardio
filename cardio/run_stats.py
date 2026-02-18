"""Run statistics tracking for completed runs."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class RunStats:
    """Statistics for a completed run.

    Tracks key metrics about how a run went, including how far the player got,
    when it happened, and what seed was used (for reproducibility/sharing).
    """

    rungs_completed: int
    seed: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def format_summary(self) -> str:
        """Return a human-readable summary of the run statistics."""
        return f"Reached rung {self.rungs_completed} (seed: {self.seed[:8]}...)"

    def __str__(self) -> str:
        return self.format_summary()


@dataclass
class RunHistory:
    """Collection of past run statistics for a player."""

    runs: List[RunStats] = field(default_factory=list)

    def add_run(self, stats: RunStats) -> None:
        """Add a completed run's statistics to the history."""
        self.runs.append(stats)

    def best_run(self) -> Optional[RunStats]:
        """Return the run with the most rungs completed, or None if no runs."""
        if not self.runs:
            return None
        return max(self.runs, key=lambda r: r.rungs_completed)

    def total_runs(self) -> int:
        """Return the total number of runs completed."""
        return len(self.runs)

    def average_rungs(self) -> float:
        """Return the average number of rungs completed per run."""
        if not self.runs:
            return 0.0
        return sum(r.rungs_completed for r in self.runs) / len(self.runs)

    def format_summary(self) -> str:
        """Return a human-readable summary of the run history."""
        if not self.runs:
            return "No runs completed yet."

        best = self.best_run()
        lines = [
            f"Total runs: {self.total_runs()}",
            f"Average rungs: {self.average_rungs():.1f}",
            f"Best run: {best.rungs_completed} rungs" if best else "",
        ]
        return "\n".join(line for line in lines if line)
