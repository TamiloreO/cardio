"""Tests for skills.

These tests rely on the `_fc` attribute being present in the `Card` class in order to
access the `FightCard` instance that was created for the fight and to verify that the
card's attributes such as health have been update correctly.
"""

import random
from typing import Optional
import pytest
from cardio import Card, CardList, GridPos, skills, Grid
from cardio.computer_strategies import Round0OnlyStrategy
from cardio.fightcard import FightCard
from cardio.fightvnc import FightVnC
from cardio.human_player import HumanPlayer
from tests.utils.humanstrategyvnc import HumanStrategyVnC


def do_the_fight(humancards: CardList, computercard: Optional[Card]) -> FightVnC:
    """Note that the assumption here is that `HumanStrategyVnC` will place new cards on
    the first free slot from the left, i.e., the very first human card gets placed on
    (2,0).
    """
    grid = Grid(4)
    humanplayer = HumanPlayer(name="HP", lives=1)
    humanplayer.deck.cards = humancards
    cs = Round0OnlyStrategy(grid=grid, cards=[(GridPos(1, 0), computercard)])
    vnc = HumanStrategyVnC(
        grid=grid, computerstrategy=cs, whichrounds=[0], humanplayer=humanplayer
    )
    vnc.handle_fight()
    return vnc


def test_vanilla_fight():
    hc = Card("Human Card", 3, 10, 1)
    cc = Card("Computer Card", 2, 5, 1)
    vnc = do_the_fight([hc], cc)
    assert hc._fc.power == 3
    assert hc._fc.health == 8
    assert cc._fc.power == 2
    assert cc._fc.health == 0
    assert vnc.humanplayer.gems == 2
    assert vnc.grid[1][0] is None


def test_instant_death():
    hc = Card("Human Card", 1, 10, 1, skills=[skills.InstantDeath])
    cc = Card("Computer Card", 2, 3, 1)
    vnc = do_the_fight([hc], cc)
    assert hc._fc.health == 10
    assert cc._fc.health == 0
    assert vnc.grid[1][0] is None


def test_soaring():
    hc = Card("Human Card", 1, 20, 1, skills=[skills.Soaring])
    cc = Card("Computer Card", 2, 3, 1)
    vnc = do_the_fight([hc], cc)
    # 12 not 10, bc fight-over conditions are checked after each line gets activated:
    assert hc._fc.health == 12
    assert cc._fc.health == 3
    assert vnc.grid[1][0] is cc._fc


def test_soaring_vs_airdefense():
    hc = Card("Human Card", 1, 20, 1, skills=[skills.Soaring])
    cc = Card("Computer Card", 2, 3, 1, skills=[skills.Airdefense])
    vnc = do_the_fight([hc], cc)
    assert hc._fc.health == 16
    assert cc._fc.health == 0
    assert vnc.grid[1][0] is None


def test_soaring_and_instantdeath_vs_airdefense():
    hc = Card("Human Card", 1, 20, 1, skills=[skills.Soaring, skills.InstantDeath])
    cc = Card("Computer Card", 2, 3, 1, skills=[skills.Airdefense])
    vnc = do_the_fight([hc], cc)
    assert hc._fc.health == 20
    assert cc._fc.health == 0
    assert vnc.grid[1][0] is None


def test_soaring_and_instantdeath_vs_no_airdefense():
    """INSTANTDEATH should have no effect and computer card should not suffer any damage
    at all bc of SOARING.
    """
    hc = Card("Human Card", 1, 20, 1, skills=[skills.Soaring, skills.InstantDeath])
    cc = Card("Computer Card", 2, 3, 1)
    vnc = do_the_fight([hc], cc)
    # 12 not 10, bc fight-over conditions are checked after each line gets activated:
    assert hc._fc.health == 12
    assert cc._fc.health == 3
    assert vnc.grid[1][0] is cc._fc


def test_spines():
    hc = Card("Human Card", 2, 10, 1)
    cc = Card("Computer Card", 2, 3, 1, skills=[skills.Spines])
    vnc = do_the_fight([hc], cc)
    assert hc._fc.health == 6
    assert cc._fc.health == 0
    assert vnc.grid[1][0] is None


def test_spines_resulting_in_both_cards_dying_simultaneously():
    hc = Card("Human Card", 1, 1, 1)
    cc = Card("Computer Card", 0, 1, 1, skills=[skills.Spines])
    vnc = do_the_fight([hc], cc)
    assert hc._fc.health == 0
    assert cc._fc.health == 0
    assert vnc.grid[1][0] is None
    assert vnc.grid[2][0] is None
    assert vnc.humanplayer.lives == 1


