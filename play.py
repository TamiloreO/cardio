import logging
import argparse
from cardio import HumanPlayer
from cardio.run import Run
from cardio.tui.mapview import TUIMapView
from cardio.locations.location_directory import view_directory
# Import blueprints before jason to ensure proper initialization order.
# The jason module imports from cardio.blueprints, which imports from cardio
# (for Card/CardList). Since HumanPlayer has a hamster_blueprint field that
# references Blueprint, we need blueprints fully initialized first.
import cardio.blueprints  # noqa: F401
from cardio import jason

logging.basicConfig(level=logging.DEBUG)


# ----- command line arguments -----

parser = argparse.ArgumentParser()
parser.add_argument("--reset", action="store_true", help="Delete save files")
parser.add_argument("--human-name", action="store", help="Set human player's name")
args = parser.parse_args()

if args.reset:
    jason.reset_all()


# ----- main -----

run = None

try:  # Existing game/player?
    humanplayer, run = jason.load_all()
except FileNotFoundError:  # New game/player
    logging.debug("No save file found. Starting new game")
    humanplayer = HumanPlayer.create_new("You")

if args.human_name:
    humanplayer.name = args.human_name

while True:  # Forever start new runs:
    if not run or not run.is_on:
        run = Run()

    mapview = TUIMapView(run, humanplayer, debug=False)
    if run.current_rung == 0:  # Starting a new run:
        # Pick random cards from collection for the deck:
        while True:
            humanplayer.collection.shuffle()
            humanplayer.deck.cards = humanplayer.collection.draw_cards(6)
            if any(c.power > 0 for c in humanplayer.deck.cards):
                # Make sure not the entire deck is powerless.
                break
        mapview.message("Starting a new run... 🏃 Good luck! 🐞")

    jason.save_all(humanplayer, run)

    while run.is_on:  # Visit locations in run:
        chosen_loc = mapview.get_next_location()
        mapview.move_to(chosen_loc)
        run.move_to(chosen_loc)
        view = view_directory[type(chosen_loc)]  # type: ignore
        run.is_on = chosen_loc.handle(view, humanplayer)
        jason.save_all(humanplayer, run)

    # Run is over - record stats and show summary:
    run_stats = humanplayer.add_run_to_history(
        rungs_completed=run.current_rung,
        seed=run.base_seed
    )

    game_over_msg = (
        f"Game over! 🥴\n\n"
        f"This run: Reached rung {run_stats.rungs_completed}\n\n"
        f"Your history:\n{humanplayer.run_history.format_summary()}\n\n"
        f"Try another run! 🎮"
    )
    mapview.message(game_over_msg)

    humanplayer.reset_lives()
    jason.save_all(humanplayer, run)
    mapview.close()

    # Add deck back into collection:
    for card in humanplayer.deck.cards:
        humanplayer.collection.add_card(card)
    humanplayer.deck.cards = []
