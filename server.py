#!/usr/bin/env python3

import queue
import re
from random import randint
import sys
import subprocess
import threading
from typing import NamedTuple, Tuple, List, Dict, Set, Optional

INITIAL_STATE = [3, 5, 7, 9, 11, 13, 11, 9, 7, 5, 3]


class IllegalMoveException(Exception):
  pass

class IllegalPlayerActionException(Exception):
  pass


def roll_dice():
  return tuple(sorted((randint(1, 6) for _ in range(4))))

class Player(NamedTuple):
  # The subprocess to communicate with the player on.
  proc: subprocess.Popen
  # The queue to receive the player program output on.
  q: queue.Queue

class Game:
  RE_PLAYER_MOVE = re.compile(r'([0-9a-c])([0-9a-c])([SC])')

  def __init__(self, player_1_cmd: str, player_2_cmd: str):
    self.state = State()

    player1_queue = queue.Queue()
    player1_proc = subprocess.Popen(
      player_1_cmd.split(' '), stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    self.player1 = Player(proc=player1_proc, q=player1_queue)
    t = threading.Thread(target=self.output_reader,
                         args=(self.player1,))
    t.daemon = True
    t.start()

    player2_queue = queue.Queue()
    player2_proc = subprocess.Popen(
      player_2_cmd.split(' '), stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    self.player2 = Player(proc=player2_proc, q=player2_queue)
    t2 = threading.Thread(target=self.output_reader,
                          args=(self.player2,))
    t2.daemon = True
    t2.start()

  def output_reader(self, player):
    while True:
      line = player.proc.stdout.readline()
      if line:
        print(line.decode('utf-8'))
        player.q.put(line.decode('utf-8'))

  def run(self):
    self.state = self.state.roll_dice()

    while True:
      if self.state.first_player:
        current_player = self.player1
      else:
        current_player = self.player2

      send = self.state.serialize()
      print(send)
      current_player.proc.stdin.write(send.encode('utf-8') + b'\n')
      current_player.proc.stdin.flush()
      line = current_player.q.get()


      md = self.RE_PLAYER_MOVE.match(line)
      if not md:
        raise IllegalMoveException(line)

      m1 = int(md.group(1), 16)
      m2 = int(md.group(2), 16)
      stop = md.group(3) == 'S'

      if not stop and md.group(3) != 'C':
        raise IllegalMoveException()

      self.state = self.state.move_checked(m1, m2, stop)

      if self.state.is_game_over():
        break

  def cleanup(self):
    self.player1.proc.terminate()
    self.player2.proc.terminate()
    

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

  def serialize(self, for_player_1=True) -> str:
    player = 1 if self.first_player else 2
    if not for_player_1:
      player = 2 if player == 1 else 1
    return '{player} {dice} {player1} {uncommitted:-<6} {player2} {last_move} {valid_moves}'.format(
        player=player,
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

  def roll_dice(self):
    return State(first_player=self.first_player,
                 dice=roll_dice(),
                 player1=self.player1,
                 player2=self.player2,
                 uncommitted=self.uncommitted)

  def move_checked(self, d1: int, d2: int, stop: bool):
    # Check if d1, d2 is a valid move.
    valid_moves = self.valid_moves()
    moves = tuple(
        sorted((d1 if 2 <= d1 <= 12 else 0, d2 if 2 <= d2 <= 12 else 0)))
    if moves not in valid_moves:
      raise IllegalMoveException(
        'invalid move %s for dice %s, valid moves are: %s' %
        (moves, self.dice, valid_moves))
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

  def is_game_over(self):
    return self.player1.count(0) >= 3 or self.player2.count(0) >= 3


def main(player_1_cmd, player_2_cmd):
  try:
    g = Game(player_1_cmd=player_1_cmd, player_2_cmd=player_2_cmd)
    g.run()
  finally:
    g.cleanup()

if __name__ == '__main__':
  if len(sys.argv) != 3:
    print('usage: server.py <player 1 cmd> <player 2 cmd>')
    sys.exit(1)
  main(sys.argv[1], sys.argv[2])