def test_fertility():
    hc = Card("Human Card", 1, 1, 0, skills=[skills.Fertility])
    cc = Card("Computer Card", 1, 2, 1)
    vnc = do_the_fight([hc], cc)
    # The original card must be used:
    assert hc._fc in vnc.decks.used.cards
    assert hc._fc.health == 0
    # The copy should be in the hand deck:
    non_hamsters_on_hand = [c for c in vnc.decks.hand.cards if c.name != "Hamster"]
    assert len(non_hamsters_on_hand) == 1
    copy = non_hamsters_on_hand[0]
    assert isinstance(copy, FightCard)
    assert copy.name == "Human Card"
    assert copy.health == 1  # Make sure the health was reset
    assert copy.skills.get_types() == [skills.Fertility]
    # The copy should _not_ be in the player's main deck, since it is a temporary card:
    assert copy not in vnc.humanplayer.deck.cards


def test_shield():
    # With shield:
    # The human card will survive bc the shield absorbs 1 damage in each round.
    hc = Card("Human Card", 2, 4, 1, skills=[skills.Shield])
    cc = Card("Computer Card", 2, 7, 1)
    vnc = do_the_fight([hc], cc)
    assert hc._fc.health == 1
    assert cc._fc.health == 0
    assert vnc.grid[1][0] is None
    assert vnc.grid[2][0] is hc._fc
    assert hc._fc.skills.get(skills.Shield)._turns_used == [0, 1, 2]

    # Without shield:
    # The human card will die bc it no longer has the shield and therefore takes 2
    # damage per round.
    hc = Card("Human Card", 2, 4, 1)
    cc = Card("Computer Card", 2, 7, 1)
    vnc = do_the_fight([hc], cc)
    assert hc._fc.health == 0
    assert cc._fc.health == 3
    assert vnc.grid[1][0] is cc._fc
    assert vnc.grid[2][0] is None

    # With shield and spines:
    # The human card will die bc while the shield absorbs 1 damage in each round, the
    # spines deal another damage, which will not be absorbed.
    hc = Card("Human Card", 2, 4, 1, skills=[skills.Shield])
    cc = Card("Computer Card", 2, 7, 1, skills=[skills.Spines])
    vnc = do_the_fight([hc], cc)
    assert hc._fc.health == 0
    assert cc._fc.health == 3
    assert vnc.grid[1][0] is cc._fc
    assert vnc.grid[2][0] is None


def test_shield_resets_at_start_of_fight():
    hc = Card("Human Card", 2, 4, 1, skills=[skills.Shield])
    # With the following setting, the cc should win. But since _turns_used will be reset
    # to [] at the start of the fight, the hc will win:
    hc.skills.get(skills.Shield)._turns_used = [0, 1, 2, 3, 4, 5]
    cc = Card("Computer Card", 2, 7, 1)
    vnc = do_the_fight([hc], cc)
    assert hc._fc.health == 1
    assert cc._fc.health == 0
    assert vnc.grid[1][0] is None
    assert vnc.grid[2][0] is hc._fc
    assert hc._fc.skills.get(skills.Shield)._turns_used == [0, 1, 2]


def test_shield_deadlock():
    hc = Card("Procupine", 1, 2, 1, skills=[skills.Airdefense, skills.Shield])
    cc = hc.copy()
    vnc = do_the_fight([hc], cc)
    assert vnc.damagestate.is_deadlocked()


def test_underdog():
    # With Underdog:
    hc = Card("Human Card", 1, 1, 1, skills=[skills.Underdog])
    cc = Card("Computer Card", 2, 2, 1)
    do_the_fight([hc], cc)
    assert hc._fc.health == 1  # hc wins bc it gets +1 power from Underdog
    assert cc._fc.health == 0

    # Without Underdog:
    hc = Card("Human Card", 1, 1, 1)
    cc = Card("Computer Card", 2, 2, 1)
    do_the_fight([hc], cc)
    assert hc._fc.health == 0
    assert cc._fc.health == 1  # cc wins bc it has more power

    # With Underdog, but 0 power:
    hc = Card("Human Card", 0, 10, 1, skills=[skills.Underdog])
    cc = Card("Computer Card", 2, 2, 1)
    do_the_fight([hc], cc)
    assert hc._fc.health == 8  # hc will fight and win even though it has 0 power
    assert cc._fc.health == 0

    # Without Underdog, but 0 power:
    hc = Card("Human Card", 0, 10, 1)
    cc = Card("Computer Card", 2, 2, 1)
    do_the_fight([hc], cc)
    assert hc._fc.health == 0  # hc will not fight and therefore lose
    assert cc._fc.health == 2


