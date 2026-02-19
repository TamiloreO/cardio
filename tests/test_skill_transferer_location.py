from typing import Optional
from cardio import Card, CardList, Deck, skills
from cardio.locations.skill_transferer_location import (
    SkillTransfererLocation,
    SkillTransfererView,
)

message = ""


class FakeSkillTransfererView(SkillTransfererView):
    def __init__(self, *args, **kwargs) -> None:
        ...

    def pick_from(self, from_cards: CardList) -> Card:
        return from_cards[0]

    def pick_to(self, to_cards: CardList) -> Optional[Card]:
        return to_cards[0]

    def show_destroy(self, card: Card) -> None:
        ...

    def show_upgrade(self, card: Card) -> None:
        ...

    def close(self) -> None:
        ...

    def message(self, msg: str) -> None:
        global message
        message = msg

    def error(self, msg: str) -> None:
        self.message(msg)


def test_successfully_transfer_one_skill_destroying_the_from_card(tt_setup):
    human, *_ = tt_setup
    cards = [Card("From", 1, 1, 1, [skills.Spines]), Card("To", 1, 1, 1, None)]
    human.deck = Deck("main", cards)
    loc = SkillTransfererLocation("0", 0, 0, [])
    res = loc.handle(view_class=FakeSkillTransfererView, humanplayer=human)
    assert res == True
    assert human.deck.size() == 1
    assert human.deck.cards[0].name == "To"
    assert human.deck.cards[0].skills.get_types() == [skills.Spines]


def test_successfully_transfer_several_skills_not_destroying_the_from_card(tt_setup):
    human, *_ = tt_setup
    cards = [
        Card("From", 1, 1, 1, [skills.Spines, skills.Soaring]),
        Card("To", 1, 1, 1, None),
    ]
    human.deck = Deck("main", cards)
    loc = SkillTransfererLocation("0", 0, 0, [])
    res = loc.handle(view_class=FakeSkillTransfererView, humanplayer=human)
    assert res == True
    assert human.deck.size() == 2
    assert human.deck.cards[0].skills.get_types() == [skills.Soaring]
    assert human.deck.cards[1].skills.get_types() == [skills.Spines]
    # Note that the location will "randomly" pick always the same bc we're always using
    # the same seed in the location initialization above.


def test_deck_too_small(tt_setup):
    human, *_ = tt_setup
    cards = [Card("From", 1, 1, 1, None)]
    human.deck = Deck("main", cards)
    loc = SkillTransfererLocation("0", 0, 0, [])
    res = loc.handle(view_class=FakeSkillTransfererView, humanplayer=human)
    assert res == True
    assert "don't have enough cards" in message


def test_no_skilled_cards(tt_setup):
    human, *_ = tt_setup
    cards = [Card("From", 1, 1, 1, None), Card("To", 1, 1, 1, None)]
    human.deck = Deck("main", cards)
    loc = SkillTransfererLocation("0", 0, 0, [])
    res = loc.handle(view_class=FakeSkillTransfererView, humanplayer=human)
    assert res == True
    assert "don't have any cards with skills" in message


def test_no_cards_to_transfer_to(tt_setup):
    human, *_ = tt_setup
    cards = [
        Card("A", 1, 1, 1, [skills.Spines, skills.Fertility]),
        Card("B", 1, 1, 1, [skills.Spines, skills.Airdefense]),
        Card("C", 1, 1, 1, [skills.Spines, skills.Soaring]),
    ]
    human.deck = Deck("main", cards)
    loc = SkillTransfererLocation("0", 0, 0, [])
    res = loc.handle(view_class=FakeSkillTransfererView, humanplayer=human)
    assert res == True
    assert "no combination" in message


def test_escape_during_to_card_selection_allows_reselecting_from_card(tt_setup):
    """Test that pressing escape during to_card selection returns to from_card selection."""
    human, *_ = tt_setup
    from_card = Card("From", 1, 1, 1, [skills.Spines])
    to_card = Card("To", 1, 1, 1, None)
    cards = [from_card, to_card]
    human.deck = Deck("main", cards)

    # Track how many times pick_from and pick_to are called
    pick_from_calls = []
    pick_to_calls = []

    class EscapeTestView(FakeSkillTransfererView):
        def pick_from(self, from_cards: CardList) -> Card:
            pick_from_calls.append(list(from_cards))
            return from_cards[0]

        def pick_to(self, to_cards: CardList) -> Optional[Card]:
            pick_to_calls.append(list(to_cards))
            # First call simulates escape (returns None), second call returns the card
            return None if len(pick_to_calls) == 1 else to_cards[0]

    loc = SkillTransfererLocation("0", 0, 0, [])
    res = loc.handle(view_class=EscapeTestView, humanplayer=human)

    assert res == True
    # pick_from should have been called twice (once initially, once after escape)
    assert len(pick_from_calls) == 2
    # pick_to should have been called twice (first returned None, second returned card)
    assert len(pick_to_calls) == 2
    # From card only had one skill, so it should have been destroyed
    assert human.deck.size() == 1
    # The "To" card should now have the Spines skill
    assert to_card.skills.get_types() == [skills.Spines]
