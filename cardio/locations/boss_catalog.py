"""Boss catalog containing all boss definitions.

Each boss has unique stats and skill combinations that provide
distinct gameplay challenges.
"""
from typing import List
from dataclasses import dataclass
import random

from cardio import Card
from cardio.skills import Shield, Spines, Regenerate, InstantDeath
from .boss_skills import Evasion, Rampage, LifeSteal, Summon, Reflective, Enrage


@dataclass
class BossDefinition:
    """Defines a boss's base attributes and skills."""
    name: str
    base_power: int
    base_health: int
    skills: List
    description: str
    reward_gems: int = 3


# The five unique boss definitions
BOSS_DEFINITIONS: List[BossDefinition] = [
    BossDefinition(
        name="Shadow Wraith",
        base_power=3,
        base_health=12,
        skills=[Evasion, LifeSteal],
        description="A spectral entity that phases through attacks and drains life force.",
        reward_gems=3,
    ),
    BossDefinition(
        name="Berserker Titan",
        base_power=2,
        base_health=15,
        skills=[Rampage, Enrage],
        description="A massive warrior that grows stronger with each passing moment.",
        reward_gems=4,
    ),
    BossDefinition(
        name="Necro Overlord",
        base_power=3,
        base_health=10,
        skills=[Summon, LifeSteal],
        description="A dark summoner who raises minions and feeds on the fallen.",
        reward_gems=4,
    ),
    BossDefinition(
        name="Crystal Guardian",
        base_power=4,
        base_health=14,
        skills=[Reflective, Shield, Regenerate],
        description="An ancient construct that reflects damage and regenerates wounds.",
        reward_gems=5,
    ),
    BossDefinition(
        name="Chaos Serpent",
        base_power=5,
        base_health=8,
        skills=[Evasion, Spines, InstantDeath],
        description="A deadly predator that strikes with lethal precision.",
        reward_gems=5,
    ),
]


def get_boss_for_rung(rung: int, seed: str) -> BossDefinition:
    """Select a random boss for the given rung.
    
    Boss selection is deterministic based on rung and seed to ensure
    consistent behavior across saves/loads.
    """
    random.seed(f"BOSS_{rung}_{seed}")
    return random.choice(BOSS_DEFINITIONS)


def create_boss_card(boss_def: BossDefinition, rung: int) -> Card:
    """Create a boss card with stats scaled for the given rung.
    
    Boss stats scale with rung to maintain challenge:
    - Power increases by 1 every 20 rungs
    - Health increases by 2 every 10 rungs
    """
    power_scaling = rung // 20
    health_scaling = (rung // 10) * 2
    
    return Card(
        name=boss_def.name,
        power=boss_def.base_power + power_scaling,
        health=boss_def.base_health + health_scaling,
        costs_fire=0,
        costs_spirits=0,
        has_fire=0,
        has_spirits=0,
        skills=boss_def.skills,
    )


def get_boss_names() -> List[str]:
    """Return all boss names for reference."""
    return [boss.name for boss in BOSS_DEFINITIONS]
