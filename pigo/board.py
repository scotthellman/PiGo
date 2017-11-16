import numpy as np
import enum
import struct
from bitarray import bitarray

class Player(enum.IntEnum):
    BLACK = 1
    WHITE = 2
PASS = (-1, -1)

class BoardState:
    #MUTABLE!

    def __init__(self, size, komi, hasher):
        self.board = np.zeros((size,size), dtype=np.int8)
        self.groups = np.ones((size,size)) * -1
        self.liberties = {}
        self.komi = komi
        self.player = Player.BLACK
        self.hasher = hasher
        self.hashval = hasher.initial
        self.captures = [0,0]
        self.turns = 0

    def __str__(self):
        char_lookup = ["-","@","O"]
        result = "\n".join(["".join([char_lookup[r] for r in row]) for row in self.board])
        return result

    def __hash__(self):
        return self.hashval

    def __eq__(self, other):
        #quick check first
        if self.hashval != other.hashval:
            return False
        return (np.all(self.board == other.board) &
                (self.komi == other.komi) &
                (self.player == other.player) &
                (self.captures == other.captures))

    def bithash(self):
        return self.hashval

#    def __hash__(self):
#        return hash(self.hashval)

    def copy(self):
        copied = BoardState(self.board.shape[0], self.komi, self.hasher)
        copied.board = np.copy(self.board)
        copied.groups = np.copy(self.groups)
        copied.liberties = {k:set(v) for k,v in self.liberties.items()}
        #NOTE: This really assumes we're dealing with a primitive
        copied.hashval = self.hashval
        copied.player = self.player
        copied.captures = self.captures[:]
        copied.turns = self.turns
        return copied

    def mutate_piece(self, x, y, new_val):
        #actually alters the board
        previous_val = self.board[x,y]
        self.board[x,y] = new_val
        if previous_val != 0:
            self.hashval = self.hasher.update_hash(self.hashval, x, y, previous_val)
        if new_val != 0:
            self.hashval = self.hasher.update_hash(self.hashval, x, y, new_val)

    def unify_groups(self, x, y):
        group, liberties, __ = self.find_group(x, y)
        #TODO: this could be faster
        labels = set(self.groups[g] for g in group)
        new_label = np.min([self.groups[g] for g in group])
        for l in labels:
            #del or just zero out?
            if l in self.liberties:
                del self.liberties[l]
        self.liberties[new_label] = liberties
        for g in group:
            self.groups[g] = new_label

    def placement_effects(self, x, y, new_val):
        suicide = None
        captures = set()
        captured_groups = set()

        #special case for when a lone suicidal stone is placed
        num_opposing = 0
        num_neighbors = 0
        for n in self.get_neighbors(x, y):
            num_neighbors += 1
            if self.board[n[0], n[1]] == 0:
                continue
            if self.board[n[0], n[1]] == self.player:
                liberties = self.liberties[self.groups[n]]
                if suicide is None and len(liberties) == 1 and list(liberties)[0] == n:
                    suicide = True
                else:
                    suicide = False
                continue
            num_opposing += 1
            group = self.groups[n]
            if len(self.liberties[group]) == 1:
                captured_groups.add(group)
                #TODO: this prob should be broken out
                xs,ys = np.where(self.groups == group)
                for pos in zip(xs,ys):
                    captures.add(pos)

        #print("A",self.board)
        if num_opposing == num_neighbors:
            suicide = True

        if len(captures) == 0 and suicide is not None and suicide:
            suicide = True
        else:
            suicide = False

        return suicide, captures, captured_groups

    def place_piece(self, x, y, new_val):
        #assumes legal, ignoring ko 
        #suicide will not change board

        suicide, captures, captured_groups = self.placement_effects(x, y, new_val)

        #check neighbors
        if suicide:
            return

        self.captures[self.board[x,y] - 1] += len(captures)

        for captured in captures:
            self.mutate_piece(captured[0], captured[1], 0)
            #return liberties
            for n in self.get_neighbors(*captured):
                if self.board[n] == new_val:
                    self.liberties[self.groups[n]].add(n)
        #self.board[list(captures)] = 0
        #print("B",self.board)
        #TODO: This is wrong!
        for group in captured_groups:
            self.groups[np.where(self.groups == group)] = -1
            del self.liberties[group]

        self.mutate_piece(x, y, new_val)
        self.groups[x,y] = self.turns
        self.unify_groups(x, y)
        self.turns += 1

        #TODO: find a more elegant place for this
        for n in self.get_neighbors(x, y):
            if n not in captures:
                if self.board[n] !=0 and self.board[n] != self.player:
                    self.liberties[self.groups[n]].discard((x,y))

    def calculate_score(self):
        score = 0
        seen = set()
        colors = set((int(Player.BLACK), int(Player.WHITE)))
        for i,row in enumerate(self.board):
            for j,val in enumerate(row):
                if val == 0:
                    group, liberties, border =  self.find_group(i,j)
                    seen.update(group)
                    neighbor_colors = border & colors
                    if len(neighbor_colors) == 1:
                        points = len(group)
                        if int(Player.WHITE) in neighbor_colors:
                            points *= -1
                        score += points
        score += self.captures[0] - self.captures[1]
        score -= self.komi
        return score

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
        liberties = set()
        border_colors = set()
        while len(group_stack) > 0:
            pos = group_stack.pop()
            for n in self.get_neighbors(*pos):
                if n not in seen:
                    border_colors.add(self.board[n[0], n[1]])
                    if self.board[n] == color:
                        seen.add(n)
                        group.add(n)
                        group_stack.append(n)
                        continue
                    elif self.board[n] == 0:
                        liberties.add(n)
        return group, liberties, border_colors


