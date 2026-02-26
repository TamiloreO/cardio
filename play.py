import logging
import argparse
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


# ----- main menu -----

menu = TUIMenu()
game_mode = menu.show()  # "computer" or "multiplayer"
menu.close()

# ----- multiplayer lobby (only when multiplayer was chosen) -----

net_sock = None   # Will hold the TCP socket when in multiplayer mode.
net_role = None   # "host" or "guest".

if game_mode == "multiplayer":
    lobby_view = TUILobbyView(player_name=humanplayer.name)
    conn = lobby_view.show()
    lobby_view.close()

    if conn is None:
        # Player pressed Escape in the lobby – fall back to vs-computer mode so the
        # process does not exit without offering them something to do.
        game_mode = "computer"
    else:
        net_sock = conn.sock
        net_role = conn.role


# ----- run loop -----

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

    while run.is_on:  # Visit locations in run:
        chosen_loc = mapview.get_next_location()
        mapview.move_to(chosen_loc)
        run.move_to(chosen_loc)
        view = session_view_directory[type(chosen_loc)]  # type: ignore
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

    # In multiplayer, the TCP connection is per-run; close it when the run ends so
    # both peers can reconnect fresh for the next run.
    if game_mode == "multiplayer" and net_sock is not None:
        try:
            net_sock.close()
        except OSError:
            pass
        net_sock = None
        net_role = None
        game_mode = "computer"  # Revert to solo for subsequent runs in this session.