def test_packrat():
    # With Packrat:
    hc = Card("Human Card", 1, 1, 1, skills=[skills.Packrat])
    xc = Card("X", 1, 1, 1)
    cc = Card("Computer Card", 1, 2, 1)
    # 3 cards will get drawn at the beginning of the fight:
    vnc = do_the_fight([hc, hc.copy(), hc.copy(), xc], cc)
    assert "Draw: Xp1h1" in vnc.stateslogger.log.split("Starting round")[1]
    # `xc` gets drawn ealier:
    assert "Draw: Xp1h1" not in vnc.stateslogger.log.split("Starting round")[2]

    # Without Packrat:
    hc = Card("Human Card", 1, 1, 1)
    xc = Card("X", 1, 1, 1)
    cc = Card("Computer Card", 1, 2, 1)
    vnc = do_the_fight([hc, hc.copy(), hc.copy(), xc], cc)
    assert "Draw: Xp1h1" in vnc.stateslogger.log.split("Starting round")[1]
    assert "Draw: Xp1h1" in vnc.stateslogger.log.split("Starting round")[2]
    # `xc` gets drawn one round later:
    assert "Draw: Xp1h1" not in vnc.stateslogger.log.split("Starting round")[3]


def test_luckystrike():
    # LuckyStrike gets unlucky and kills itself:
    random.seed(0)
    hc = Card("Human Card", 10, 10, 1, skills=[skills.LuckyStrike])
    cc = Card("Computer Card", 1, 1, 1)
    do_the_fight([hc], cc)
    assert hc._fc.health == 0  # `hc` should have died immediately

    # LuckyStrike gets lucky and kills the opponent:
    random.seed(1)
    hc = Card("Human Card", 1, 1, 1, skills=[skills.LuckyStrike])
    cc = Card("Computer Card", 10, 10, 1)
    do_the_fight([hc], cc)
    assert cc._fc.health == 0  # `cc` should have died immediately

    # LuckyStrike gets lucky, but no opposing card:
    # (Computer will be defeated immediately bc `hc` has 3 power, which will get
    # doubled, for a power of 6.)
    random.seed(1)
    hc = Card("Human Card", 3, 1, 1, skills=[skills.LuckyStrike])
    vnc = do_the_fight([hc], None)
    assert hc._fc.health == 1  # `hc` should have survived
    assert "-6 damage," in vnc.stateslogger.log.split("Starting round")[1]


def test_regenerate():
    hc = Card("Human Card", 1, 5, 1, skills=[skills.Regenerate])
    cc = Card("Computer Card", 2, 2, 1)
    do_the_fight([hc], cc)
    assert hc._fc.health == 5  # Back to full health (but not higher)
    assert cc._fc.health == 0


def test_used_card_does_not_regenerate():
    hc = Card("Human Card", 1, 1, 1, skills=[skills.Regenerate])
    cc = Card("Computer Card", 2, 2, 1)
    do_the_fight([hc], cc)
    assert hc._fc.health == 0  # Died, no regeneration


def test_weakness():
    # With Weakness -- hc dies:
    hc = Card("Human Card", 2, 2, 1, skills=[skills.Weakness])
    cc = Card("Computer Card", 2, 2, 1)
    do_the_fight([hc], cc)
    assert hc._fc.health == 0
    assert cc._fc.health == 1

    # Without Weakness -- cc dies:
    hc = Card("Human Card", 2, 2, 1)
    cc = Card("Computer Card", 2, 2, 1)
    do_the_fight([hc], cc)
    assert hc._fc.health == 2
    assert cc._fc.health == 0

def test_weakness_against_agent():
    hc = Card("Human Card", 10, 2, 1, skills=[skills.Weakness])
    vnc = do_the_fight([hc], None)
    assert vnc.damagestate.diff == -9


