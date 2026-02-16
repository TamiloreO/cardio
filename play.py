import logging
import argparse
import sys
from datetime import datetime
from pathlib import Path
from platformdirs import user_data_path

# Set up file logging before any other imports that might log
LOG_DIR = user_data_path("cardio") / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Log file: {LOG_FILE}")

from cardio import HumanPlayer
from cardio.run import Run
from cardio.tui.mapview import TUIMapView, QuitToMenuException
from cardio.tui.mainmenu import MainMenu, MenuChoice
from cardio.locations.location_directory import view_directory
# FIXME For some reason, we need to import blueprints here, otherwise jason will
# complain about being partially initialized when starting the game:
import cardio.blueprints
from cardio import jason


# ----- command line arguments -----

parser = argparse.ArgumentParser()
parser.add_argument("--reset", action="store_true", help="Delete save files")
parser.add_argument("--human-name", action="store", help="Set human player's name")
args = parser.parse_args()

if args.reset:
    jason.reset_all()


# ----- main menu -----

def check_save_exists() -> bool:
    try:
        jason.load_all()
        return True
    except (FileNotFoundError, AssertionError):
        return False


def show_main_menu() -> MenuChoice:
    has_save = check_save_exists()
    menu = MainMenu(has_save=has_save)
    return menu.show_menu()


# ----- main -----

while True:
    try:
        choice = show_main_menu()

        if choice == MenuChoice.EXIT:
            logger.info("Player exited game")
            sys.exit(0)

        if choice == MenuChoice.NEW_GAME:
            logger.info("Starting new game")
            jason.reset_all()
            humanplayer = HumanPlayer.create_new("You")
            run = None
        elif choice == MenuChoice.CONTINUE:
            logger.info("Continuing saved game")
            try:
                humanplayer, run = jason.load_all()
            except (FileNotFoundError, AssertionError) as e:
                logger.warning(f"Failed to load save: {e}. Starting new game")
                humanplayer = HumanPlayer.create_new("You")
                run = None

        if args.human_name:
            humanplayer.name = args.human_name

        while True:  # Forever start new runs:
            if not run or not run.is_on:
                run = Run()
                logger.info(f"Starting new run with seed {run.base_seed}")

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

            try:
                while run.is_on:  # Visit locations in run:
                    chosen_loc = mapview.get_next_location()
                    mapview.move_to(chosen_loc)
                    run.move_to(chosen_loc)
                    view = view_directory[type(chosen_loc)]  # type: ignore
                    run.is_on = chosen_loc.handle(view, humanplayer)
                    jason.save_all(humanplayer, run)
            except QuitToMenuException:
                logger.info("Player quit to main menu")
                jason.save_all(humanplayer, run)
                mapview.close()
                break  # Return to main menu

            # Run is over:
            mapview.message("Game over! 🥴 For this run. Try another run. 🎮")
            logger.info("Run ended")
            # FIXME Show run stats & somehow add run stats to player's history
            humanplayer.reset_lives()
            mapview.close()
            # Add deck back into collection:
            for card in humanplayer.deck.cards:
                humanplayer.collection.add_card(card)
            humanplayer.deck.cards = []
            break  # Return to main menu after a run ends

    except Exception as e:
        logger.exception(f"Unhandled exception: {e}")
        raise
