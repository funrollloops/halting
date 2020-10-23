#!/usr/bin/env python3

import random
import sys

from player_common import State, PlayerResponse, run_player
from typing import Dict, List

def yield_opts():
  for i in range(1, 7):
    for j in range(1, 7):
      for k in range(1, 7):
        for l in range(1, 7):
          yield ((a, b) if a < b else (b, a)
                 for a, b in ((i + j, k + l), (i + k, j + l), (i + l, j + k)))


class DistHelper(object):
  def __init__(self):
    self.bv = []
    for p in yield_opts():
      b = 0
      for a, b in p:
        b |= (1 << a)
        b |= (1 << b)
      bv.append(b)

  def probs(self, vs):
    bvs = 0
    for v in vs:
      bvs |= (1 << v)
    return sum((bvs & vv) != 0 for vv in self.bv) * 1. / len(self.bv)

def value_move(m, state: State):
  m -= 2
  s = state.player1[m] - state.player2[m]
  if not state.first_player: s = -s
  return s

def heuristic_player(state: State) -> PlayerResponse:
  valid_moves = state.valid_moves()
  best = (-100000, False, 0, 0)
  for m1, m2 in state.valid_moves():
    s1, s2 = value_move(m1, state), value_move(m2, state)
    score = s1 + s2
    stop = s1 > 1 and s2 > 1
    candidate = (score, stop, m1, m2)
    if candidate > best: best = candidate
  return PlayerResponse(track1=best[2], track2=best[3], stop=best[1])

if __name__ == '__main__':
  run_player(heuristic_player)
