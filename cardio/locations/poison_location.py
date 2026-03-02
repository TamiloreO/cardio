from typing import Protocol, Type
from cardio import Card, CardList, skills
from cardio.human_player import HumanPlayer
from .location import Location
from .baseview import BaseLocationView


class PoisonView(BaseLocationView, Protocol):
    def __init__(self, cards: CardList, *args, **kwargs) -> None:
        ...

    def pick(self, activecards: CardList) -> Card:
        ...

    def show_upgrade(self, card: Card) -> None:
        ...


class PoisonLocation(Location):
    """Add the Poison skill to a card.

    The player selects a card from their deck that doesn't already have the Poison
    skill. The Poison skill is then added to that card.
    """

    marker = "PSN"
    description = "Add the Poison 🐍 skill to a card."

    def generate(self) -> None:
        super().generate()

    def handle(self, view_class: Type[PoisonView], humanplayer: HumanPlayer) -> bool:
        view = view_class(humanplayer.deck.cards, description=self.description)

        # Find cards that can receive the Poison skill (don't already have it and have
        # room for more skills):
        eligible_cards = [
            c
            for c in humanplayer.deck.cards
            if not c.skills.has(skills.Poison) and c.skills.count() < Card.MAX_SKILLS
        ]

        if not eligible_cards:
            view.error(
                "Sorry, none of your cards can receive the Poison skill.\n"
                "(They either already have it or have too many skills.)"
            )
            view.close()
            return True

        card = view.pick(eligible_cards)
        card.skills.add(skills.Poison)
        view.show_upgrade(card)
        view.message(f"{card.name} gained the Poison 🐍 skill!")
        view.close()
        return True
