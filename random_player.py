#!/usr/bin/env python3

import random
import sys

from player_common import run_player, State, PlayerResponse

def random_player(state: State) -> PlayerResponse:
  move = random.sample(state.valid_moves(), 1)[0]
  # Randomly decide to stop or continue
  stop = random.choice((True, False))
  return PlayerResponse(move[0], move[1], stop)

if __name__ == '__main__':
  run_player(random_player)
