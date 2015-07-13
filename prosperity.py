from cards_and_decks import *
from base_set import *

class Loan(Treasure):
    def cost(self):
        return 3

    def value(self):
        return 1

    def text(self):
        return [
            "When you play this, reveal cards from your deck until you " + \
            "reveal a Treasure. Discard or it trash it. Discard the other cards."
        ]

    def discard_or_trash(self, pid, payload):
        if payload.get('discard'):
            self.game.active_deck.discard.append(self.revealed)
        else:
            self.game.active_deck.discard.append(self.revealed[:-1])
            self.game.trash.append(self.revealed[-1])
        return {'clear': True}

    def preplay(self, payload):
        deck = self.game.active_deck
        card = None
        self.revealed = []
        while True:
            card = deck.peek()
            if card is None:
                break
            self.revealed.append(deck.library.pop())
            if card.is_treasure():
                break

        if card is not None:
            self.game.add_callback(
                'discard_or_trash',
                self.discard_or_trash,
                [self.game.active_player]
            )
        return {'revealed': [x.dict() for x in self.revealed]}

class TradeRoute(Reaction):
    def cost(self):
        return 3

    def text(self):
        return [

        ]

    def play(self, payload):
        pass

class Watchtower(Reaction):
    def cost(self):
        return 3

    def text(self):
        return [

        ]

    def play(self, payload):
        pass

class Bishop(Action):
    def cost(self):
        return 4

    def text(self):
        return [
            "+$1",
            "+1 VP token",
            "Trash a card from your hand. +VP tokens equal to half its cost " + \
            "in coins, rounded down. Each other player may trash a card " + \
            "from his hand."
        ]

    def maybe_trash(self, pid, payload, gain_vp=False):
        if 'card' not in payload:
            return {'error': 'Parameter card is required.'}
        card = payload['card']
        if not isinstance(card, dict):
            return {'error': 'Card is invalid.'}
        deck = self.game.players[pid].deck
        c = deck.trash_hand(card)
        if c is None:
            return {'error': 'Card {0} not found in hand'.format(card.get('name'))}
        if gain_vp:
            self.game.players[pid].victory_tokens += c.cost() / 2
        return {}

    def play(self, payload):
        result = self.maybe_trash(self.game.active_player.id, payload, True)
        if 'error' in result:
            return result
        self.game.add_callback(
            'maybe_trash',
            self.maybe_trash,
            self.game.opponents()
        )
        return result

class Monument(Action):
    def cost(self):
        return 4

    def text(self):
        return [
            "+$2",
            "+1 VP token."
        ]

    def play(self, payload):
        self.game.active_player.victory_tokens += 1
        self.game.add_money(2)
        return {}

class Quarry(Treasure):
    def cost(self):
        return 4

    def text(self):
        return [

        ]

    def play(self, payload):
        pass

class Talisman(Treasure):
    def cost(self):
        return 4

    def text(self):
        return [

        ]

    def play(self, payload):
        pass

class WorkersVillage(Action):
    def cost(self):
        return 4

    def text(self):
        return [
            "+1 Card",
            "+2 Actions",
            "+1 Buy",
        ]

    def play(self, payload):
        self.game.active_deck.draw()
        self.game.add_actions(2)
        self.game.add_buys(1)
        return {}

class City(Action):
    def cost(self):
        return 5

    def text(self):
        return [

        ]

    def play(self, payload):
        pass

class Contraband(Treasure):
    def cost(self):
        return 5

    def text(self):
        return [

        ]

    def play(self, payload):
        pass

class CountingHouse(Action):
    def cost(self):
        return 5

    def text(self):
        return [

        ]

    def play(self, payload):
        pass

class Mint(Action):
    def cost(self):
        return 5

    def text(self):
        return [

        ]

    def play(self, payload):
        pass

class Mountebank(Attack):
    def cost(self):
        return 5

    def text(self):
        return [

        ]

    def play(self, payload):
        pass

