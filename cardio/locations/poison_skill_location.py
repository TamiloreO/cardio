"""PoisonSkillLocation

A map location that adds the Poison skill to a card the player chooses. This is a
dedicated, deterministic upgrade (unlike `SkillLotteryLocation`, which adds a *random*
skill and may remove one instead): the player picks a card and that card is guaranteed
to receive the Poison skill — provided the card does not already have Poison and has
room for another skill.
"""

from typing import Protocol, Type
from cardio import Card, CardList, skills
from cardio.human_player import HumanPlayer
from .location import Location
from .baseview import BaseLocationView


class PoisonSkillView(BaseLocationView, Protocol):
    """View protocol for `PoisonSkillLocation`.

    This intentionally mirrors the shape of `SkillLotteryView` so that the existing
    `TUISkillLotteryView` can be reused without modification (it already implements
    `pick(activecards)` and `show_upgrade(card)`).
    """

    def __init__(self, cards: CardList, *args, **kwargs) -> None:
        ...

    def pick(self, activecards: CardList) -> Card:
        ...

    def show_upgrade(self, card: Card) -> None:
        ...


class PoisonSkillLocation(Location):
    """Add the Poison skill to a card of the player's choosing.

    Eligible cards are those that:
    - do **not** already have the Poison skill (no skill stacking), and
    - have fewer than `Card.MAX_SKILLS` skills (room for one more).

    If no card is eligible, the player is shown an error message and the location is
    a no-op (the run continues normally).
    """

    marker = "S🐍U"
    description = (
        f"Add the {skills.Poison.name} {skills.Poison.symbol} skill to a card."
    )

    def generate(self) -> None:
        super().generate()

    def handle(self, view_class: Type[PoisonSkillView], humanplayer: HumanPlayer) -> bool:
        view = view_class(humanplayer.deck.cards, description=self.description)

        # Determine which cards are eligible: must have room for another skill and
        # must not already carry Poison (the guarded-no-stacking invariant mirrors the
        # in-fight `_poisoned` guard — a card can carry Poison at most once).
        eligible_cards = [
            c
            for c in humanplayer.deck.cards
            if c.skills.count() < Card.MAX_SKILLS and not c.skills.has(skills.Poison)
        ]

        if not eligible_cards:
            view.error(
                "Sorry, none of your cards can receive the Poison skill.\n"
                "(Each eligible card must have a free skill slot and must not "
                "already have Poison.)"
            )
            view.close()
            return True

        card = view.pick(eligible_cards)
        card.skills.add(skills.Poison)
        view.show_upgrade(card)
        view.message(
            f"{card.name} gained the {skills.Poison.name} "
            f"{skills.Poison.symbol} skill! 🥳"
        )

        view.close()
        return True
