from unittest.mock import patch

from server import State, IllegalMoveException

def test_serialize_deserialize():
  test_strings = [
      '1 1112 01234567890 123456 01234567890 ab! 03',
      '1 1234 3579bdb9753 ------ 3579bdb9753 91S 37|46|55',
      '1 1234 11111111111 ------ 11111111111 91S 05|37|46',
      '1 1234 11111111111 406030 11111111111 91S ',
      '1 1234 3579bdb9753 6ac2-- 3579bdb9753 a1S 03|07|46|55',
      '1 3456 3579bdb9753 ------ 3579bdb9753 a1S 7b|8a|99',
  ]

  for case in test_strings:
    print("case: <%s>" % case)
    reserialized = State.deserialize(case).serialize()
    print("  <>: <%s>" % reserialized)
    assert reserialized == case

@patch('server.roll_dice', lambda: (6, 5, 4, 3))
def test_moves():
  test_cases = [
      # Take valid move and stop.
      ('1 1112 01234567890 b850-- 01234567890 00! 03', (0, 3, True),
       '2 6543 00204567880 ------ 01234567890 03S'),
      # Take a valid move and bust.
      ('1 1112 01234567890 4152-- 11234567890 00! 03', (0, 3, False),
       '2 6543 01234567890 ------ 11234567890 03!'),
      #'1234 3579bdb9753 ------ 3579bdb9753 91S 37|46|55',
      #'1234 11111111111 ------ 11111111111 91S 05|37|46',
      #'1234 11111111111 406030 11111111111 91S ',
      #'1234 3579bdb9753 6ac2-- 3579bdb9753 a1S 03|07|46|55',
      #'3456 3579bdb9753 ------ 3579bdb9753 a1S 7b|8a|99',
  ]
  for initial, move, expected in test_cases:
    print("==")
    print("initial:", initial)
    initial_parsed = State.deserialize(initial)
    assert initial_parsed.serialize()[:len(initial)] == initial, \
        "initial not idempotent?\n input: %s\noutput: %s" % (initial, initial_parsed.serialize())
    print('move:', move)
    try:
      actual = initial_parsed.move_checked(*move)
      print('expected:', expected)
      assert actual.serialize()[:len(expected)] == expected, \
          "\n initial: %s\nexpected: ???? %s\n  actual: %s" % (
              initial, expected, actual.serialize())
    except IllegalMoveException as e:
      assert expected == False, "unexpected failure during move %s" % e