class Rabble(Attack):
    def cost(self):
        return 5

    def text(self):
        return [

        ]

    def play(self, payload):
        pass

class RoyalSeal(Treasure):
    def cost(self):
        return 5

    def text(self):
        return [
            "While this is in play, when you gain a card, you may put that " + \
            "card on top of your deck."
        ]

    def put_top(self, pid, payload):
        if payload.get('put_top'):
            deck = self.game.active_deck
            deck.library.append(deck.discard.pop())
        return {'clear': True}

    def effect(self):
        self.game.add_callback('put_top', self.put_top, [self.game.active_player])

    def preplay(self, payload):
        self.game.on_buy(lambda x: True, self.effect)
        return {}

class Vault(Action):
    def cost(self):
        return 5

    def text(self):
        return [
            "+2 Cards",
            "Discard any number of cards. +$1 per card discarded.  Each " + \
            "other player may discard 2 cards. If he does, he draws a card.",
        ]

    def cycle(self, pid, payload):
        if 'cards' not in payload:
            return {'error': 'Parameter cards is required.'}
        if not isinstance(payload['cards'], list):
            return {'error': 'Cards must be list.'}
        if not payload['cards']:
            return {'clear': True}
        if len(payload['cards'] != 2):
            return {'error': 'Must discard exactly 2 cards, or none.'}

        deck = self.game.players[pid].deck
        cards = []
        for card in payload['cards']:
            if not isinstance(card, dict):
                deck.hand += cards
                return {'error': 'Invalid card'}
            c = deck.find_card_in_hand(card)
            if c is None:
                deck.hand += cards
                return {'error': 'Card {0} not in hand'.format(card.get('name'))}
            cards.append(c)
            deck.hand.remove(c)

        deck.discard += cards
        deck.draw()
        return {'clear': True}

    def play(self, payload):
        deck = self.game.active_deck

        if 'cards' not in payload:
            return {'error': 'No cards to discard.'}
        if not isinstance(payload['cards'], list):
            return {'error': 'Cards must be list.'}

        cards = []
        for card in payload['cards']:
            if not isinstance(card, dict):
                deck.hand += cards
                return {'error': 'Invalid card'}
            c = deck.find_card_in_hand(card)
            if c is None:
                deck.hand += cards
                return {'error': 'Card {0} not in hand'.format(card.get('name'))}
            cards.append(c)
            deck.hand.remove(c)

        deck.discard += cards
        self.game.add_money(len(cards))
        self.game.add_callback('cycle', self.cycle, self.game.opponents())
        return {}

class Venture(Treasure):
    def cost(self):
        return 5

    def value(self):
        return 1

    def text(self):
        return [
            "When you play this, reveal cards from your deck until you " + \
            "reveal a Treasure. Discard the other cards. Play that Treasure."
        ]

    def preplay(self, payload):
        revealed = []
        deck = self.game.active_deck
        while True:
            c = deck.peek()
            if c is None:
                break
            deck.library.pop()
            if c.is_treasure():
                deck.tmp_zone.append(c)
                self.game.log.append({
                    'pid': self.game.active_player.id,
                    'action': 'venture',
                    'played': c.dict(),
                })
                c.play({})
                break
            revealed.append(c)
        deck.discard += revealed
        return {}

class Goons(Militia):
    def cost(self):
        return 6

    def text(self):
        return [
            "+1 Buy",
            "+$2",
            "Each other player discards down to 3 cards in hand. " + \
            "While this is in play, when you buy a card, +1 VP token.",
        ]

    def effect(self):
        self.game.active_player.victory_tokens += 1

    def preplay(self, payload):
        self.game.add_buys(1)
        self.game.add_money(2)
        self.game.on_buy(lambda x: True, self.effects)
        return {}

