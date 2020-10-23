import random
import sys

from typing import NamedTuple, Tuple, Callable

from server import State

class PlayerResponse(NamedTuple):
  track1: int
  track2: int
  stop: bool


def run_player(player: Callable[[State], PlayerResponse]):
  """Given a player (a callable), implement the game protocol.

  The given player will be passed a State object and is expected to return a
  PlayerResponse. A falsey track number means no advancement."""
  
  while True:
    line = sys.stdin.readline()
    if not line:
      break

    
    state = State.deserialize(line.strip())
    m1, m2, stop = player(state)
    print('%x%x%s' % (m1 or 0, m2 or 0, 'S' if stop else 'C'))
    sys.stdout.flush()
