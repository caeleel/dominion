from cards_and_decks import *

class Duration(Action):
    def is_duration(self):
        return True

    def blocks_attack(self):
        return False

    def play(self, payload):
        dur = self.__class__(self.game)
        result = dur.preplay(payload)
        if 'error' in result:
            return result

        self.game.active_player.durations.append(dur)
        return result

class Embargo(Action):
    def cost(self):
        return 2

    def text(self):
        return [
            "Trash this card. Put an Embargo token on top of a Supply pile. " + \
            "When a player buys a card, he gains a Curse card per Embargo " + \
            "token on that pile."
        ]

    def play(self, payload):
        if 'card' not in payload:
            return {'error': 'No card specified'}
        card = payload['card']
        if not isinstance(card, dict):
            return {'error': 'Card must be dict'}
        c = self.game.card_from_name(card.get('name'))
        if c is None:
            return {'error': 'No such card {0}'.format(card.get('name'))}
        c.embargos += 1
        self.game.add_money(2)
        self.deck.trash_tmp_zone({'name': 'Embargo'})
        return {}

class Haven(Duration):
    def cost(self):
        return 2

    def text(self):
        return [
            "+1 Card",
            "+1 Action",
            "Set aside a card from your hand face down. At the start of your " + \
            "next turn, put it into your hand.",
        ]

    def duration(self):
        self.game.active_deck.hand.append(self.stored)

    def preplay(self, payload):
        if 'card' not in payload:
            return {'error': 'No card specified'}
        card = payload['card']
        if not isinstance(card, dict):
            return {'error': 'Card must be dict'}

        c = self.deck.find_card_in_hand(card)
        if c is None:
            return {'error': 'Card {0} not found in hand'.format(c.get('name'))}
        self.deck.hand.remove(c)
        self.stored = c
        self.game.add_actions(1)
        deck.draw()
        return {}

class LightHouse(Duration):
    def cost(self):
        return 2

    def text(self):
        return [
            "+1 Action",
            "Now and at the start of your next turn: +$1.",
            "While this is in play, when another player plays an Attack card, " + \
            "it doesn't affect you.",
        ]

    def blocks_attack(self):
        return True

    def duration(self):
        self.game.add_money(1)

    def preplay(self, payload):
        self.game.add_actions(1)
        self.game.add_money(1)
        return {}

class NativeVillage(Action):
    def cost(self):
        return 2

    def text(self):
        return [
            "+2 Actions",
            "Choose one: Set aside the top card of your deck face down on " + \
            "your Native Village mat; or put all the cards from your mat " + \
            "into your hand. You may look at the cards on your mat at any " + \
            "time; return them to your deck at the end of the game."
        ]

    def play(self, payload):
        if not payload.get('retrieve'):
            if self.deck.peek():
                deck.native_village.append(self.deck.library.pop())
        else:
            self.deck.hand += deck.native_village
            self.deck.native_village = []
        return {}

class PearlDiver(Action):
    def cost(self):
        return 2

    def text(self):
        return [
            "+1 Card",
            "+1 Action",
            "Look at the bottom card of your deck. You may put it on top.",
        ]

    def put_top(self, payload):
        if payload.get('put_top'):
            deck.library.append(self.deck.library.pop(0))
        return {'clear': True}

    def play(self, payload):
        self.game.add_actions(1)
        self.deck.draw()

        c = self.deck.peek_bottom()
        if c is None:
            return {'card': None}

        self.game.add_callback('put_top', self.put_top, [self.game.active_player])
        return {'card': c.dict()}