def test_poison():
    """Basic test: poison ticks 1 damage to the opposing card at the end of each turn.

    Round 0: hc attacks cc -> cc takes 1 normal damage (10 -> 9). cc attacks hc -> hc
    takes 1 normal damage (10 -> 9). End of round: cc gets poisoned and takes 1 poison
    DOT (9 -> 8).
    Round 1: hc attacks cc -> cc 8 -> 7; cc attacks hc -> hc 9 -> 8; poison DOT cc
    7 -> 6.
    Round 2: hc attacks cc -> cc 6 -> 5; cc attacks hc -> hc 8 -> 7; poison DOT cc
    5 -> 4.
    Round 3: hc attacks cc -> cc 4 -> 3; cc attacks hc -> hc 7 -> 6; poison DOT cc
    3 -> 2.
    Round 4: hc attacks cc -> cc 2 -> 1; cc attacks hc -> hc 6 -> 5; poison DOT cc
    1 -> 0. cc dies.
    Round 5: hc attacks agent directly for 1 damage (-1 diff).
    ...
    Round 9: hc attacks agent directly; diff now at -5. Human wins.
    => hc ends with 5 health, cc with 0.

    Compare that to the same scenario *without* poison: hc and cc trade 1 damage each
    round; since hc always strikes first, hc narrowly survives with 1 health. The
    difference (5 vs 1 remaining health) demonstrates the DOT effect of Poison.
    """
    # With Poison:
    hc = Card("Human Card", 1, 10, 1, skills=[skills.Poison])
    cc = Card("Computer Card", 1, 10, 1)
    vnc = do_the_fight([hc], cc)
    assert hc._fc.health == 5
    assert cc._fc.health == 0
    assert vnc.grid[1][0] is None
    assert vnc.grid[2][0] is hc._fc

    # Without Poison -- control group: hc barely survives with 1 health:
    hc = Card("Human Card", 1, 10, 1)
    cc = Card("Computer Card", 1, 10, 1)
    vnc = do_the_fight([hc], cc)
    assert hc._fc.health == 1
    assert cc._fc.health == 0


def test_poison_with_zero_power():
    """Poison ticks even if the carrier has 0 power and therefore never attacks.

    Each round: hc does not attack (0 power). cc attacks hc for 1 damage.
    End of round: cc gets poisoned (first round only, idempotent afterwards) and
    takes 1 poison DOT.

    After 3 rounds: cc 3 -> 0 (dies from poison). hc 10 -> 7.
    Then hc is alone on the grid with 0 power; fight runs until deadlock or until
    agent-damage threshold is met. With 0 power, hc never damages the agent, so the
    fight will deadlock (computer "wins" on deadlock). What's important for us here is
    the card healths, proving poison works with a 0-power carrier.
    """
    hc = Card("Human Card", 0, 10, 1, skills=[skills.Poison])
    cc = Card("Computer Card", 1, 3, 1)
    do_the_fight([hc], cc)
    assert cc._fc.health == 0  # Killed entirely by poison DOT
    assert hc._fc.health == 7  # Took 3 hits before cc died from poison


def test_poison_against_agent():
    """Poison has no effect when there is no opposing card (attacking the agent
    directly). It must not crash and must not apply poison to the agent.
    """
    hc = Card("Human Card", 3, 2, 1, skills=[skills.Poison])
    vnc = do_the_fight([hc], None)
    # hc hits agent for 3 each round. After 2 rounds diff is at -6, human wins with 1
    # overflow gem. Nothing poison-related should alter this:
    assert hc._fc.health == 2
    assert vnc.humanplayer.gems == 1
    # The internal poison target must remain None since there never was a target:
    assert hc._fc.skills.get(skills.Poison)._poisoned_target is None


def test_poison_cannot_be_applied_twice():
    """A card that is already poisoned cannot be poisoned again. The DOT must stay at
    exactly 1 damage per turn regardless of how often Poison *tries* to apply.
    """
    # Part 1: Integration test. 0-power on both sides => poison is the ONLY source of
    # damage. We verify cc loses exactly 1 hp per round (no stacking / double-ticking).
    # We use 5 hp for cc so it dies well before deadlock (which triggers after 10
    # rounds of no agent-damage change).
    hc = Card("Human Card", 0, 10, 1, skills=[skills.Poison])
    cc = Card("Computer Card", 0, 5, 1)
    vnc = do_the_fight([hc], cc)
    assert cc._fc.health == 0
    assert hc._fc.health == 10  # hc never took any damage
    # Round-by-round: cc must have lost EXACTLY 1 hp per round. If poison stacked
    # (applied anew each round), cc would lose 1, then 2, then 3... hp per round.
    log_rounds = vnc.stateslogger.log.split("Starting round")
    assert "Cp0h4" in log_rounds[2]  # after 1 tick
    assert "Cp0h3" in log_rounds[3]  # after 2 ticks
    assert "Cp0h2" in log_rounds[4]  # after 3 ticks
    assert "Cp0h1" in log_rounds[5]  # after 4 ticks

    # Part 2: Direct unit test on the skill class. Calling `_try_apply` twice on the
    # same target must be a no-op the second time.
    grid2 = Grid(4)
    humanplayer2 = HumanPlayer(name="HP2", lives=1)
    vnc2 = FightVnC(grid2, None, humanplayer2)
    FightCard.init_fight(vnc2, grid2)
    carrier = FightCard.from_card(Card("Carrier", 0, 5, 1, skills=[skills.Poison]))
    target = FightCard.from_card(Card("Target", 0, 5, 1))
    grid2[2][0] = carrier
    grid2[1][0] = target
    poison = carrier.skills.get(skills.Poison)
    poison.pre_fight(carrier)
    # First application -> target becomes poisoned:
    poison._try_apply(carrier)
    assert getattr(target, "_poisoned", False) is True
    assert poison._poisoned_target is target
    # Second application on already-poisoned target -> no-op:
    poison._try_apply(carrier)
    assert getattr(target, "_poisoned", False) is True  # still poisoned (not reset)
    assert poison._poisoned_target is target  # not changed

    # Part 3: A *different* Poison instance also cannot poison an already-poisoned
    # target. This covers the scenario of two Poison carriers facing the same target.
    other_poison = skills.Poison()
    other_poison.pre_fight(carrier)
    other_poison._try_apply(carrier)
    # The second Poison instance must not have "claimed" the target:
    assert other_poison._poisoned_target is None


