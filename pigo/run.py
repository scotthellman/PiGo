import mc
import board

def run():
    brd = board.Board(5)
    simulator = mc.MonteCarlo(brd, time=5)
    state = brd.start()
    iteration = 0
    while brd.winner(state, [s.bithash() for s in simulator.states]) == 0:
        print(state)
        simulator.update(state)
        move = simulator.get_play()
        state = brd.next_state(state, move)
        iteration += 1
        if iteration > 5:
            break
    print("winner was", brd.winner(state, [s.bithash() for s in simulator.states]))
    print(state)

if __name__ == "__main__":
    run()
