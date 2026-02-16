import logging
import argparse
import sys
from cardio import HumanPlayer
from cardio.run import Run
from cardio.tui.mapview import TUIMapView
from cardio.tui.mainmenu import MainMenu
from cardio.locations.location_directory import view_directory
# FIXME For some reason, we need to import blueprints here, otherwise jason will
# complain about being partially initialized when starting the game:
import cardio.blueprints
from cardio import jason

logging.basicConfig(level=logging.DEBUG)


# ----- command line arguments -----

parser = argparse.ArgumentParser()
parser.add_argument("--reset", action="store_true", help="Delete save files")
parser.add_argument("--human-name", action="store", help="Set human player's name")
args = parser.parse_args()

if args.reset:
    jason.reset_all()


# ----- main menu -----

def has_save_file() -> bool:
    try:
        jason.load_all()
        return True
    except FileNotFoundError:
        return False


menu = MainMenu(has_save=has_save_file())
choice = menu.show()

if choice == "exit":
    sys.exit(0)

run = None
humanplayer = None

if choice == "continue":
    try:
        humanplayer, run = jason.load_all()
    except FileNotFoundError:
        logging.debug("No save file found. Starting new game")
        humanplayer = HumanPlayer.create_new("You")
else:  # choice == "start"
    jason.reset_all()
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

    # Run is over:
    mapview.message("Game over! 🥴 For this run. Try another run. 🎮")
    # FIXME Show run stats & somehow add run stats to player's history
    humanplayer.reset_lives()
    mapview.close()
    # Add deck back into collection:
    for card in humanplayer.deck.cards:
        humanplayer.collection.add_card(card)
    humanplayer.deck.cards = []
