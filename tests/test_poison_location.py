from cardio import Card, CardList, Deck, skills
from cardio.locations.poison_location import PoisonLocation, PoisonView


class FakePoisonView(PoisonView):
    def __init__(self, *args, **kwargs) -> None:
        self.last_message = None
        self.last_error = None

    def pick(self, activecards: CardList) -> Card:
        return activecards[0]

    def show_upgrade(self, card: Card) -> None:
        pass

    def close(self) -> None:
        pass

    def message(self, msg: str) -> None:
        self.last_message = msg

    def error(self, msg: str) -> None:
        self.last_error = msg


def test_add_poison_to_card_without_skills(tt_setup):
    human, *_ = tt_setup
    card = Card("Viper", 1, 1, 1, None)
    human.deck = Deck("main", [card])
    loc = PoisonLocation("0", 0, 0, [])
    res = loc.handle(view_class=FakePoisonView, humanplayer=human)
    assert res is True
    assert card.skills.has(skills.Poison)
    assert card.skills.count() == 1


def test_add_poison_to_card_with_existing_skills(tt_setup):
    human, *_ = tt_setup
    card = Card("Viper", 1, 1, 1, [skills.Spines, skills.Shield])
    human.deck = Deck("main", [card])
    loc = PoisonLocation("0", 0, 0, [])
    res = loc.handle(view_class=FakePoisonView, humanplayer=human)
    assert res is True
    assert card.skills.has(skills.Poison)
    assert card.skills.has(skills.Spines)
    assert card.skills.has(skills.Shield)
    assert card.skills.count() == 3


def test_cannot_add_poison_to_card_that_already_has_it(tt_setup):
    human, *_ = tt_setup
    card_with_poison = Card("Already Poisoned", 1, 1, 1, [skills.Poison])
    card_without_poison = Card("Clean", 1, 1, 1, None)
    human.deck = Deck("main", [card_with_poison, card_without_poison])
    loc = PoisonLocation("0", 0, 0, [])
    view = FakePoisonView()
    res = loc.handle(view_class=lambda *a, **kw: view, humanplayer=human)
    assert res is True
    # The card_with_poison should be excluded from eligible cards, so card_without_poison
    # gets picked and receives Poison:
    assert card_without_poison.skills.has(skills.Poison)
    # card_with_poison still has exactly one Poison (not stacked):
    assert card_with_poison.skills.count() == 1


def test_no_eligible_cards_all_have_poison(tt_setup):
    human, *_ = tt_setup
    card1 = Card("Poisoned1", 1, 1, 1, [skills.Poison])
    card2 = Card("Poisoned2", 1, 1, 1, [skills.Poison])
    human.deck = Deck("main", [card1, card2])
    loc = PoisonLocation("0", 0, 0, [])
    view = FakePoisonView()
    res = loc.handle(view_class=lambda *a, **kw: view, humanplayer=human)
    assert res is True
    assert "none of your cards" in view.last_error.lower()
    # Cards unchanged:
    assert card1.skills.count() == 1
    assert card2.skills.count() == 1


def test_no_eligible_cards_all_at_max_skills(tt_setup):
    human, *_ = tt_setup
    # Card with MAX_SKILLS skills (but not Poison):
    max_skills = [
        skills.Spines,
        skills.Shield,
        skills.Regenerate,
        skills.Soaring,
        skills.Airdefense,
        skills.Underdog,
    ]
    assert len(max_skills) == Card.MAX_SKILLS
    card = Card("FullyLoaded", 1, 1, 1, max_skills)
    human.deck = Deck("main", [card])
    loc = PoisonLocation("0", 0, 0, [])
    view = FakePoisonView()
    res = loc.handle(view_class=lambda *a, **kw: view, humanplayer=human)
    assert res is True
    assert "none of your cards" in view.last_error.lower()
    assert not card.skills.has(skills.Poison)


def test_selects_from_multiple_eligible_cards(tt_setup):
    """The view's pick method receives only eligible cards."""
    human, *_ = tt_setup
    card_with_poison = Card("HasPoison", 1, 1, 1, [skills.Poison])
    card_eligible1 = Card("Eligible1", 2, 2, 1, None)
    card_eligible2 = Card("Eligible2", 3, 3, 1, [skills.Spines])
    human.deck = Deck("main", [card_with_poison, card_eligible1, card_eligible2])

    picked_cards = []

    class TrackingView(FakePoisonView):
        def pick(self, activecards: CardList) -> Card:
            picked_cards.extend(activecards)
            return activecards[0]

    loc = PoisonLocation("0", 0, 0, [])
    loc.handle(view_class=TrackingView, humanplayer=human)

    # card_with_poison should NOT be in the eligible list:
    assert card_with_poison not in picked_cards
    assert card_eligible1 in picked_cards
    assert card_eligible2 in picked_cards
    # First eligible card gets picked and receives Poison:
    assert card_eligible1.skills.has(skills.Poison)