class Ambassador(Attack):
    def cost(self):
        return 3

    def attack(self, players):
        for player in players:
            self.game.gain(player.deck, self.saved)

    def preplay(self, payload):
        if 'card' not in payload:
            return {'error': 'No card specified'}
        card = payload['card']
        if not isinstance(card, dict):
            return {'error': 'Card must be dict'}

        self.saved = card
        c = self.deck.find_card_in_hand(card)
        if c is None:
            return {'error': 'Card {0} not found in hand'.format(card.get('name'))}
        if 'count' not in payload:
            return {'error': 'Parameter count is required'}
        count = payload['count']
        if not isinstance(count, int):
            return {'error': 'Count must be integer'}
        if count < 1 or count > 2:
            return {'error': 'Count must be 1 or 2'}
        returned = 0
        for i in xrange(count):
            if self.game.ungain(self.deck, c):
                returned += 1
        return {'returned': returned}

class FishingVillage(Duration):
    def cost(self):
        return 3

    def text(self):
        return [
            "+2 Actions",
            "+$1",
            "At the start of your next turn: +1 Action; +$1.",
        ]

    def duration(self):
        self.game.add_actions(1)
        self.game.add_money(1)

    def preplay(self, payload):
        self.game.add_actions(2)
        self.game.add_money(1)
        return {}

class Lookout(Action):
    def cost(self):
        return 3

    def text(self):
        return [
            "+1 Action",
            "Look at the top 3 cards of your deck. Trash one of them. " + \
            "Discard one of them. Put the other one on top of your deck."
        ]

    def play(self, payload):
        pass

class Smugglers(Action):
    def cost(self):
        return 3

    def text(self):
        return [
            "Gain a copy of a card costing up to $6 that the player to " + \
            "your right gained on his last turn."
        ]

    def play(self, payload):
        pass

class Warehouse(Action):
    def cost(self):
        return 3

    def text(self):
        return [
            "+3 Cards",
            "+1 Action",
            "Discard 3 cards.",
        ]

    def play(self, payload):
        pass

class Caravan(Duration):
    def cost(self):
        return 3

    def text(self):
        return [

        ]

    def play(self, payload):
        pass

class Cutpurse(Attack):
    def cost(self):
        return 3

    def text(self):
        return [

        ]

    def play(self, payload):
        pass

class Island(Action):
    def cost(self):
        return 3

    def text(self):
        return [

        ]

    def is_victory(self):
        return True

    def play(self, payload):
        pass

class Navigator(Action):
    def cost(self):
        return 3

    def text(self):
        return [

        ]

    def play(self, payload):
        pass

class PirateShip(Attack):
    def cost(self):
        return 3

    def text(self):
        return [

        ]

    def play(self, payload):
        pass

class Salvager(Action):
    def cost(self):
        return 3

    def text(self):
        return [

        ]

    def play(self, payload):
        pass

class SeaHag(Attack):
    def cost(self):
        return 3

    def text(self):
        return [

        ]

    def play(self, payload):
        pass

class TreasureMap(Action):
    def cost(self):
        return 3

    def text(self):
        return [

        ]

    def play(self, payload):
        pass

class Bazaar(Action):
    def cost(self):
        return 3

    def text(self):
        return [

        ]

    def play(self, payload):
        pass

class Explorer(Action):
    def cost(self):
        return 3

    def text(self):
        return [

        ]

    def play(self, payload):
        pass

class GhostShip(Attack):
    def cost(self):
        return 3

    def text(self):
        return [

        ]

    def play(self, payload):
        pass

class MerchantShip(Duration):
    def cost(self):
        return 3

    def text(self):
        return [

        ]

    def play(self, payload):
        pass

class Outpost(Duration):
    def cost(self):
        return 3

    def text(self):
        return [

        ]

    def play(self, payload):
        pass

class Tactician(Duration):
    def cost(self):
        return 3

    def text(self):
        return [

        ]

    def play(self, payload):
        pass

class Treasury(Action):
    def cost(self):
        return 3

    def text(self):
        return [

        ]

    def play(self, payload):
        pass

class Wharf(Duration):
    def cost(self):
        return 3

    def text(self):
        return [

        ]

    def play(self, payload):
        pass
