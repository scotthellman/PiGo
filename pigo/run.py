import mc
import board

board = board.Board(5)
simulator = mc.MonteCarlo(board, time=10)
state = board.start()
while board.winner(state, [s.bithash() for s in simulator.states]) == 0:
    print(state)
    simulator.update(state)
    move = simulator.get_play()
    state = board.next_state(state, move)
print("winner was", board.winner(state, [s.bithash() for s in simulator.states]))
print(state)
