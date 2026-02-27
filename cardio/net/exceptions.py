"""cardio.net.exceptions — Network-layer exception types.

Kept in a module with zero game-level imports so that test files can import these
exception classes without triggering the full TUI import chain (which requires a
functioning asciimatics installation).
"""


class PeerDisconnectedError(Exception):
    """Raised when the remote peer drops the connection during a fight.

    Propagates up through :meth:`~cardio.net.network_fight_vnc.NetworkFightVnC.handle_fight`
    after the player has been shown a message.  The caller (``play.py``) catches this
    to return the player to the main menu rather than crashing.
    """
