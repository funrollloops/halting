#!/usr/bin/env python3

from random import randint
from typing import NamedTuple, Tuple, List, Dict, Set, Optional

INITIAL_STATE = [3, 5, 7, 9, 11, 13, 11, 9, 7, 5, 3]


class IllegalMoveException(Exception):
  pass


def roll_dice():
  return tuple(sorted((randint(1, 6) for _ in range(4))))


class State(NamedTuple):
  # Is it the first player's turn?
  first_player: bool = True  # offset 0
  # The dice this player can use this turn.
  dice: Tuple[int, int, int, int] = (0, 0, 0, 0)  # offset 2
  # The current player's committed board position.
  player1: List[int] = INITIAL_STATE  # offset 7
  # The current player's black token positions.
  uncommitted: Dict[int, int] = {}  # offset 19
  # The opponent's board position.
  player2: List[int] = INITIAL_STATE  # offset 26
  # The last move. The first two are the track(s) taken, the last is
  # S for stop, C for a successful continue, and ! for bust.
  last_move: Optional[Tuple[int, int, str]] = (0, 0, '!')  # offset 38

  def serialize(self) -> str:
    return '{player} {dice} {player1} {uncommitted:-<6} {player2} {last_move} {valid_moves}'.format(
        player=1 if self.first_player else 2,
        dice=''.join(map(str, self.dice)),
        player1=''.join('%x' % x for x in self.player1),
        uncommitted=''.join('%x%x' % i for i in self.uncommitted.items()),
        player2=''.join('%x' % x for x in self.player2),
        last_move='%x%x%s' % self.last_move,
        valid_moves='|'.join("%x%x" % m for m in sorted(self.valid_moves())))

  @staticmethod
  def deserialize(msg: str):
    msg = msg.strip()
    assert len(msg) >= (4 + 1 + 11 + 1 + 6 + 1 + 11 + 1 + 3), (len(msg), msg)
    first_player = msg[0] == '1'
    dice = tuple(map(int, msg[2:2+4]))
    uncommitted = {}
    for a, b in (msg[19:21], msg[21:23], msg[23:25]):
      if a == '-' or b == '-':
        continue
      uncommitted[int(a, 16)] = int(b, 16)
    player1 = list(int(x, 16) for x in msg[7:7 + 11])
    player2 = list(int(x, 16) for x in msg[26:26 + 11])
    last_move = (int(msg[38], 16), int(msg[39], 16), msg[40])
    s = State(dice=dice,
              player1=player1,
              uncommitted=uncommitted,
              player2=player2,
              last_move=last_move)
    return s

  def isvalid(self) -> bool:
    return (not all(0 <= a <= m for a, m in zip(self.player1, INITIAL_STATE)) or
            not all(0 <= a <= m for a, m in zip(self.player2, INITIAL_STATE)) or
            not all(1 <= d <= 6 for d in self.dice) or
            not len(self.uncommitted) > 3 or
            not all(2 <= t <= 12 and 0 <= v <= INITIAL_STATE[t - 2]
                    for t, v in self.uncommitted))

  def active_player_state(self):
    return self.player1 if self.first_player else self.player2

  def valid_moves(self, dice=None) -> Set[Tuple[int, int]]:
    dice = dice or self.dice
    all_moves = [(dice[0] + dice[1], dice[2] + dice[3]),
                 (dice[0] + dice[2], dice[1] + dice[3]),
                 (dice[0] + dice[3], dice[1] + dice[2])]
    available_tracks = set(i + 2
                           for i in range(11)
                           if self.player1[i] > 0 and self.player2[i] > 0 and
                           self.uncommitted.get(i + 2, 1) > 0)
    black_tokens = set(self.uncommitted.keys())
    valid_moves = set()
    for m1, m2 in all_moves:
      if m1 not in available_tracks:
        m1 = 0
      if m2 not in available_tracks:
        m2 = 0
      if len(black_tokens) >= 3:
        if m1 not in black_tokens:
          m1 = 0
        if m2 not in black_tokens:
          m2 = 0
      if m1 == 0 and m2 == 0:
        continue
      # Both tracks are different and have not been advanced this turn, but we
      # only have one black token left. Generate two possible moves for this
      # case.
      elif (len(black_tokens) == 2 and m1 != m2 and m1 != 0 and m2 != 0 and
            m1 not in black_tokens and m2 not in black_tokens):
        valid_moves.add((0, m1))
        valid_moves.add((0, m2))
      # Both tracks are the same but there's only advancement left. Allow one
      # advancement in this case.
      elif (m1 == m2 and
            self.uncommitted.get(m1,
                                 self.active_player_state()[m1 - 2]) == 1):
        valid_moves.add((0, m1))
      else:
        valid_moves.add((m1, m2) if m1 < m2 else (m2, m1))
    return valid_moves

  def move_checked(self, d1: int, d2: int, stop: bool):
    # Check if d1, d2 is a valid move.
    valid_moves = self.valid_moves()
    moves = tuple(
        sorted((d1 if 2 <= d1 <= 12 else 0, d2 if 2 <= d2 <= 12 else 0)))
    if moves not in valid_moves:
      raise IllegalMoveException('invalid move %s for dice %s' %
                                 (moves, self.dice))
    # State variables.
    first_player = self.first_player
    player1 = self.player1[:]
    player2 = self.player2[:]
    uncommitted = self.uncommitted
    my_state = player1 if first_player else player2
    # Apply moves to uncommitted.
    for move in moves:
      if not (2 <= move <= 12):
        continue
      uncommitted[move] = uncommitted.get(move, my_state[move - 2]) - 1

    dice = roll_dice()
    def make_state(last_result):
      return State(first_player=first_player,
                   dice=dice,
                   player1=player1,
                   player2=player2,
                   uncommitted=uncommitted,
                   last_move=(d1, d2, last_result))

    # If player chose to stop, commit.
    if stop:
      first_player = not first_player
      for t, v in uncommitted.items():
        my_state[t - 2] = v
      uncommitted = {}
      next_state = make_state('S')
    else:
      next_state = make_state('C')

    consecutive_busts = 0
    while len(next_state.valid_moves()) == 0:
      print("no valid moves for", next_state.serialize())
      dice = roll_dice()
      first_player = not first_player
      uncommitted = {}
      if consecutive_busts > 0:
        d1, d2 = 0, 0
      consecutive_busts += 1
      assert consecutive_busts < 5
      next_state = make_state('!')
    assert next_state.isvalid(), (
        "valid move %s from %s resulted in invalid state %s" %
        ((d1, d2, stop), self.serialize(), next_state.serialize()))
    return next_state
