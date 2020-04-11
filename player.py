import random
import sys

from server import State

def main():
  while True:
    line = sys.stdin.readline()
    if not line:
      break

    state = State.deserialize(line.strip())
    move = random.sample(state.valid_moves(), 1)
    stop = random.choice((True, True, False))

    print('%x%x%s' % (move[0] + ('S' if stop else 'C',)))
    sys.stdout.flush()

if __name__ == '__main__':
  main()
