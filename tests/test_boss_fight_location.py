"""Tests for boss fight location and boss mechanics."""
from cardio import Grid
from cardio.boss_cards import (
    BossCard,
    get_random_boss,
    create_shadow_stalker,
    create_blood_tyrant,
    create_iron_colossus,
    create_berserker_chief,
    create_storm_warden,
    BOSS_CREATORS,
)
from cardio.boss_skills import Evasion, Rampage, SoulDrain, Enrage, Multiattack
from cardio.boss_strategy import BossStrategy
from cardio.locations.boss_fight_location import BossFightLocation, is_boss_rung
from cardio.skills import InstantDeath, Shield, Regenerate


def test_is_boss_rung():
    assert is_boss_rung(10) == True
    assert is_boss_rung(20) == True
    assert is_boss_rung(30) == True
    assert is_boss_rung(100) == True
    
    assert is_boss_rung(0) == False
    assert is_boss_rung(1) == False
    assert is_boss_rung(5) == False
    assert is_boss_rung(9) == False
    assert is_boss_rung(11) == False
    assert is_boss_rung(15) == False


def test_boss_location_generate():
    loc = BossFightLocation("test_seed", 10, 0, [0])
    assert isinstance(loc.grid, Grid)
    assert isinstance(loc.computerstrategy, BossStrategy)
    assert isinstance(loc.boss, BossCard)
    assert loc.marker == "👹👹👹"


def test_boss_location_different_seeds_different_bosses():
    """Different seeds should potentially produce different bosses."""
    bosses = set()
    for i in range(10):
        loc = BossFightLocation(f"seed_{i}", 10, 0, [0])
        bosses.add(loc.boss.name)
    # With 5 bosses and 10 seeds, we should see variety
    assert len(bosses) > 1


def test_all_boss_creators():
    """Test that all boss creators produce valid bosses."""
    for creator in BOSS_CREATORS:
        boss = creator(10)
        assert isinstance(boss, BossCard)
        assert boss.power > 0
        assert boss.health > 0
        assert boss.boss_title != ""
        assert boss.boss_description != ""
        assert len(boss.skills.skills) >= 1


def test_shadow_stalker():
    boss = create_shadow_stalker(10)
    assert boss.name == "Shadow Stalker"
    assert boss.boss_title == "The Unseen Death"
    assert Evasion in boss.skills
    assert InstantDeath in boss.skills


def test_blood_tyrant():
    boss = create_blood_tyrant(10)
    assert boss.name == "Blood Tyrant"
    assert boss.boss_title == "Lord of Carnage"
    assert Rampage in boss.skills
    assert SoulDrain in boss.skills


def test_iron_colossus():
    boss = create_iron_colossus(10)
    assert boss.name == "Iron Colossus"
    assert boss.boss_title == "The Immovable"
    assert Shield in boss.skills
    assert Regenerate in boss.skills


def test_berserker_chief():
    boss = create_berserker_chief(10)
    assert boss.name == "Berserker Chief"
    assert boss.boss_title == "Fury Incarnate"
    assert Enrage in boss.skills
    assert Regenerate in boss.skills


def test_storm_warden():
    boss = create_storm_warden(10)
    assert boss.name == "Storm Warden"
    assert boss.boss_title == "Herald of Thunder"
    assert Multiattack in boss.skills
    assert Shield in boss.skills


def test_boss_scaling():
    """Test that bosses scale with rung level."""
    boss_10 = create_iron_colossus(10)
    boss_20 = create_iron_colossus(20)
    boss_30 = create_iron_colossus(30)
    
    # Power should increase
    assert boss_20.power > boss_10.power
    assert boss_30.power > boss_20.power
    
    # Health should increase
    assert boss_20.health > boss_10.health
    assert boss_30.health > boss_20.health


