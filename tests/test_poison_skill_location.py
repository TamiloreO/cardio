from cardio import Card, CardList, Deck, skills
from cardio.locations.poison_skill_location import (
    PoisonSkillLocation,
    PoisonSkillView,
)


message = ""
error_message = ""


class FakePoisonSkillView(PoisonSkillView):
    """Fake view that always picks the first eligible card handed to it."""

    def __init__(self, *args, **kwargs) -> None:
        ...

    def pick(self, activecards: CardList) -> Card:
        # Always pick the first eligible card. The location filters the list for us,
        # so we know every card in `activecards` is a valid target.
        return activecards[0]

    def show_upgrade(self, card: Card) -> None:
        ...

    def close(self) -> None:
        ...

    def message(self, msg: str) -> None:
        global message
        message = msg

    def error(self, msg: str) -> None:
        global error_message
        error_message = msg


def _reset_messages():
    global message, error_message
    message = ""
    error_message = ""


def test_adds_poison_to_card_without_skills(tt_setup):
    """Basic happy path: a card with no skills receives Poison."""
    _reset_messages()
    human, *_ = tt_setup
    card = Card("Plain", 1, 1, 1, None)
    human.deck = Deck("main", [card])
    loc = PoisonSkillLocation("0", 0, 0, [])
    res = loc.handle(view_class=FakePoisonSkillView, humanplayer=human)
    assert res is True
    assert card.skills.has(skills.Poison)
    assert card.skills.count() == 1
    assert "Poison" in message
    assert error_message == ""


def test_adds_poison_to_card_with_other_skills(tt_setup):
    """A card that already has other (non-Poison) skills can still receive Poison,
    as long as it has a free skill slot."""
    _reset_messages()
    human, *_ = tt_setup
    card = Card("Spiky", 1, 1, 1, [skills.Spines, skills.Shield])
    human.deck = Deck("main", [card])
    loc = PoisonSkillLocation("0", 0, 0, [])
    res = loc.handle(view_class=FakePoisonSkillView, humanplayer=human)
    assert res is True
    assert card.skills.has(skills.Poison)
    assert card.skills.has(skills.Spines)  # existing skills are preserved
    assert card.skills.has(skills.Shield)
    assert card.skills.count() == 3


def test_skips_card_that_already_has_poison(tt_setup):
    """A card that already has Poison is NOT eligible — the location picks the next
    eligible card instead. This mirrors the in-fight "cannot poison twice" invariant.
    """
    _reset_messages()
    human, *_ = tt_setup
    already_poisoned = Card("AlreadyPoisoned", 1, 1, 1, [skills.Poison])
    fresh = Card("Fresh", 1, 1, 1, None)
    human.deck = Deck("main", [already_poisoned, fresh])
    loc = PoisonSkillLocation("0", 0, 0, [])
    res = loc.handle(view_class=FakePoisonSkillView, humanplayer=human)
    assert res is True
    # The already-poisoned card must NOT have been touched (still exactly 1 Poison):
    assert already_poisoned.skills.count() == 1
    assert already_poisoned.skills.has(skills.Poison)
    # The fresh card must have received Poison:
    assert fresh.skills.has(skills.Poison)


def test_skips_card_at_max_skills(tt_setup):
    """A card at `Card.MAX_SKILLS` (with no free slot) is not eligible. The location
    picks the next eligible card instead."""
    _reset_messages()
    human, *_ = tt_setup
    # Build a card with MAX_SKILLS distinct non-Poison skills:
    all_skills = [
        s for s in skills.get_skilltypes() if s is not skills.Poison
    ][: Card.MAX_SKILLS]
    assert len(all_skills) == Card.MAX_SKILLS  # sanity check
    full_card = Card("Full", 1, 1, 1, all_skills)
    fresh = Card("Fresh", 1, 1, 1, None)
    human.deck = Deck("main", [full_card, fresh])
    loc = PoisonSkillLocation("0", 0, 0, [])
    res = loc.handle(view_class=FakePoisonSkillView, humanplayer=human)
    assert res is True
    # The full card must NOT have been touched:
    assert full_card.skills.count() == Card.MAX_SKILLS
    assert not full_card.skills.has(skills.Poison)
    # The fresh card must have received Poison:
    assert fresh.skills.has(skills.Poison)


def test_error_when_all_cards_already_have_poison(tt_setup):
    """If every card in the deck already has Poison, show an error and no-op."""
    _reset_messages()
    human, *_ = tt_setup
    cards = [
        Card("A", 1, 1, 1, [skills.Poison]),
        Card("B", 1, 1, 1, [skills.Poison, skills.Spines]),
    ]
    human.deck = Deck("main", cards)
    loc = PoisonSkillLocation("0", 0, 0, [])
    res = loc.handle(view_class=FakePoisonSkillView, humanplayer=human)
    assert res is True  # run continues
    assert "none of your cards can receive the Poison skill" in error_message
    # Nothing was changed:
    assert cards[0].skills.count() == 1
    assert cards[1].skills.count() == 2


def test_error_when_no_eligible_cards_at_all(tt_setup):
    """If the deck has only ineligible cards (all at MAX_SKILLS with non-Poison skills),
    show an error and no-op."""
    _reset_messages()
    human, *_ = tt_setup
    all_non_poison = [
        s for s in skills.get_skilltypes() if s is not skills.Poison
    ][: Card.MAX_SKILLS]
    cards = [Card("Full", 1, 1, 1, all_non_poison)]
    human.deck = Deck("main", cards)
    loc = PoisonSkillLocation("0", 0, 0, [])
    res = loc.handle(view_class=FakePoisonSkillView, humanplayer=human)
    assert res is True
    assert "none of your cards can receive the Poison skill" in error_message
    assert cards[0].skills.count() == Card.MAX_SKILLS
    assert not cards[0].skills.has(skills.Poison)


def test_error_when_deck_is_empty(tt_setup):
    """Empty deck → no eligible cards → error message and no-op (no crash)."""
    _reset_messages()
    human, *_ = tt_setup
    human.deck = Deck("main", [])
    loc = PoisonSkillLocation("0", 0, 0, [])
    res = loc.handle(view_class=FakePoisonSkillView, humanplayer=human)
    assert res is True
    assert "none of your cards can receive the Poison skill" in error_message


def test_location_has_proper_marker_and_description():
    """The location must have a non-default marker and a description that references
    Poison so it renders sensibly on the map."""
    loc = PoisonSkillLocation("0", 0, 0, [])
    assert loc.marker != "___"  # not the abstract base default
    assert loc.description is not None
    assert "Poison" in loc.description
