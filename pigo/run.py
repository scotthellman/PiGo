import mc
import board

def run():
    brd = board.Board(5, komi=0)
    simulator = mc.MonteCarlo(brd, time=15)
    state = brd.start()
    while brd.winner(state, [s.bithash() for s in simulator.states]) == 0:
        print(state)
        simulator.update(state)
        move = simulator.get_play()
        state = brd.next_state(state, move)
    print("winner was", brd.winner(state, [s.bithash() for s in simulator.states]))
    print(state)

if __name__ == "__main__":
    run()
