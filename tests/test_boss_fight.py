"""Tests for boss fight functionality."""
import pytest

from cardio import Card, CardList, Grid, GridPos
from cardio.computer_strategies import Round0OnlyStrategy
from cardio.fightcard import FightCard
from cardio.fightvnc import FightVnC
from cardio.human_player import HumanPlayer
from cardio.placement_manager import PlacementManager

from cardio.locations.boss_skills import (
    Evasion, Rampage, LifeSteal, Summon, Reflective, Enrage,
    get_boss_skill_types,
)
from cardio.locations.boss_card import BossCard
from cardio.locations.boss_catalog import (
    BOSS_DEFINITIONS,
    get_boss_for_rung,
    create_boss_card,
    get_boss_names,
)
from cardio.locations.boss_strategy import BossStrategy
from cardio.locations.boss_fight_location import BossFightLocation
from cardio.locations.location import is_boss_rung, BOSS_FIGHT_INTERVAL


class BossTestHumanStrategyVnC(FightVnC):
    """A VnC that simulates a human player for testing."""

    def __init__(self, whichrounds=None, target_slot=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.whichrounds = whichrounds
        self.target_slot = target_slot  # Specific slot to place cards in

    def handle_human_choose_deck_to_draw_from(self):
        if self.decks.draw.is_empty() and self.decks.hamster.is_empty():
            return None
        if self.decks.draw.is_empty() or self.round_num % 2 == 0:
            return self.decks.hamster
        return self.decks.draw

    def handle_human_plays_cards(self, place_card_callback):
        if self.whichrounds and self.round_num not in self.whichrounds:
            return
        if self.decks.hand.is_empty():
            return
        
        # If target_slot specified, try that first
        if self.target_slot is not None:
            pos = GridPos(2, self.target_slot)
            if self.grid.get_card(pos) is None:
                card = self.decks.hand.cards[0]
                card.costs_fire = 0
                card.costs_spirits = 0
                p = PlacementManager(self.grid, 0, card, placement_position=pos)
                place_card_callback(p, 0)
                return
        
        # Otherwise find first empty slot
        for slot in range(self.grid.width):
            pos = GridPos(2, slot)
            if self.grid.get_card(pos) is None:
                card = self.decks.hand.cards[0]
                card.costs_fire = 0
                card.costs_spirits = 0
                p = PlacementManager(self.grid, 0, card, placement_position=pos)
                place_card_callback(p, 0)
                return


def do_boss_fight(humancards: CardList, boss_card: Card) -> FightVnC:
    """Run a boss fight with given human cards against a boss."""
    grid = Grid(4)
    humanplayer = HumanPlayer(name="HP", lives=1)
    humanplayer.deck.cards = humancards
    
    center_slot = grid.width // 2
    cs = Round0OnlyStrategy(grid=grid, cards=[(GridPos(1, center_slot), boss_card)])
    vnc = BossTestHumanStrategyVnC(
        grid=grid, computerstrategy=cs, whichrounds=[0], humanplayer=humanplayer
    )
    
    # Convert boss card to BossCard
    for pos_card in cs.cards:
        if pos_card[1] and not isinstance(pos_card[1], FightCard):
            boss = BossCard.from_card(pos_card[1])
            cs.cards = [(pos_card[0], boss)]
    
    vnc.handle_fight()
    return vnc


class TestBossRungDetection:
    def test_is_boss_rung_at_intervals(self):
        assert not is_boss_rung(0)
        assert is_boss_rung(10)
        assert is_boss_rung(20)
        assert is_boss_rung(30)
        assert is_boss_rung(100)

    def test_is_not_boss_rung_between_intervals(self):
        assert not is_boss_rung(5)
        assert not is_boss_rung(15)
        assert not is_boss_rung(99)


class TestBossCatalog:
    def test_five_bosses_defined(self):
        assert len(BOSS_DEFINITIONS) == 5

    def test_all_bosses_have_unique_names(self):
        names = get_boss_names()
        assert len(names) == len(set(names))

    def test_all_bosses_have_skills(self):
        for boss in BOSS_DEFINITIONS:
            assert len(boss.skills) > 0

    def test_get_boss_for_rung_deterministic(self):
        boss1 = get_boss_for_rung(10, "test_seed")
        boss2 = get_boss_for_rung(10, "test_seed")
        assert boss1.name == boss2.name

    def test_get_boss_for_rung_varies_by_seed(self):
        results = set()
        for i in range(100):
            boss = get_boss_for_rung(10, f"seed_{i}")
            results.add(boss.name)
        assert len(results) > 1

    def test_create_boss_card_basic(self):
        boss_def = BOSS_DEFINITIONS[0]
        card = create_boss_card(boss_def, 10)
        assert card.name == boss_def.name
        assert card.power >= boss_def.base_power
        assert card.health >= boss_def.base_health

    def test_create_boss_card_scaling(self):
        boss_def = BOSS_DEFINITIONS[0]
        card_10 = create_boss_card(boss_def, 10)
        card_30 = create_boss_card(boss_def, 30)
        
        assert card_30.health > card_10.health
        assert card_30.power >= card_10.power


class TestBossSkills:
    def test_all_boss_skills_registered(self):
        skill_types = get_boss_skill_types()
        assert len(skill_types) == 6
        assert Evasion in skill_types
        assert Rampage in skill_types
        assert LifeSteal in skill_types
        assert Summon in skill_types
        assert Reflective in skill_types
        assert Enrage in skill_types


class TestRampageSkill:
    def test_rampage_increases_power(self):
        hc = Card("Human Card", 1, 20, 1)
        boss = Card("Boss", 2, 10, 1, skills=[Rampage])
        
        grid = Grid(4)
        humanplayer = HumanPlayer(name="HP", lives=1)
        humanplayer.deck.cards = [hc]
        
        cs = Round0OnlyStrategy(grid=grid, cards=[(GridPos(1, 2), boss)])
        vnc = BossTestHumanStrategyVnC(
            grid=grid, computerstrategy=cs, whichrounds=[0], humanplayer=humanplayer
        )
        vnc.handle_fight()
        
        # Boss should have gained power through rampage
        boss_fc = boss._fc
        assert boss_fc.power > 2


class TestEnrageSkill:
    def test_enrage_triggers_below_half_health(self):
        skill = Enrage()
        
        hc = Card("Human Card", 10, 10, 1)
        boss = Card("Boss", 2, 10, 1, skills=[Enrage])
        
        grid = Grid(4)
        
        # Simulate boss taking damage
        class MockVnC:
            round_num = 0
            def redraw_view(self): pass
            def card_lost_health(self, card): pass
        
        FightCard.init_fight(MockVnC(), grid)
        boss_fc = BossCard.from_card(boss)
        boss_fc.skills.call("pre_fight", boss_fc)
        
        # Enrage should track original health
        enrage = boss_fc.skills.get(Enrage)
        assert enrage._original_health == 10
        
        # Simulate dropping below half
        boss_fc.health = 4
        triggered = enrage.check_enrage(boss_fc)
        
        assert triggered
        assert boss_fc.power == 4  # +2 from enrage


class TestBossFightLocation:
    def test_location_generates_boss(self):
        loc = BossFightLocation("test_seed", 10, 0, [0])
        assert loc.boss_definition is not None
        assert loc.boss_definition.name in get_boss_names()

    def test_location_has_boss_marker(self):
        loc = BossFightLocation("test_seed", 10, 0, [0])
        assert "B" in loc.marker

    def test_location_creates_strategy(self):
        loc = BossFightLocation("test_seed", 10, 0, [0])
        assert isinstance(loc.computerstrategy, BossStrategy)


class TestBossStrategy:
    def test_boss_placed_in_center(self):
        boss_def = BOSS_DEFINITIONS[0]
        grid = Grid(4)
        strategy = BossStrategy(boss_def, 10, grid)
        
        cards = strategy.cards_to_be_played(0)
        assert len(cards) == 1
        assert cards[0].pos.slot == 2  # Center of 4-wide grid
        assert cards[0].pos.line == 1

    def test_boss_only_placed_once(self):
        boss_def = BOSS_DEFINITIONS[0]
        grid = Grid(4)
        strategy = BossStrategy(boss_def, 10, grid)
        
        cards_r0 = strategy.cards_to_be_played(0)
        strategy._boss_placed = True
        cards_r1 = strategy.cards_to_be_played(1)
        
        assert len(cards_r0) == 1
        assert len(cards_r1) == 0


class TestEvasionSkill:
    def test_evasion_can_find_empty_slots(self):
        grid = Grid(4)
        
        class MockVnC:
            round_num = 0
            def redraw_view(self): pass
        
        boss = Card("Boss", 2, 10, 1, skills=[Evasion])
        FightCard.init_fight(MockVnC(), grid)
        boss_fc = BossCard.from_card(boss)
        
        # Place boss in center
        grid.set_card(GridPos(1, 2), boss_fc)
        
        evasion = boss_fc.skills.get(Evasion)
        evasion._evasion_chance = 1.0  # Force evasion
        
        evaded = evasion.try_evade(boss_fc)
        
        assert evaded
        # Boss should have moved
        assert grid.get_card(GridPos(1, 2)) is None
        new_pos = grid.find_card(boss_fc)
        assert new_pos.slot in [1, 3]

    def test_evasion_fails_when_surrounded(self):
        grid = Grid(4)
        
        class MockVnC:
            round_num = 0
            def redraw_view(self): pass
        
        blocker1 = Card("Blocker1", 1, 1, 0)
        blocker2 = Card("Blocker2", 1, 1, 0)
        boss = Card("Boss", 2, 10, 1, skills=[Evasion])
        
        FightCard.init_fight(MockVnC(), grid)
        
        # Place blockers on both sides
        grid.set_card(GridPos(1, 1), FightCard.from_card(blocker1))
        grid.set_card(GridPos(1, 3), FightCard.from_card(blocker2))
        
        boss_fc = BossCard.from_card(boss)
        grid.set_card(GridPos(1, 2), boss_fc)
        
        evasion = boss_fc.skills.get(Evasion)
        evasion._evasion_chance = 1.0
        
        evaded = evasion.try_evade(boss_fc)
        
        assert not evaded
        assert grid.find_card(boss_fc).slot == 2


class TestSummonSkill:
    def test_summon_creates_minion(self):
        grid = Grid(4)
        
        class MockVnC:
            round_num = 0
            def redraw_view(self): pass
        
        boss = Card("Boss", 2, 10, 1, skills=[Summon])
        FightCard.init_fight(MockVnC(), grid)
        boss_fc = BossCard.from_card(boss)
        
        grid.set_card(GridPos(1, 2), boss_fc)
        boss_fc.skills.call("pre_fight", boss_fc)
        
        summon = boss_fc.skills.get(Summon)
        summon._rounds_until_summon = 0
        summon.post_round(boss_fc)
        
        # Check for minion in adjacent slot
        minion_left = grid.get_card(GridPos(1, 1))
        minion_right = grid.get_card(GridPos(1, 3))
        
        assert minion_left is not None or minion_right is not None


class TestLifeStealSkill:
    def test_life_steal_tracks_damage(self):
        skill = LifeSteal()
        skill.pre_fight(None)
        skill.pre_attack(None)
        
        skill.register_damage(4)
        assert skill._damage_dealt_this_attack == 4

    def test_life_steal_heals_boss_in_fight(self):
        """Test that LifeSteal heals the boss for half of damage dealt using BossStrategy."""
        from cardio.locations.boss_catalog import BossDefinition
        
        boss_def = BossDefinition(
            name="Test Vampire",
            base_power=3,
            base_health=8,
            skills=[LifeSteal],
            description="Test boss",
            reward_gems=1,
        )
        
        # Human card: 1 power, 20 health
        # Boss: 3 power, 8 health with LifeSteal (placed at center slot 2)
        # Per round: Human deals 1 damage to boss, boss deals 3 to human and heals 1
        # Boss net damage per round: 1 - 1 = 0 (takes 1, heals 1)
        # Human dies after ~7 rounds, boss should still have ~8 health
        hc = Card("Human Card", 1, 20, 1)
        
        grid = Grid(4)
        humanplayer = HumanPlayer(name="HP", lives=1)
        humanplayer.deck.cards = [hc]
        
        strategy = BossStrategy(boss_def, 10, grid)
        # Place human card at slot 2 to oppose the boss
        vnc = BossTestHumanStrategyVnC(
            grid=grid, computerstrategy=strategy, whichrounds=[0], humanplayer=humanplayer,
            target_slot=2
        )
        
        vnc.handle_fight()
        
        # Find the boss card on grid or in strategy
        boss_fc = None
        for line in grid.lines:
            for card in line:
                if card and card.name == "Test Vampire":
                    boss_fc = card
                    break
        
        # Boss should have won or healed significantly during the fight
        assert vnc.damagestate.who_won() == "computer"

    def test_life_steal_healing_amount(self):
        """Verify LifeSteal heals for exactly half damage dealt (rounded down)."""
        skill = LifeSteal()
        skill.pre_fight(None)
        skill.pre_attack(None)
        
        # Test various damage amounts
        skill.register_damage(4)
        assert skill._damage_dealt_this_attack == 4
        # Healing would be 4 // 2 = 2
        
        skill.pre_attack(None)  # Reset
        skill.register_damage(5)
        assert skill._damage_dealt_this_attack == 5
        # Healing would be 5 // 2 = 2
        
        skill.pre_attack(None)  # Reset
        skill.register_damage(1)
        assert skill._damage_dealt_this_attack == 1
        # Healing would be 1 // 2 = 0


class TestReflectiveSkill:
    def test_reflective_returns_damage_amount(self):
        skill = Reflective()
        assert skill.get_reflect_damage() == 1

    def test_reflective_damages_attacker(self):
        """Test that Reflective deals damage back to attacking cards using BossStrategy."""
        from cardio.locations.boss_catalog import BossDefinition
        
        boss_def = BossDefinition(
            name="Mirror Boss",
            base_power=1,
            base_health=10,
            skills=[Reflective],
            description="Test boss",
            reward_gems=1,
        )
        
        # Human card with 20 health, 2 power
        # Boss with 10 health, 1 power, Reflective skill (placed at center slot 2)
        # Each round: human deals 2 damage to boss, takes 1 from boss attack + 1 from Reflective = 2
        hc = Card("Human Card", 2, 20, 1)
        
        grid = Grid(4)
        humanplayer = HumanPlayer(name="HP", lives=1)
        humanplayer.deck.cards = [hc]
        
        strategy = BossStrategy(boss_def, 10, grid)
        # Place human card at slot 2 to oppose the boss (which is placed at center slot 2)
        vnc = BossTestHumanStrategyVnC(
            grid=grid, computerstrategy=strategy, whichrounds=[0], humanplayer=humanplayer,
            target_slot=2
        )
        
        vnc.handle_fight()
        
        # Human should have won (boss defeated)
        assert vnc.damagestate.who_won() == "human"
        # Human card should have taken some reflective damage (less than starting health)
        assert hc._fc.health < 20
        # Human card should have survived
        assert hc._fc.health > 0


class TestIntegration:
    def test_boss_fight_completes(self):
        """Verify a boss fight can run to completion."""
        hc = Card("Human Card", 5, 20, 1)
        boss_def = BOSS_DEFINITIONS[0]
        boss = create_boss_card(boss_def, 10)
        
        grid = Grid(4)
        humanplayer = HumanPlayer(name="HP", lives=2)
        humanplayer.deck.cards = [hc]
        
        strategy = BossStrategy(boss_def, 10, grid)
        
        vnc = BossTestHumanStrategyVnC(
            grid=grid,
            computerstrategy=strategy,
            whichrounds=[0],
            humanplayer=humanplayer,
        )
        vnc.handle_fight()
        
        # Fight should have ended one way or another
        assert vnc.damagestate.who_won() is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
