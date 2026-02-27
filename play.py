import logging
import argparse
import sys
from cardio import HumanPlayer
from cardio.run import Run
from cardio.tui.mapview import TUIMapView
from cardio.tui.menu import TUIMenu
from cardio.tui.lobby_view import TUILobbyView
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


# ----- load or create player -----

run = None

try:  # Existing game/player?
    humanplayer, run = jason.load_all()
except FileNotFoundError:  # New game/player
    logging.debug("No save file found. Starting new game")
    humanplayer = HumanPlayer.create_new("You")

if args.human_name:
    humanplayer.name = args.human_name


# ----- main game loop (menu → lobby → run) -----

while True:
    # ----- main menu -----
    menu = TUIMenu()
    game_mode = menu.show()  # "computer", "multiplayer", or "exit"
    menu.close()

    if game_mode == "exit":
        sys.exit(0)

    # ----- multiplayer lobby (only when multiplayer was chosen) -----

    net_sock = None   # Will hold the TCP socket when in multiplayer mode.
    net_role = None   # "host" or "guest".

    if game_mode == "multiplayer":
        lobby_view = TUILobbyView(player_name=humanplayer.name)
        conn = lobby_view.show()
        lobby_view.close()

        if conn is None:
            # Player pressed Escape in the lobby – return to main menu.
            continue
        else:
            net_sock = conn.sock
            net_role = conn.role

    # ----- run loop -----

    while True:  # Forever start new runs (until returning to menu):

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

            if game_mode == "multiplayer":
                mapview.message(
                    f"Starting a new multiplayer run as {net_role}! ⚔  Good luck! 🐞"
                )
            else:
                mapview.message("Starting a new run... 🏃 Good luck! 🐞")

        jason.save_all(humanplayer, run)

        # Build the view directory for this session.  In multiplayer mode we swap the
        # FightLocation view class so it uses NetworkFightVnC instead of TUIFightVnC.
        if game_mode == "multiplayer" and net_sock is not None:
            from cardio.locations.fight_location import FightLocation
            from cardio.net.network_fight_vnc import NetworkFightVnC
            from cardio.net.network_fight_vnc import NetworkDisconnectedError
            import functools

            # Build a thin factory that pre-binds the network socket.
            # NetworkFightVnC.__init__ accepts ``sock`` as its first positional argument
            # (before *args / **kwargs) so we use functools.partial to inject it.
            NetworkFightVnCForSession = functools.partial(NetworkFightVnC, net_sock)

            # Copy the view directory and replace only the fight entry.
            session_view_directory = dict(view_directory)
            session_view_directory[FightLocation] = NetworkFightVnCForSession
        else:
            session_view_directory = view_directory
            NetworkDisconnectedError = None  # Not used in single-player.

        return_to_menu = False
        try:
            while run.is_on:  # Visit locations in run:
                chosen_loc = mapview.get_next_location()
                mapview.move_to(chosen_loc)
                run.move_to(chosen_loc)
                view = session_view_directory[type(chosen_loc)]  # type: ignore
                run.is_on = chosen_loc.handle(view, humanplayer)
                jason.save_all(humanplayer, run)
        except Exception as e:
            # Handle network disconnection in multiplayer mode.
            if game_mode == "multiplayer" and (
                NetworkDisconnectedError is not None
                and isinstance(e, NetworkDisconnectedError)
            ):
                mapview.message(
                    "Opponent disconnected! 🔌 Returning to main menu..."
                )
                return_to_menu = True
                run = None  # Reset the run so a new one starts next time.
            else:
                raise

        if return_to_menu:
            # Clean up and return to main menu.
            humanplayer.reset_lives()
            mapview.close()
            for card in humanplayer.deck.cards:
                humanplayer.collection.add_card(card)
            humanplayer.deck.cards = []
            if net_sock is not None:
                try:
                    net_sock.close()
                except OSError:
                    pass
            break  # Break out of run loop, continue to main menu loop.

        # Run is over:
        mapview.message("Game over! 🥴 For this run. Try another run. 🎮")
        # FIXME Show run stats & somehow add run stats to player's history
        humanplayer.reset_lives()
        mapview.close()
        # Add deck back into collection:
        for card in humanplayer.deck.cards:
            humanplayer.collection.add_card(card)
        humanplayer.deck.cards = []

        # In multiplayer, after the run ends, return to main menu so player can
        # start a fresh session (host/join again).
        if game_mode == "multiplayer" and net_sock is not None:
            try:
                net_sock.close()
            except OSError:
                pass
            break  # Return to main menu after multiplayer run ends.

