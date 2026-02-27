"""Boss card definitions.

Each boss has unique stats, skills, and thematic flavor.
"""
from typing import List
from cardio import Card
from cardio.boss_skills import Evasion, Rampage, SoulDrain, Enrage, Multiattack
from cardio.skills import Regenerate, Shield, InstantDeath


class BossCard(Card):
    """A boss card with enhanced abilities."""
    boss_title: str = ""
    boss_description: str = ""

    def __init__(self, *args, boss_title: str = "", boss_description: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        self.boss_title = boss_title
        self.boss_description = boss_description


def create_shadow_stalker(rung: int) -> BossCard:
    """The Shadow Stalker - An evasive assassin that strikes from the shadows."""
    base_health = 15 + (rung // 10) * 5
    base_power = 3 + (rung // 10) * 1
    return BossCard(
        name="Shadow Stalker",
        power=base_power,
        health=base_health,
        costs_fire=0,
        skills=[Evasion(), InstantDeath()],
        boss_title="The Unseen Death",
        boss_description="A master of evasion who delivers killing blows from unexpected angles.",
    )


def create_blood_tyrant(rung: int) -> BossCard:
    """The Blood Tyrant - A vampiric warlord that grows stronger with each kill."""
    base_health = 20 + (rung // 10) * 6
    base_power = 2 + (rung // 10) * 1
    return BossCard(
        name="Blood Tyrant",
        power=base_power,
        health=base_health,
        costs_fire=0,
        skills=[Rampage(), SoulDrain()],
        boss_title="Lord of Carnage",
        boss_description="Feeds on the essence of fallen enemies, growing ever more powerful.",
    )


def create_iron_colossus(rung: int) -> BossCard:
    """The Iron Colossus - An unstoppable juggernaut with massive health and defense."""
    base_health = 30 + (rung // 10) * 8
    base_power = 2 + (rung // 10) * 1
    return BossCard(
        name="Iron Colossus",
        power=base_power,
        health=base_health,
        costs_fire=0,
        skills=[Shield(), Regenerate()],
        boss_title="The Immovable",
        boss_description="An ancient war machine that shrugs off damage and repairs itself.",
    )


def create_berserker_chief(rung: int) -> BossCard:
    """The Berserker Chief - A rage-fueled warrior that becomes deadlier when hurt."""
    base_health = 18 + (rung // 10) * 5
    base_power = 3 + (rung // 10) * 1
    return BossCard(
        name="Berserker Chief",
        power=base_power,
        health=base_health,
        costs_fire=0,
        skills=[Enrage(), Regenerate()],
        boss_title="Fury Incarnate",
        boss_description="Pain only fuels the endless rage. Each wound makes this warrior stronger.",
    )


def create_storm_warden(rung: int) -> BossCard:
    """The Storm Warden - A devastating force that strikes multiple targets at once."""
    base_health = 16 + (rung // 10) * 4
    base_power = 2 + (rung // 10) * 1
    return BossCard(
        name="Storm Warden",
        power=base_power,
        health=base_health,
        costs_fire=0,
        skills=[Multiattack(), Shield()],
        boss_title="Herald of Thunder",
        boss_description="Commands lightning to strike all who stand before it.",
    )


BOSS_CREATORS = [
    create_shadow_stalker,
    create_blood_tyrant,
    create_iron_colossus,
    create_berserker_chief,
    create_storm_warden,
]


def get_random_boss(rung: int, seed: str) -> BossCard:
    """Get a random boss appropriate for the given rung."""
    import random
    random.seed(f"boss_{seed}_{rung}")
    creator = random.choice(BOSS_CREATORS)
    return creator(rung)


def get_all_boss_names() -> List[str]:
    """Return names of all bosses."""
    return [
        "Shadow Stalker",
        "Blood Tyrant", 
        "Iron Colossus",
        "Berserker Chief",
        "Storm Warden",
    ]