def test_poison_ticks_across_multiple_turns():
    """Verify that poison status is correctly tracked and damage is applied across
    several turns. We inspect the fight round-by-round via the states logger.
    """
    hc = Card("Human Card", 0, 10, 1, skills=[skills.Poison])
    cc = Card("Computer Card", 0, 5, 1)
    vnc = do_the_fight([hc], cc)
    # Both have 0 power, so ALL damage to cc is poison DOT. cc starts at 5hp, loses 1
    # at the end of each round -> dies after 5 rounds.
    assert cc._fc.health == 0
    assert hc._fc.health == 10
    # Verify round-by-round health progression from the states log:
    log_rounds = vnc.stateslogger.log.split("Starting round")
    # Round 1 snapshot is taken at the *start* of round 1, so cc should have taken
    # exactly 1 poison tick by then (5 -> 4):
    assert "Cp0h4" in log_rounds[2]  # start of round 1
    assert "Cp0h3" in log_rounds[3]  # start of round 2
    assert "Cp0h2" in log_rounds[4]  # start of round 3
    assert "Cp0h1" in log_rounds[5]  # start of round 4


def test_poison_state_resets_at_start_of_fight():
    """Poison's tracked target must reset at the start of each fight so that stale
    targets from a previous fight don't get damaged.
    """
    hc = Card("Human Card", 2, 10, 1, skills=[skills.Poison])
    # Manually dirty the poison state as-if it was left over from a prior fight:
    hc.skills.get(skills.Poison)._poisoned_target = object()  # type: ignore
    cc = Card("Computer Card", 1, 4, 1)
    vnc = do_the_fight([hc], cc)
    # If pre_fight reset works, cc gets poisoned and the fight proceeds normally.
    # Round 0: cc 4->2 (attack) -> 2->1 (poison). hc 10->9.
    # Round 1: cc 1->0 (attack; dies). hc 9->9 (cc already dead).
    # => cc dead after round 1:
    assert cc._fc.health == 0
    assert hc._fc.health == 9
    # After the fight, the skill's tracked target should be cleared (since cc died):
    assert hc._fc.skills.get(skills.Poison)._poisoned_target is None


def test_poison_with_shield():
    """Shield absorbs 1 damage per turn. Poison deals 1 damage per turn. So a card with
    Shield opposing a 0-power Poison carrier should take 0 net damage from poison each
    turn (shield absorbs it).
    """
    hc = Card("Human Card", 0, 10, 1, skills=[skills.Poison])
    cc = Card("Computer Card", 0, 10, 1, skills=[skills.Shield])
    vnc = do_the_fight([hc], cc)
    # Neither card attacks (both 0 power). Poison ticks 1 each round; Shield absorbs 1
    # each round. cc should take 0 net damage. Fight will deadlock.
    assert cc._fc.health == 10
    assert hc._fc.health == 10
    assert vnc.damagestate.is_deadlocked()


def test_poison_can_be_added_as_upgrade():
    """Verify that Poison is a proper skill type picked up by `get_skilltypes()` and
    can therefore be added to a card via the upgrade mechanisms (skill lottery,
    skill transferer).
    """
    # Poison must appear in the global list of skill types:
    assert skills.Poison in skills.get_skilltypes()
    # And it must be addable to a card's SkillSet like any other skill:
    c = Card("Upgradable", 1, 1, 1)
    assert not c.skills.has(skills.Poison)
    c.skills.add(skills.Poison)
    assert c.skills.has(skills.Poison)
    assert skills.Poison in c.skills.get_types()
    # Adding it again must fail (no skill stacking):
    with pytest.raises(AssertionError):
        c.skills.add(skills.Poison)