class GrandMarket(Action):
    def cost(self):
        return 6

    def text(self):
        return [
            "+1 Card",
            "+1 Action",
            "+1 Buy",
            "+$2",
            "You can't buy this if you have any Copper in play.",
        ]

    def on_buy(self):
        c = self.game.active_deck.find_card_in_tmp_zone({'name': 'Copper'})
        if c is not None:
            return {'error': 'Cannot buy Grand Market when Copper in play.'}
        else:
            return {}

    def play(self, payload):
        self.game.active_deck.draw()
        self.game.add_actions(1)
        self.game.add_buys(1)
        self.game.add_money(2)
        return {}

class Hoard(Treasure):
    def cost(self):
        return 6

    def value(self):
        return 2

    def text(self):
        return [
            "While this is in play, when you buy a Victory card, gain a Gold."
        ]

    def fits_criteria(self, card):
        return card.is_victory()

    def effect(self):
        self.game.gain(self.game.active_deck, 'Gold')

    def preplay(self, payload):
        self.game.on_buy(self.fits_criteria, self.effect)
        return {}

class Bank(Treasure):
    def cost(self):
        return 7

    def value(self):
        deck = self.game.active_deck
        val = 0
        if not deck:
            return val
        return len([x for x in deck.tmp_zone if x.is_treasure()])

    def text(self):
        return [
            "When you play this, it's worth $1 per Treasure card you " + \
            "have in play (counting this)."
        ]

class Expand(Remodel):
    def __init__(self, game):
        super(Expand, self).__init__(game, 3)

    def cost(self):
        return 7

class Forge(Action):
    def cost(self):
        return 7

    def text(self):
        return [
            "Trash any number of cards from your hand. Gain a card with " + \
            "cost exactly equal to the total cost in coins of the trashed cards."
        ]

    def play(self, payload):
        deck = self.game.active_deck

        if 'cards' not in payload:
            return {'error': 'No cards to trash.'}
        if not isinstance(payload['cards'], list):
            return {'error': 'Cards must be list.'}

        if 'gain' not in payload:
            return {'error': 'No card gained.'}
        gain = payload['gain']
        if not isinstance(gain, dict):
            return {'error': 'Gained card invalid.'}
        name = gain.get('name')
        gained = self.game.card_from_name(name)
        if gained is None:
            return {'error': 'No such card {0}'.format(name)}

        total_cost = 0
        cards = []
        for card in payload['cards']:
            if not isinstance(card, dict):
                deck.hand += cards
                return {'error': 'Invalid card'}
            c = deck.find_card_in_hand(card)
            if c is None:
                deck.hand += cards
                return {'error': 'Card {0} not in hand'.format(card.get('name'))}
            total_cost += c.cost()
            cards.append(c)
            deck.hand.remove(c)

        if gained.cost() != total_cost:
            deck.hand += cards
            return {'error': 'Gained card must have equal cost to sum of trashed cards.'}
        c = self.game.gain(deck, name)
        if c is None:
            deck.hand += cards
            return {'error': 'Could not gain {0}'.format(name)}

        self.game.trash += cards
        return {}

class KingsCourt(ThroneRoom):
    def __init__(self, game):
        super(KingsCourt, self).__init__(game, 2)

    def cost(self):
        return 7

class Peddler(Action):
    def cost(self):
        cost = 8
        deck = self.game.active_deck
        if not deck:
            return cost
        for card in deck.tmp_zone:
            if card.is_action():
                cost -= 2
        return max(cost, 0)

    def text(self):
        return [
            "+1 Card",
            "+1 Action",
            "+$1",
            "During your Buy phase, this costs $2 less per Action card " + \
            "you have in play, but not less than $0."
        ]

    def play(self, payload):
        self.game.active_deck.draw()
        self.game.add_actions(1)
        self.game.add_money(1)
        return {}

class Platinum(Treasure):
    def cost(self):
        return 9

    def value(self):
        return 5

class Colony(Victory):
    def cost(self):
        return 11

    def points(self):
        return 10
