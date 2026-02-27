import logging
import sys
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


# ----- shared run-teardown helper -----

def _cleanup_run(humanplayer, run, mapview, net_sock):
    """Return deck cards to the collection, reset lives, close the map view, and
    (if provided) close the network socket.  Safe to call after both normal run
    completion and mid-run disconnection.
    """
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


# ----- load or create player -----

run = None

try:  # Existing game/player?
    humanplayer, run = jason.load_all()
except FileNotFoundError:  # New game/player
    logging.debug("No save file found. Starting new game")
    humanplayer = HumanPlayer.create_new("You")

if args.human_name:
    humanplayer.name = args.human_name


# ----- outer loop: main menu → optional lobby → run -----
#
# This loop is re-entered whenever:
#   • The player presses Escape in the lobby (returns to the menu, not into a game).
#   • A multiplayer run ends normally.
#   • The remote peer disconnects mid-fight (returns to the menu, not into a solo run).

while True:

    # ── main menu ──────────────────────────────────────────────────────────────
    menu = TUIMenu()
    game_mode = menu.show()  # "computer", "multiplayer", or "exit"
    menu.close()

    if game_mode == "exit":
        sys.exit(0)

    # ── multiplayer lobby (only when multiplayer was chosen) ───────────────────
    net_sock = None   # Will hold the TCP socket when in multiplayer mode.
    net_role = None   # "host" or "guest".

    if game_mode == "multiplayer":
        lobby_view = TUILobbyView(player_name=humanplayer.name)
        conn = lobby_view.show()
        lobby_view.close()

        if conn is None:
            # Player pressed Escape anywhere inside the lobby — loop back to show
            # the main menu again.  Do NOT fall through to a computer-mode run.
            continue

        net_sock = conn.sock
        net_role = conn.role

    # ── run loop ───────────────────────────────────────────────────────────────
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
        from cardio.net.network_fight_vnc import NetworkFightVnC, PeerDisconnectedError
        import functools

        # Build a thin factory that pre-binds the network socket.
        # NetworkFightVnC.__init__ accepts ``sock`` as its first positional argument
        # (before *args / **kwargs) so we use functools.partial to inject it.
        NetworkFightVnCForSession = functools.partial(NetworkFightVnC, net_sock)

        # Copy the view directory and replace only the fight entry.
        session_view_directory = dict(view_directory)
        session_view_directory[FightLocation] = NetworkFightVnCForSession
    else:
        PeerDisconnectedError = None  # type: ignore[assignment,misc]
        session_view_directory = view_directory

    # ── inner location loop ────────────────────────────────────────────────────
    try:
        while run.is_on:  # Visit locations in run:
            chosen_loc = mapview.get_next_location()
            mapview.move_to(chosen_loc)
            run.move_to(chosen_loc)
            view = session_view_directory[type(chosen_loc)]  # type: ignore
            run.is_on = chosen_loc.handle(view, humanplayer)
            jason.save_all(humanplayer, run)

    except Exception as exc:  # noqa: BLE001
        # Only handle PeerDisconnectedError when it is defined (multiplayer mode).
        if PeerDisconnectedError is not None and isinstance(exc, PeerDisconnectedError):
            # The fight view already showed the player a message before raising.
            # Clean up and loop back to the main menu.
            _cleanup_run(humanplayer, run, mapview, net_sock)
            run = None
            net_sock = None
            net_role = None
            continue
        raise  # All other exceptions propagate normally.

    # ── normal end-of-run cleanup ──────────────────────────────────────────────
    mapview.message("Game over! 🥴 For this run. Try another run. 🎮")
    # FIXME Show run stats & somehow add run stats to player's history
    _cleanup_run(humanplayer, run, mapview, net_sock)
    run = None

    # In multiplayer, the TCP connection is per-run.  It is closed inside
    # _cleanup_run; clear the local references and loop back to the main menu so
    # the player can start a fresh session (solo or multiplayer).
    if game_mode == "multiplayer":
        net_sock = None
        net_role = None
        continue  # Return to the main menu after a multiplayer run ends.
