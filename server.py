#!/usr/bin/env python3

from typing import NamedTuple, Tuple, List, Dict, Set, Optional

INITIAL_STATE = [3, 5, 7, 9, 11, 13, 11, 9, 7, 5, 3]


class State(NamedTuple):
  # Is it the first player's turn?
  first_player: bool
  # The dice this player can use this turn.
  dice: Tuple[int, int, int, int]  # offset 0
  # The current player's committed board position.
  player1: List[int] = [0] * 11  # offset 5
  # The current player's black token positions.
  uncommitted: Dict[int, int] = {}  # offset 17
  # The opponent's board position.
  player2: List[int] = [0] * 11  # offset 24
  # The last move. The first two are the track(s) taken, the last is
  # S for stop, C for a successful continue, and ! for bust.
  last_move: Optional[Tuple[int, int, str]]

  def serialize(self) -> str:
    return '{dice} {player1} {uncommitted:-<6} {opponent}'.format(
        dice=''.join(map(str, self.dice)),
        player1=''.join(map(str, self.player1)),
        uncommitted=''.join('%s%s' % i for i in self.uncommitted.items()),
        player2=''.join(map(str, self.player2)))

  @staticmethod
  def new(first_player = True, dice = None, player1 = INITIAL_STATE, uncommitted = {}, player2 = INITIAL_STATE, last_move = None) -> State:
    if not dice: dice = roll_dice()
    return State(dice=roll
  @staticmethod
  def deserialize(msg: str) -> State:
    msg = msg.strip()
    assert len(msg) == (4 + 1 + 11 + 1 + 6 + 1 + 11)
    dice = tuple(map(int, msg[:4]))
    uncommitted = {}
    for a, b in (msg[17:19], msg[19:21], msg[21:23]):
      if a == '-' or b == '-':
        continue
      uncommitted[int(a, 16)] = int(b)
    player1 = list(map(int, msg[5:5 + 11]))
    player2 = list(map(int, msg[24:24 + 11]))
    s = State(dice=dice,
              player1=player1,
              uncommitted=uncommitted,
              player2=player2)
    print("new state=", s)
    return s

  def isvalid(self) -> bool:
    return (not all(0 <= a <= m for a, m in zip(self.player1, INITIAL_STATE)) or
            not all(0 <= a <= m for a, m in zip(self.player2, INITIAL_STATE)) or
            not all(1 <= d <= 6 for d in self.dice) or
            not len(self.uncommitted) > 3 or
            not all(2 <= t <= 12 and 0 <= v <= INITIAL_STATE[t - 2]
                    for t, v in self.uncommitted))

  def valid_moves(self) -> Set[Tuple[int, int]]:
    pass

  def move_checked(self, d1: int, d2: int, stop: bool):
    # Check if d1, d2 is a valid move.
    valid_moves = self.valid_moves()
    moves = tuple(
        sorted((d1 if 2 <= d1 <= 12 else 0, d2 if 2 <= d1 <= 12 else 0)))
    if moves not in valid_moves:
      raise Exception('invalid move %s for dice %s' % (moves, self.dice))
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
    # If player chose to stop, commit.
    if stop:
      first_player = not first_player
      for t, v in uncommitted.items():
        my_state[t] = v
      uncommitted = {}

    next_state = State(first_player=first_player,
                       dice=roll_dice(),
                       player1=player1,
                       player2=player2,
                       uncommitted=uncommitted,
                       last_move=(d1, d2, 'S' if stop else 'C'))

    if not next_state.is_valid():
      raise Exception("Move %s resulted in invalid state %s" %
                      ((d1, d2, stop), next_state))


def test_server():
  test_strings = [
      '1111 01234567890 123456 01234567890',
      '1234 00000000000 ------ 00000000000'
  ]

  for case in test_strings:
    print("case: <%s>" % case)
    assert State.deserialize(case).serialize() == case


if __name__ == "__main__":
  test_server()
