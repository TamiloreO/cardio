from cardio import Card, CardList, Deck, skills
from cardio.locations.poison_shop_location import (
    PoisonShopLocation,
    PoisonShopView,
)

message = ""


class FakePoisonShopView(PoisonShopView):
    def __init__(self, *args, **kwargs) -> None:
        ...

    def pick(self, activecards: CardList) -> Card:
        return activecards[0]

    def show_upgrade(self, card: Card) -> None:
        ...

    def close(self) -> None:
        ...

    def message(self, msg: str) -> None:
        global message
        message = msg

    def error(self, msg: str) -> None:
        self.message(msg)


def test_add_poison_to_plain_card(tt_setup):
    """A card with no skills should successfully receive the Poison skill."""
    human, *_ = tt_setup
    card = Card("Plain", 1, 1, 1, None)
    human.deck = Deck("main", [card])
    loc = PoisonShopLocation("0", 0, 0, [])
    res = loc.handle(view_class=FakePoisonShopView, humanplayer=human)
    assert res is True
    assert card.skills.has(skills.Poison)
    assert card.skills.count() == 1
    assert "Poison" in message and "🐍" in message


def test_add_poison_to_card_with_other_skills(tt_setup):
    """A card that already has other (non-Poison) skills still gets Poison added."""
    human, *_ = tt_setup
    card = Card("Spiky", 1, 1, 1, [skills.Spines, skills.Shield])
    human.deck = Deck("main", [card])
    loc = PoisonShopLocation("0", 0, 0, [])
    res = loc.handle(view_class=FakePoisonShopView, humanplayer=human)
    assert res is True
    assert card.skills.has(skills.Poison)
    assert card.skills.has(skills.Spines)  # existing skill untouched
    assert card.skills.has(skills.Shield)  # existing skill untouched
    assert card.skills.count() == 3


def test_cannot_add_poison_twice(tt_setup):
    """If every card in the deck already has Poison, the location refuses."""
    human, *_ = tt_setup
    card = Card("Already Venomous", 1, 1, 1, [skills.Poison])
    human.deck = Deck("main", [card])
    loc = PoisonShopLocation("0", 0, 0, [])
    res = loc.handle(view_class=FakePoisonShopView, humanplayer=human)
    assert res is True  # location always returns True (run continues)
    # Still has exactly one Poison skill — no stacking:
    assert card.skills.get_types() == [skills.Poison]
    assert card.skills.count() == 1
    assert "none of your cards can be coated" in message.lower()


def test_already_poisoned_card_excluded_from_pick_list(tt_setup):
    """Cards that already have Poison are filtered out of the pick list; the
    non-poisoned card gets upgraded instead.
    """
    human, *_ = tt_setup
    already_poisoned = Card("Snake", 1, 1, 1, [skills.Poison])
    plain = Card("Plain", 1, 1, 1, None)
    human.deck = Deck("main", [already_poisoned, plain])
    loc = PoisonShopLocation("0", 0, 0, [])
    res = loc.handle(view_class=FakePoisonShopView, humanplayer=human)
    assert res is True
    # The fake view picks activecards[0]. Since `already_poisoned` is filtered out,
    # `plain` must be the one that got upgraded:
    assert plain.skills.has(skills.Poison)
    # And the already-poisoned card is untouched:
    assert already_poisoned.skills.get_types() == [skills.Poison]


def test_card_at_skill_cap_excluded(tt_setup):
    """Cards at the skill cap are filtered out of the pick list."""
    human, *_ = tt_setup
    full_skills = [
        skills.Spines,
        skills.Shield,
        skills.Soaring,
        skills.Airdefense,
        skills.Regenerate,
        skills.Underdog,
    ]
    assert len(full_skills) == Card.MAX_SKILLS
    maxed = Card("Maxed", 1, 1, 1, full_skills)
    plain = Card("Plain", 1, 1, 1, None)
    human.deck = Deck("main", [maxed, plain])
    loc = PoisonShopLocation("0", 0, 0, [])
    res = loc.handle(view_class=FakePoisonShopView, humanplayer=human)
    assert res is True
    # Maxed card was filtered out, so Plain got the upgrade:
    assert plain.skills.has(skills.Poison)
    assert not maxed.skills.has(skills.Poison)
    assert maxed.skills.count() == Card.MAX_SKILLS


def test_no_eligible_cards_at_all(tt_setup):
    """Mix of maxed-out and already-poisoned cards → error, no upgrade."""
    human, *_ = tt_setup
    full_skills = [
        skills.Spines,
        skills.Shield,
        skills.Soaring,
        skills.Airdefense,
        skills.Regenerate,
        skills.Underdog,
    ]
    assert len(full_skills) == Card.MAX_SKILLS
    maxed = Card("Maxed", 1, 1, 1, full_skills)
    venomous = Card("Venomous", 1, 1, 1, [skills.Poison])
    human.deck = Deck("main", [maxed, venomous])
    loc = PoisonShopLocation("0", 0, 0, [])
    res = loc.handle(view_class=FakePoisonShopView, humanplayer=human)
    assert res is True
    assert "none of your cards can be coated" in message.lower()
    # Nothing changed:
    assert not maxed.skills.has(skills.Poison)
    assert venomous.skills.get_types() == [skills.Poison]


def test_upgrade_persists_and_works_in_fight(tt_setup):
    """After upgrading at the PoisonShop, the card actually poisons opponents in
    fights (end-to-end: location upgrade -> fight DOT behaviour).
    """
    human, *_ = tt_setup
    card = Card("Viper", 0, 10, 1, None)
    human.deck = Deck("main", [card])
    loc = PoisonShopLocation("0", 0, 0, [])
    loc.handle(view_class=FakePoisonShopView, humanplayer=human)
    assert card.skills.has(skills.Poison)

    # Now use this upgraded card in a fight. Reusing the same helper pattern as
    # test_skills.do_the_fight so we don't import a private helper across modules:
    from cardio import Grid, GridPos
    from cardio.computer_strategies import Round0OnlyStrategy
    from cardio.human_player import HumanPlayer
    from tests.utils.humanstrategyvnc import HumanStrategyVnC

    grid = Grid(4)
    fight_human = HumanPlayer(name="HP", lives=1)
    fight_human.deck.cards = [card]  # the upgraded card
    cc = Card("Victim", 0, 3, 1)
    cs = Round0OnlyStrategy(grid=grid, cards=[(GridPos(1, 0), cc)])
    vnc = HumanStrategyVnC(
        grid=grid, computerstrategy=cs, whichrounds=[0], humanplayer=fight_human
    )
    vnc.handle_fight()

    # Both cards have 0 power, so ALL damage to cc is poison DOT. cc starts at 3hp,
    # takes 1 poison tick per round -> dies after 3 rounds:
    assert cc._fc.health == 0
    assert card._fc.health == 10
