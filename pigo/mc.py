import datetime
import random
import numpy as np

class MonteCarlo(object):
    def __init__(self, board, **kwargs):
        # Takes an instance of a Board and optionally some keyword
        # arguments.  Initializes the list of game states and the
        # statistics tables.
        self.board = board
        self.states = []

        seconds = kwargs.get('time', 30)
        self.calculation_time = datetime.timedelta(seconds=seconds)
        self.max_moves = kwargs.get('max_moves', 100)
        self.wins = {}
        self.plays = {}

        self.C = kwargs.get('C', 1.4)


    def update(self, state):
        # Takes a game state, and appends it to the history.
        self.states.append(state)

    def get_play(self):
        # Causes the AI to calculate the best move from the
        # current game state and return it.
        self.max_depth = 0
        state = self.states[-1]
        player = self.board.current_player(state)
        legal = self.board.legal_plays(state, [s.bithash() for s in self.states])

        if not legal:
            return
        if len(legal) == 1:
            return legal[0]

        games = 0
        begin = datetime.datetime.utcnow()
        while datetime.datetime.utcnow() - begin < self.calculation_time:
            self.run_simulation()
            games += 1

        moves_states = [(p, self.board.next_state(state, p)) for p in legal]

        print(games,datetime.datetime.utcnow() - begin)


        percent_wins, move = max(
                (self.wins.get((player, S), 0) / self.plays.get((player, S), 1),
                 p)
                for p, S in moves_states
        )

        for x in sorted(
            ((100 * self.wins.get((player, S), 0) /
              self.plays.get((player, S), 1),
              self.wins.get((player, S), 0),
              self.plays.get((player, S), 0), p)
             for p, S in moves_states),
            reverse=True
        ):
            print("{3}: {0:.2f}% ({1} / {2})".format(*x))

        print("Maximum depth searched:", self.max_depth)
        print(move)

        return move


    def run_simulation(self):
        # Plays out a "random" game from the current position,
        # then updates the statistics tables with the result.
        plays, wins = self.plays, self.wins

        visited_states = set()
        states_copy = self.states[:]
        state = states_copy[-1]
        player = self.board.current_player(state)

        expand = True

        for t in range(self.max_moves):
            legal = self.board.legal_plays(state, [s.bithash() for s in states_copy])
            moves_states = [(p, self.board.next_state(state, p)) for p in legal]
            unseen = [m for m in moves_states if (player, m[0]) not in plays]
            #if all(plays.get((player, S)) for p, S in moves_states):
            if len(unseen) == 0:
                # If we have stats on all of the legal moves here, use them.
                log_total = np.log(
                    sum(plays[(player, S)] for p, S in moves_states))
                value, move, state = max(
                    ((wins[(player, S)] / plays[(player, S)]) +
                     self.C * sqrt(log_total / plays[(player, S)]), p, S)
                    for p, S in moves_states
                )
            else:
                # Otherwise, just make an arbitrary decision from paths we have not tried
                #TODO: this is probably wrong
                move, state = random.choice(unseen)

            states_copy.append(state)

            if expand and (player, state) not in plays:
                expand = False
                plays[(player, state)] = 0
                wins[(player, state)] = 0
                if t > self.max_depth:
                    self.max_depth = t

            visited_states.add((player, state))

            player = self.board.current_player(state)
            winner = self.board.winner(state, [s.bithash() for s in states_copy])
            if winner:
                break
        else:
            winner = self.board.projected_winner(state)

        for player, state in visited_states:
            if (player, state) not in plays:
                continue
            plays[(player, state)] += 1
            if int(player) == winner:
                wins[(player, state)] += 1

