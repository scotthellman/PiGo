import mc
import board

def run():
    brd = board.Board(5, komi=0)
    simulator = mc.MonteCarlo(brd, time=5)
    state = brd.start()
    simulator.update(state)
    while brd.winner(state, [s.bithash() for s in simulator.states]) == 0:
        print(state)
        move = simulator.get_play()
        state = brd.next_state(state, move)
        simulator.update(state)
        print([s.bithash() for s in simulator.states][-2:])
    print("winner was", brd.winner(state, [s.bithash() for s in simulator.states]))
    print(state)

if __name__ == "__main__":
    run()
