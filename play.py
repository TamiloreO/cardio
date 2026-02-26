import logging
import argparse
from cardio import HumanPlayer, Grid
from cardio.run import Run
from cardio.tui.mapview import TUIMapView
from cardio.tui.mainmenu import TUIMainMenu, TUIMultiplayerMenu, TUITextInput, GameMode
from cardio.tui.lobbyview import TUILobbyView, TUIServerBrowser
from cardio.tui.locations.multiplayer_fightview import TUIMultiplayerFightVnC
from cardio.locations.location_directory import view_directory
from cardio.multiplayer.lobby import Lobby
import cardio.blueprints
from cardio import jason

logging.basicConfig(level=logging.DEBUG)


# ----- command line arguments -----

parser = argparse.ArgumentParser()
parser.add_argument("--reset", action="store_true", help="Delete save files")
parser.add_argument("--human-name", action="store", help="Set human player's name")
parser.add_argument(
    "--mode",
    choices=["computer", "multiplayer"],
    help="Skip menu and start in specified mode",
)
args = parser.parse_args()

if args.reset:
    jason.reset_all()


# ----- Game mode handlers -----


def play_vs_computer(humanplayer: HumanPlayer) -> None:
    """Play the standard single-player vs computer mode."""
    run = None

    try:
        humanplayer, run = jason.load_all()
    except FileNotFoundError:
        logging.debug("No save file found. Starting new game")

    while True:
        if not run or not run.is_on:
            run = Run()

        mapview = TUIMapView(run, humanplayer, debug=False)
        if run.current_rung == 0:
            while True:
                humanplayer.collection.shuffle()
                humanplayer.deck.cards = humanplayer.collection.draw_cards(6)
                if any(c.power > 0 for c in humanplayer.deck.cards):
                    break
            mapview.message("Starting a new run... Good luck!")

        jason.save_all(humanplayer, run)

        while run.is_on:
            chosen_loc = mapview.get_next_location()
            mapview.move_to(chosen_loc)
            run.move_to(chosen_loc)
            view = view_directory[type(chosen_loc)]
            run.is_on = chosen_loc.handle(view, humanplayer)
            jason.save_all(humanplayer, run)

        mapview.message("Game over! For this run. Try another run.")
        humanplayer.reset_lives()
        mapview.close()
        for card in humanplayer.deck.cards:
            humanplayer.collection.add_card(card)
        humanplayer.deck.cards = []


def play_multiplayer(humanplayer: HumanPlayer) -> None:
    """Play the multiplayer mode."""
    menu = TUIMultiplayerMenu()
    choice = menu.show()
    menu.close()

    if choice == "back" or choice is None:
        return

    lobby = Lobby()

    if choice == "host":
        # Get player name if not set
        if humanplayer.name == "You":
            input_view = TUITextInput("Enter your name:", default="Host")
            name = input_view.show()
            input_view.close()
            if name:
                humanplayer.name = name

        if not lobby.host_game(humanplayer.name):
            logging.error("Failed to host game")
            return

    elif choice == "join":
        # Get server IP
        browser = TUIServerBrowser()
        host_ip = browser.show()
        browser.close()

        if not host_ip:
            return

        # Get player name
        if humanplayer.name == "You":
            input_view = TUITextInput("Enter your name:", default="Player")
            name = input_view.show()
            input_view.close()
            if name:
                humanplayer.name = name

        if not lobby.join_game(host_ip, humanplayer.name):
            logging.error("Failed to join game at %s", host_ip)
            return

    # Show lobby and wait for game to start
    lobby_view = TUILobbyView(lobby)
    game_seed = lobby_view.show()
    lobby_view.close()

    if not game_seed:
        lobby.leave_lobby()
        return

    # Get opponent info
    players = lobby.get_players()
    remote_player = next(
        (p for p in players if p.id != lobby.local_player.id), None
    )
    if not remote_player:
        logging.error("No remote player found")
        lobby.leave_lobby()
        return

    # Start multiplayer game loop
    run_multiplayer_game(
        humanplayer=humanplayer,
        remote_player_name=remote_player.name,
        is_host=lobby.is_host,
        lobby=lobby,
        game_seed=game_seed,
    )


def run_multiplayer_game(
    humanplayer: HumanPlayer,
    remote_player_name: str,
    is_host: bool,
    lobby: Lobby,
    game_seed: str,
) -> None:
    """Run the multiplayer game with the map TUI."""
    run = Run(base_seed=game_seed)

    # Set up deck for this run
    while True:
        humanplayer.collection.shuffle()
        humanplayer.deck.cards = humanplayer.collection.draw_cards(6)
        if any(c.power > 0 for c in humanplayer.deck.cards):
            break

    mapview = TUIMapView(run, humanplayer, debug=False)
    mapview.message(f"Multiplayer run starting! Opponent: {remote_player_name}")

    while run.is_on:
        chosen_loc = mapview.get_next_location()
        mapview.move_to(chosen_loc)
        run.move_to(chosen_loc)

        # For fight locations, use multiplayer fight view
        from cardio.locations.fight_location import FightLocation

        if isinstance(chosen_loc, FightLocation):
            grid = Grid(4)
            fight_view = TUIMultiplayerFightVnC(
                grid=grid,
                local_player=humanplayer,
                remote_player_name=remote_player_name,
                is_host=is_host,
                server=lobby.server,
                client=lobby.client,
                debug=False,
                description="MULTIPLAYER FIGHT!",
            )
            fight_view.handle_multiplayer_fight()
            fight_view.close()
            run.is_on = humanplayer.lives > 0
        else:
            # Use regular view for non-fight locations
            view = view_directory[type(chosen_loc)]
            run.is_on = chosen_loc.handle(view, humanplayer)

    mapview.message("Multiplayer game over!")
    humanplayer.reset_lives()
    mapview.close()

    for card in humanplayer.deck.cards:
        humanplayer.collection.add_card(card)
    humanplayer.deck.cards = []

    lobby.leave_lobby()


# ----- main -----


def main():
    # Load or create player
    try:
        humanplayer, _ = jason.load_all()
    except FileNotFoundError:
        logging.debug("No save file found. Creating new player")
        humanplayer = HumanPlayer.create_new("You")

    if args.human_name:
        humanplayer.name = args.human_name

    # Handle command line mode selection
    if args.mode == "computer":
        play_vs_computer(humanplayer)
        return
    elif args.mode == "multiplayer":
        play_multiplayer(humanplayer)
        return

    # Show main menu
    while True:
        menu = TUIMainMenu()
        choice = menu.show()
        menu.close()

        if choice is None:
            break
        elif choice == GameMode.COMPUTER:
            play_vs_computer(humanplayer)
        elif choice == GameMode.MULTIPLAYER:
            play_multiplayer(humanplayer)


if __name__ == "__main__":
    main()
