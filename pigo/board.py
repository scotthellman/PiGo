import numpy as np
import enum
from bitarray import bitarray

class Player(enum.IntEnum):
    BLACK = 1
    WHITE = 2

class BoardState:
    #MUTABLE!

    def __init__(self, size, komi, hasher):
        self.board = np.zeros((size,size), dtype=np.int8)
        self.komi = komi
        self.player = Player.BLACK
        self.hasher = hasher
        self.hashval = hasher.initial

    def __str__(self):
        char_lookup = ["-","@","O"]
        result = "\n".join(["".join([char_lookup[r] for r in row]) for row in self.board])
        return result

    def bithash(self):
        return self.hashval

    def copy(self):
        copied = BoardState(self.board.shape[0], self.komi, self.hasher)
        copied.board = np.copy(self.board)
        copied.hashval = bitarray(self.hashval)
        copied.player = self.player
        return copied

    def mutate_piece(self, x, y, new_val):
        #actually alters the board
        previous_val = self.board[x,y]
        self.board[x,y] = new_val
        if previous_val != 0:
            self.hashval = self.hasher.update_hash(self.hashval, x, y, previous_val)
        if new_val != 0:
            self.hashval = self.hasher.update_hash(self.hashval, x, y, new_val)

    def place_piece(self, x, y, new_val):
        #assumes legal, ignoring ko 
        #suicide will not change board

        #conjectural placement
        self.mutate_piece(x, y, new_val)

        #calculate liberties of this group

        #check neighbors
        for n in self.get_neighbors(x, y):
            if self.board[n[0], n[1]] == 0:
                continue
            if self.board[n[0], n[1]] == self.player:
                continue
            group, liberties = self.find_group(*n)
            #potentialy redundant check
            if liberties == 0:
                for pos in group:
                    self.mutate_piece(pos[0], pos[1], 0)

        _, liberties = self.find_group(x,y)
        if liberties == 0:
            self.mutate_piece(x, y, 0)
            return

        pass

    def get_neighbors(self, x, y):
        current = (x,y)
        size = self.board.shape[0]
        directions = [-1,1]
        possible = []
        for d in directions:
            for idx in range(2):
                candidate = list(current)
                candidate[idx] += d
                if candidate[0] < 0 or candidate[0] >= size or candidate[1] < 0 or candidate[1] >= size:
                    continue
                possible.append(tuple(candidate))
        return possible

    def find_group(self, x, y):
        group_stack = [(x,y)]
        color = self.board[x,y]
        seen = set(group_stack)
        group = set(group_stack)
        liberties = 0
        while len(group_stack) > 0:
            pos = group_stack.pop()
            for n in self.get_neighbors(*pos):
                if n not in seen:
                    if self.board[n[0], n[1]] == color:
                        seen.add(n)
                        group.add(n)
                        group_stack.append(n)
                    elif self.board[n[0], n[1]] == 0:
                        liberties += 1
        return group, liberties


class Zobrist:

    def __init__(self, size, length=64):
        #TODO: set seed then we can not worry about multiple copies
        #TODO: and/or make it a singleton
        self.size = size
        self.length = length
        positions = []
        for i in range(size*size):
            elements = []
            for element in Player:
                elements.append(bitarray(list(np.random.randint(2, size=length))))
            positions.append(elements)
        self.bitstrings = positions

    @property
    def initial(self):
        return bitarray([0]*self.length)

    def update_hash(self, hashval, i, j, val):
        return hashval ^ self.bitstrings[i + self.size * j][val - 1]



class Board:

    def __init__(self, size, komi=6.5):
        self.komi = komi
        self.size = size
        self.hasher = Zobrist(size)

    def start(self):
        # Returns a representation of the starting state of the game.
        return BoardState(self.size, self.komi, self.hasher)

    def current_player(self, state):
        return state.player

    def next_state(self, state, play):
        # Takes the game state, and the move to be applied.
        # Returns the new game state.
        # Doesn't check legality
        #this logic prob belongs in state
        state.place_piece(play[0], play[1], state.player)
        if state.player == Player.BLACK:
            state.player = Player.WHITE
        else:
            state.player = Player.BLACK
        return state

    def legal_plays(self, state, history):
        # Takes a sequence of game states representing the full
        # game history, and returns the full list of moves that
        # are legal plays for the current player.
        #For now, a play is just (Int, Int)
        legal = []

        for i in range(self.size):
            for j in range(self.size):
                if state.board[i,j] != 0:
                    continue
                #tentatively place piece for next checks
                projected_state = state.copy()
                projected_state.place_piece(i, j, projected_state.player)

                #check for suicide
                if projected_state.board[i,j] == 0:
                    continue

                #check for ko
                if projected_state.bithash() in history:
                    continue

                legal.append((i,j))
        return legal

    def winner(self, state_history):
        # Takes a sequence of game states representing the full
        # game history.  If the game is now won, return the player
        # number.  If the game is still ongoing, return zero.  If
        # the game is tied, return a different distinct value, e.g. -1.
        pass


if __name__ == "__main__":
    board = Board(5)
    state = board.start()
    print(state)
    history = [state.bithash()]
    ko = [(2,2),
          (3,2),
          (3,3),
          (2,3),
          (3,1),
          (2,1),
          (4,2),
          (1,2),
          (0,0),
          (3,2),
          (2,2)]
    for move in ko:
        legal_moves = board.legal_plays(state, history)
        print(legal_moves)
        print(move)
        assert move in legal_moves
        state = board.next_state(state, move)
        history.append(state.bithash())
        print(state)