class Zobrist:

    def __init__(self, size, length=64):
        #TODO: set seed then we can not worry about multiple copies
        #TODO: and/or make it a singleton
        #TODO: now we're using ints and its' all a mess
        self.size = size
        self.length = length
        positions = []
        for i in range(size*size):
            elements = []
            for element in Player:
                h = list(np.random.randint(2, size=length))
                val = "0b" + "".join((str(v) for v in h))
                elements.append(int(val,2))
            positions.append(elements)
        self.bitstrings = positions

    @property
    def initial(self):
        return 0

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
        state = state.copy()
        if play != PASS:
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
        legal = [PASS]

        for i in range(self.size):
            for j in range(self.size):
                if state.board[i,j] != 0:
                    continue
                #tentatively place piece for next checks

                #projected_state = state.copy()
                suicide, captures, _ = state.placement_effects(i, j, state.player)
                #projected_state.place_piece(i, j, projected_state.player)

                #check for suicide
                if suicide:
                    continue
                #check for ko
                if len(captures) == 0:
                    state.mutate_piece(i, j, state.player)
                    ko = state.bithash() in history
                    state.mutate_piece(i, j, 0)
                else:
                    projected_state = state.copy()
                    projected_state.place_piece(i, j, projected_state.player)
                    ko = projected_state.bithash() in history
                if ko:
                    continue

                legal.append((i,j))
        return legal

    def projected_winner(self, current_state):
        score = current_state.calculate_score()
        if score > 0:
            return int(Player.BLACK)
        else:
            return int(Player.WHITE)


    def winner(self, current_state, state_history):
        # Takes a sequence of game states representing the full
        # game history.  If the game is now won, return the player
        # number.  If the game is still ongoing, return zero.  If
        # the game is tied, return a different distinct value, e.g. -1.
        if len(state_history) > 3:
            if state_history[-1] == state_history[-2] == state_history[-3]:
                score = current_state.calculate_score()
                if score > 0:
                    return int(Player.BLACK)
                else:
                    return int(Player.WHITE)
        return 0


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
    #small_game = ko[:-1]
    #small_game.append((2,0))
    corner = [(0,1),
              (2,2),
              (1,0),
              (0,0)]
    for move in ko:
        print("-"*20)
        legal_moves = board.legal_plays(state, history)
        print(legal_moves)
        print(move)
        assert move in legal_moves
        state = board.next_state(state, move)
        history.append(state.bithash())
        print(history[-3:])
        print(state)
        print(state.groups)
    print(state.calculate_score())

