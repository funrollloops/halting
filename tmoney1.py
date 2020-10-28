#!/usr/bin/env python3

import random
import sys

from player_common import State, PlayerResponse, run_player

rank_to_distance = {
  0: 0,
  2: 3,
  3: 5,
  4: 7,
  5: 9,
  6: 11,
  7: 13,
  8: 11,
  9: 9,
  10: 7,
  11: 5,
  12: 3,
}

INITIAL_GOAL = sum(rank_to_distance.values())

def goal_remaining(state):
  goal = 0
  for rank in state.uncommitted.keys():
    if state.first_player:
      goal += state.player1[rank]
    else:
      goal += state.player2[rank]
  return goal

def value_move(rank, state):
  return 100 if rank in state.uncommitted.keys() else rank_to_distance[rank]

def decide_stop(state):
  if len(state.uncommitted) < 3:
    return False

  progress = 0
  for rank, value in state.uncommitted.items():
    if state.first_player:
      progress += state.player1[rank - 2] - value
    else:
      progress += state.player2[rank - 2] - value
  
  # print('/%s' % progress, file=sys.stderr)
  return progress >= 4

def tmoney1_player(state: State) -> PlayerResponse:
  valid_moves = state.valid_moves()
  best = (-100000, False, 0, 0)

  for m1, m2 in state.valid_moves():
    s1, s2 = value_move(m1, state), value_move(m2, state)
    score = s1 + s2
    candidate = (score, m1, m2)
    if candidate > best:
      best = candidate

  stop = decide_stop(state)
  return PlayerResponse(track1=best[1], track2=best[2], stop=stop)

if __name__ == '__main__':
  run_player(tmoney1_player)
