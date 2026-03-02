"""PoisonShopLocation

A map location where the player can have one of their cards coated in poison,
i.e. get the Poison skill added as a permanent upgrade.

Rules:
    - Player picks one card from their deck.
    - If that card already has the Poison skill, the coating fails: poison cannot
      be applied twice (mirrors the in-fight rule that an already-poisoned target
      cannot be poisoned again).
    - If the card is at its skill cap (`Card.MAX_SKILLS`), the coating fails.
    - Otherwise, the Poison skill is added to the card (permanent change to the
      `Card` instance — this survives the location and carries into all future
      fights, cf. DOMAIN.md "Modifications on cards are permanent").
"""

from typing import Protocol, Type
from cardio import Card, CardList
from cardio.human_player import HumanPlayer
from cardio.skills import Poison
from .location import Location
from .baseview import BaseLocationView


class PoisonShopView(BaseLocationView, Protocol):
    """View protocol for `PoisonShopLocation`.

    Intentionally matches the shape of `SkillLotteryView` so that
    `TUISkillLotteryView` (or any equivalent card-picker view) can be reused.
    """

    def __init__(self, cards: CardList, *args, **kwargs) -> None:
        ...

    def pick(self, activecards: CardList) -> Card:
        ...

    def show_upgrade(self, card: Card) -> None:
        ...


class PoisonShopLocation(Location):
    """Add the Poison 🐍 skill to a card of the player's choice."""

    marker = "P🐍S"
    description = (
        "🐍 Poison Shop — Coat one of your cards in venom and "
        "permanently add the Poison skill to it."
    )

    def generate(self) -> None:
        super().generate()

    def handle(
        self, view_class: Type[PoisonShopView], humanplayer: HumanPlayer
    ) -> bool:
        view = view_class(humanplayer.deck.cards, description=self.description)

        # Eligible cards = cards that don't already have Poison AND are below the
        # skill cap. "Already has Poison" is rejected by design: applying poison
        # twice is not allowed, and `SkillSet.add` would assert anyway.
        possible_cards = [
            c
            for c in humanplayer.deck.cards
            if not c.skills.has(Poison) and c.skills.count() < Card.MAX_SKILLS
        ]
        if not possible_cards:
            view.error(
                "Sorry, none of your cards can be coated in poison.\n"
                "(Every card either already has Poison or has no room for more skills.)"
            )
            return True

        card = view.pick(possible_cards)

        # Double-guard in case a view implementation returns a card outside the
        # active set; keep consistent with the location rules.
        if card.skills.has(Poison):
            view.error(
                f"{card.name} already has the Poison skill — "
                "it cannot be poisoned again."
            )
            return True
        if card.skills.count() >= Card.MAX_SKILLS:
            view.error(f"{card.name} is at its skill cap — no room for Poison.")
            return True

        card.skills.add(Poison)
        view.show_upgrade(card)
        view.message(
            f"{card.name} was coated in venom and gained the "
            f"{Poison.name} {Poison.symbol} skill! 🎉"
        )
        view.close()
        return True
