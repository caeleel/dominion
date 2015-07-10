import random
import copy

class Card(object):
    def __init__(self, game):
        self.game = game

    def is_playable(self):
        return False

    def can_block(self):
        return False

    def play(self, payload):
        raise NotImplementedError

    def reacts_to(self):
        return []

    def is_reaction(self):
        return False

    def is_action(self):
        return False

    def is_attack(self):
        return False

    def is_treasure(self):
        return False

    def is_victory(self):
        return False

    def cost(self):
        return 0

    def points(self):
        return 0

    def value(self):
        return 0

    def text(self):
        return ""

    def dict(self):
        type = None
        if self.is_reaction():
            type = "Action - Reaction"
        elif self.is_attack():
            type = "Action - Attack"
        elif self.is_treasure():
            type = "Treasure"
        elif self.is_victory():
            type = "Victory"
        elif self.is_action():
            type = "Action"

        return {
            'name': self.__class__.__name__,
            'value': self.value(),
            'cost': self.cost(),
            'points': self.points(),
            'text': self.text(),
            'type': type,
        }

class Treasure(Card):
    def is_treasure(self):
        return True

    def is_playable(self):
        return True

    def play(self, payload):
        self.game.add_money(self.value())
        return {}

class Victory(Card):
    def is_victory(self):
        return True

class Action(Card):
    def is_playable(self):
        return True

    def is_action(self):
        return True

class Reaction(Action):
    def is_reaction(self):
        return True

class Attack(Action):
    def is_attack(self):
        return True

    def preplay(self, payload):
        pass

    def resolve(self, pid, blocked):
        for player in self.waiting_players:
            if player.id == pid:
                if not blocked:
                    self.to_attack.append(player)
                self.waiting_players.remove(player)
                break
        if not self.waiting_players:
            self.attack(self.to_attack)

    def play(self, payload):
        self.preplay(payload)
        self.waiting_players = set()
        self.to_attack = []

        for player in self.game.opponents():
            deck = player.deck
            for c in deck.hand:
                if 'attack' in c.reacts_to():
                    self.waiting_players.add(player)

        if self.waiting_players:
            self.game.callback_reaction(self.resolve, list(self.waiting_players), 'attack')
        else:
            self.attack(self.game.opponents())
        return {}

class Estate(Victory):
    def cost(self):
        return 2

    def points(self):
        return 1

class Duchy(Victory):
    def cost(self):
        return 5

    def points(self):
        return 3

class Province(Victory):
    def cost(self):
        return 8

    def points(self):
        return 6

class Curse(Card):
    def points(self):
        return -1

class Copper(Treasure):
    def value(self):
        return 1

class Silver(Treasure):
    def cost(self):
        return 3

    def value(self):
        return 2

class Gold(Treasure):
    def cost(self):
        return 6

    def value(self):
        return 3

class Deck(object):
    HAND_SIZE = 5

    def __init__(self, player, game):
        self.discard = []
        self.hand = []
        self.tmp_zone = []
        self.library = []
        self.player = player
        self.game = game
        for i in xrange(7):
            game.gain(self, 'Copper')
        for i in xrange(3):
            game.gain(self, 'Estate')

        self.shuffle()
        self.redraw()

    def size(self):
        return len(self.library) + len(self.tmp_zone) + len(self.discard) + len(self.hand)

    def score(self):
        total = 0
        for card in self.library + self.discard + self.hand:
            total += card.points()
        return total

    def dict(self):
        hand = sorted([x.dict() for x in self.hand], key=lambda x: x.get('cost'))
        discard = [x.dict() for x in self.discard]
        return {
            'hand': hand,
            'discard': discard,
            'library_size': len(self.library),
        }

    def hand_names(self):
        return [card.__class__.__name__ for card in self.hand]

    def redraw(self):
        self.discard += self.hand
        self.discard += self.tmp_zone
        self.hand = []
        self.tmp_zone = []
        self.draw(Deck.HAND_SIZE)

    def gain(self, card):
        self.discard.append(card)

    def find_card_in_hand(self, card):
        for c in self.hand:
            if c.__class__.__name__ == card.get('name'):
                return c
        return None

    def find_card_in_discard(self, card):
        for c in self.discard:
            if c.__class__.__name__ == card.get('name'):
                return c
        return None

    def find_card_in_tmp_zone(self, card):
        for c in self.tmp_zone:
            if c.__class__.__name__ == card.get('name'):
                return c
        return None

    def discard_hand(self, card):
        c = self.find_card_in_hand(card)
        if not c:
            return None

        self.discard.append(c)
        self.hand.remove(c)
        return c

    def trash_hand(self, card):
        c = self.find_card_in_hand(card)
        if not c:
            return None

        self.game.trash.append(c)
        self.hand.remove(c)
        return c

    def trash_tmp_zone(self, card):
        c = self.find_card_in_tmp_zone(card)
        if not c:
            return False

        self.game.trash.append(c)
        self.tmp_zone.remove(c)
        return True

    def peek(self, shuffle=True):
        if not self.library and shuffle:
            self.shuffle()
        if not self.library:
            return None
        return self.library[-1]

    def discard_top(self):
        if self.peek(False) is None:
            return False
        self.discard.append(self.library.pop())
        return True

    def discard_to_library(self, card):
        c = self.find_card_in_discard(card)
        if not c:
            return None

        self.library.append(c)
        self.discard.remove(c)
        return c

    def discard_to_hand(self, card):
        c = self.find_card_in_discard(card)
        if not c:
            return None

        self.hand.append(c)
        self.discard.remove(c)
        return c

    def hand_to_library(self, card):
        c = self.find_card_in_hand(card)
        if not c:
            return None

        self.library.append(c)
        self.hand.remove(c)
        return c

    def play(self, card, payload):
        card = self.find_card_in_hand(card)
        if not card:
            return {'error': 'Card not in hand'}
        if not card.is_playable():
            return {'error': "That's not a card you can play"}
        if not card.is_treasure() and self.player.actions < 1:
            return {'error': 'No actions remaining'}
        if self.game.state not in ('action', 'buy'):
            return {'error': 'Cannot play cards right now'}
        if self.game.state == 'action' and not card.is_action():
            return {'error': 'Must play an action'}
        if self.game.state == 'buy' and not card.is_treasure():
            return {'error': 'Must play a treasure card'}
        self.tmp_zone.append(card)
        self.hand.remove(card)
        result = card.play(payload)

        if 'error' not in result:
            self.game.log.append({
                'pid': self.game.active_player.id,
                'action': 'play',
                'card': card.__class__.__name__,
                'payload': payload,
                'result': result,
            })
            if not card.is_treasure():
                self.player.actions -= 1
        else:
            self.tmp_zone.remove(card)
            self.hand.append(card)
        return result

    def draw(self, n=1):
        for i in xrange(n):
            if self.library:
                self.hand.append(self.library.pop())
                continue
            if self.discard:
                self.shuffle()
                self.hand.append(self.library.pop())
                continue
            break

    def value(self):
        return sum([x.value() for x in self.hand])

    def points(self):
        deck = self.hand + self.discard + self.library
        return sum([x.value() for x in deck])

    def shuffle(self):
        self.library = self.discard
        n = len(self.library)
        for i in xrange(n):
            j = random.randint(i, n-1)
            x = self.library[j]
            self.library[j] = self.library[i]
            self.library[i] = x
        self.discard = []
