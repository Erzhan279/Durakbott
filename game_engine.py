import random

RANKS = ["6","7","8","9","10","J","Q","K","A"]
SUITS = ["♠","♥","♦","♣"]

class Game:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.players = []       # list of user_id
        self.hands = {}         # user_id -> list of cards
        self.deck = []
        self.trump = None
        self.started = False
        self.table = []         # current table cards (pairs)
        self.turn_index = 0     # index in players for whose turn
        self.history = []

    def add_player(self, user_id):
        if self.started:
            return False
        if user_id not in self.players:
            self.players.append(user_id)
            self.hands[user_id] = []
        return True

    def remove_player(self, user_id):
        if user_id in self.players:
            self.players.remove(user_id)
            self.hands.pop(user_id, None)
            return True
        return False

    def deal(self):
        # Create deck and shuffle
        self.deck = [r + s for r in RANKS for s in SUITS]
        random.shuffle(self.deck)
        self.trump = self.deck[-1][-1]  # last card suit char (like '♠')
        # Give each player 6 cards
        for p in self.players:
            self.hands[p] = []
        for _ in range(6):
            for p in self.players:
                if self.deck:
                    self.hands[p].append(self.deck.pop())
        self.started = True
        self.turn_index = 0
        self.table = []
        self.history = []

    def get_player_hand(self, user_id):
        return self.hands.get(user_id, [])

    def serialize_for_frontend(self):
        # return minimal game state suitable for frontend
        return {
            "players": self.players,
            "hands_count": {str(k): len(v) for k,v in self.hands.items()},
            "trump": self.trump,
            "deck_count": len(self.deck),
            "started": self.started,
            "table": self.table,
            "turn_user": self.players[self.turn_index] if self.players else None
        }

GAMES = {}

def get_game(chat_id):
    if chat_id not in GAMES:
        GAMES[chat_id] = Game(chat_id)
    return GAMES[chat_id]