def test_boss_strategy_placement():
    """Test that boss strategy places the boss in the center."""
    boss = create_iron_colossus(10)
    grid = Grid(4)
    strategy = BossStrategy(boss, grid)
    
    cards = strategy.cards_to_be_played(0)
    assert len(cards) == 1
    pos, card = cards[0]
    assert pos.line == 1
    assert pos.slot == grid.width // 2  # Center slot


def test_boss_strategy_no_additional_cards():
    """Test that boss strategy only plays the boss and no additional cards."""
    boss = create_iron_colossus(10)
    grid = Grid(4)
    strategy = BossStrategy(boss, grid)
    
    # Round 0 has the boss
    assert len(strategy.cards_to_be_played(0)) == 1
    
    # Later rounds have no new cards
    for round_num in [1, 2, 3, 5, 10]:
        assert len(strategy.cards_to_be_played(round_num)) == 0


def test_evasion_skill():
    """Test the Evasion skill mechanics."""
    evasion = Evasion()
    
    # Should track rounds properly
    assert evasion._last_evade_round == -1
    
    # pre_fight should reset state
    evasion._last_evade_round = 5
    evasion.pre_fight(None)
    assert evasion._last_evade_round == -1


def test_rampage_skill():
    """Test the Rampage skill mechanics."""
    rampage = Rampage()
    
    assert rampage._kills == 0
    rampage.pre_fight(None)
    assert rampage._kills == 0


def test_enrage_skill():
    """Test the Enrage skill mechanics."""
    enrage = Enrage()
    
    assert enrage._rage_stacks == 0
    enrage.pre_fight(None)
    assert enrage._rage_stacks == 0


def test_soul_drain_skill():
    """Test the SoulDrain skill calculation."""
    soul_drain = SoulDrain()
    
    # Create a mock carrier with health
    class MockCard:
        def __init__(self):
            self.health = 10
            self.name = "Mock"
        def heal_damage(self, amount):
            self.health = min(self.health + amount, 20)
    
    carrier = MockCard()
    
    # Test heal calculation
    healed = soul_drain.heal_from_damage(carrier, 6)
    assert healed == 3  # 6 // 2 = 3
    assert carrier.health == 13
    
    healed = soul_drain.heal_from_damage(carrier, 1)
    assert healed == 0  # 1 // 2 = 0


def test_multiattack_targets():
    """Test the Multiattack skill target calculation."""
    from cardio import FightCard, GridPos
    from cardio.fightvnc import FightVnC
    from cardio.human_player import HumanPlayer
    
    multiattack = Multiattack()
    
    grid = Grid(4)
    humanplayer = HumanPlayer(name="Test")
    from cardio.computer_strategies import Round0OnlyStrategy
    strategy = Round0OnlyStrategy(grid=grid, cards=[])
    vnc = FightVnC(grid=grid, computerstrategy=strategy, humanplayer=humanplayer)
    FightCard.init_fight(vnc, grid)
    
    # Create a card and place it
    boss = create_storm_warden(10)
    fc = FightCard.from_card(boss)
    
    # Place in slot 1 (middle-ish)
    grid.set_card(GridPos(1, 1), fc)
    
    extra_targets = multiattack.get_extra_targets(fc)
    assert 0 in extra_targets  # Left
    assert 2 in extra_targets  # Right
    
    # Place in slot 0 (edge)
    grid.clear_position(GridPos(1, 1))
    grid.set_card(GridPos(1, 0), fc)
    
    extra_targets = multiattack.get_extra_targets(fc)
    assert 0 not in extra_targets  # No left
    assert 1 in extra_targets  # Only right


def test_get_all_boss_names():
    """Test helper function returns all boss names."""
    from cardio.boss_cards import get_all_boss_names
    
    names = get_all_boss_names()
    assert len(names) == 5
    assert "Shadow Stalker" in names
    assert "Blood Tyrant" in names
    assert "Iron Colossus" in names
    assert "Berserker Chief" in names
    assert "Storm Warden" in names
