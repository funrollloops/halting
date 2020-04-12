#!/usr/bin/env python3

import queue
import re
from random import randint
import sys
import subprocess
import threading
from typing import NamedTuple, Tuple, List, Dict, Set, Optional

from state import State

class IllegalPlayerActionException(Exception):
  pass


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
