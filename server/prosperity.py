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
            self.deck.discard += self.revealed
        else:
            self.deck.discard += self.revealed[:-1]
            self.game.trash.append(self.revealed[-1])
        return {'clear': True}

    def preplay(self, payload):
        card = None
        self.revealed = []
        while True:
            card = self.deck.peek()
            if card is None:
                break
            self.revealed.append(self.deck.library.pop())
            if card.is_treasure():
                break

        if card is not None:
            self.game.add_callback(
                'discard_or_trash',
                self.discard_or_trash,
                [self.deck.player]
            )
        return {'revealed': [x.dict() for x in self.revealed]}

class TradeRoute(Action):
    def cost(self):
        return 3

    def text(self):
        return [
            "+1 Buy",
            "+$1 per token on the Trade Route mat.",
            "Trash a card from your hand.",
            "------",
            "Setup: Put a token on each Victory card Supply pile. When a " + \
            "card is gained from that pile, move the token to the Trade " + \
            "Route mat."
        ]

    def play(self, payload):
        card = payload.get('card')
        if not isinstance(card, dict):
            return {'error': 'Invalid trash card.'}
        c = self.deck.trash_hand(card)
        if c is None:
            return {'error': 'Card {0} not in hand'.format(card.get('name'))}

        self.game.add_buys(1)
        self.game.add_money(len(self.game.victories_gained))
        return {}

class Watchtower(Reaction):
    def cost(self):
        return 3

    def reacts_to(self):
        return ['gain']

    def react(self, pid, payload):
        deck = self.game.players[pid].deck

        if self.gained in deck.discard:
            if payload.get('trash'):
                self.game.trash.append(self.gained)
                deck.discard.remove(self.gained)
            elif payload.get('put_top'):
                deck.library.append(self.gained)
                deck.discard.remove(self.gained)
        return {'clear': True}

    def register_reaction(self, pid, card):
        self.gained = card
        self.game.queue_callback(
            'watchtower:{0}'.format(card.name()),
            self.react,
            [self.game.players[pid]]
        )

    def text(self):
        return [
            "Draw until you have 6 cards in hand.",
            "When you gain a card, you may reveal this from your hand. If " + \
            "you do, either trash that card, or put it on top of your deck.",
        ]

    def play(self, payload):
        while len(self.deck.hand) < 6:
            if not self.deck.draw():
                break
        return {}

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
        return {'clear': True}

    def play(self, payload):
        result = self.maybe_trash(self.deck.player.id, payload, True)
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
        self.deck.player.victory_tokens += 1
        self.game.add_money(2)
        return {}

class Quarry(Treasure):
    def cost(self):
        return 4

    def value(self):
        return 1

    def text(self):
        return [
            "While this is in play, Action cards cost $2 less, but " + \
            "not less than $0."
        ]

    def discount(self, card, cost):
        if card.is_action():
            cost -= 2
        return max(cost, 0)

    def preplay(self, payload):
        self.deck.player.discounts.append(self.discount)
        return {}

class Talisman(Treasure):
    def cost(self):
        return 4

    def value(self):
        return 1

    def text(self):
        return [
            "While this is in play, when you buy a card costing $4 or " + \
            "less that is not a Victory card, gain a copy of it."
        ]

    def effect(self, card):
        self.game.gain(self.deck, card.name())

    def preplay(self, payload):
        self.game.on_buy(
            lambda x: x.effective_cost(self.deck.player) <= 4 and not x.is_victory(),
            self.effect
        )
        return {}

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
        self.deck.draw()
        self.game.add_actions(2)
        self.game.add_buys(1)
        return {}

class City(Action):
    def cost(self):
        return 5

    def text(self):
        return [
            "+1 Card",
            "+2 Actions",
            "If there are one or more empty Supply piles, +1 Card. " + \
            "If there are two or more, +$1 and +1 Buy."
        ]

    def play(self, payload):
        self.deck.draw()
        self.game.add_actions(2)
        if self.game.empty_stacks >= 1:
            self.deck.draw()
        if self.game.empty_stacks >= 2:
            self.game.add_money(1)
            self.game.add_buys(1)
        return {}

class Contraband(Treasure):
    def cost(self):
        return 5

    def value(self):
        return 3

    def text(self):
        return [
            "+1 Buy",
            "When you play this, the player to your left names a card. " + \
            "You can't buy that card this turn.",
        ]

    def name_contraband(self, pid, payload):
        card = payload.get('card')
        if not isinstance(card, dict):
            return {'error': 'Invalid card chosen.'}
        if not self.game.active_player.add_contraband(card):
            return {'error': 'No such card {0}'.format(card.get('name'))}
        return {'clear': True}

    def preplay(self, payload):
        self.game.add_callback(
            'name_contraband',
            self.name_contraband,
            self.game.opponents()[0:1]
        )
        return {}

class CountingHouse(Action):
    def cost(self):
        return 5

    def text(self):
        return [
            "Look through your discard pile, reveal any number of Copper " + \
            "cards from it, and put them into your hand."
        ]

    def play(self, payload):
        if 'count' not in payload:
            return {'error': 'Parameter count required.'}
        count = payload['count']
        if not isinstance(count, int):
            return {'error': 'Parameter count must be an int.'}
        coppers = [x for x in self.deck.discard if x.name() == 'Copper']
        if len(coppers) < count:
            return {'error': 'You do not have that many coppers in your discard.'}
        for i in xrange(count):
            self.deck.hand.append(coppers[i])
            self.deck.discard.remove(coppers[i])
        return {}

class Mint(Action):
    def cost(self):
        return 5

    def text(self):
        return [
            "You may reveal a Treasure card from your hand. Gain a copy of " + \
            "it. When you buy this, trash all Treasures you have in play."
        ]

    def on_buy(self):
        for card in self.deck.tmp_zone:
            if card.is_treasure():
                self.game.trash.append(card)
                self.deck.tmp_zone.remove(card)
        return {}

    def play(self, payload):
        card = payload.get('card')
        if not isinstance(card, dict):
            return {'error': 'Invalid card chosen.'}
        if self.deck.find_card_in_hand(card) is None:
            return {'error': 'Card {0} not in hand.'.format(card.get('name'))}
        self.game.gain(self.deck, card.get('name'))
        return {}

class Mountebank(Attack):
    def cost(self):
        return 5

    def text(self):
        return [
            "+$2",
            "Each other player may discard a Curse. If he doesn't, he " + \
            "gains a Curse and a Copper.",
        ]

    def preplay(self, payload):
        self.game.add_buys(2)
        return {}

    def discard_curse(self, pid, payload):
        deck = self.game.players[pid].deck
        if payload.get('discard'):
            c = deck.discard_hand({'name': 'Curse'})
            if c is None:
                return {'error': 'No Curse to discard.'}
        else:
            self.game.gain(deck, 'Curse')
            self.game.gain(deck, 'Copper')
        return {'clear': True}

    def attack(self, players):
        self.game.add_money(2)
        self.game.add_callback("discard_curse", self.discard_curse, players)

class Rabble(Attack):
    def cost(self):
        return 5

    def text(self):
        return [
            "+3 Cards",
            "Each other player reveals the top 3 cards of his deck, " + \
            "discards the revealed Actions and Treasures, and puts the " + \
            "rest back on top in any order he chooses.",
        ]

    def preplay(self, payload):
        self.deck.draw(3)
        return {}

    def choose_order(self, pid, payload):
        if not isinstance(payload.get('cards'), list):
            return {'error': 'Cards must be list.'}

        cards = []
        revealed = self.revealed[pid]
        if len(revealed) != len(payload['cards']):
            return {'error': 'Must reorder all cards.'}
        for card in payload['cards']:
            if not isinstance(card, dict):
                revealed += cards
                return {'error': 'Invalid card.'}
            matching = [x for x in revealed if x.name() == card.get('name')]
            if not matching:
                revealed += cards
                return {'error': 'Card not in revealed cards.'}
            cards.append(matching[0])
            revealed.remove(matching[0])

        self.game.players[pid].deck.library += cards
        return {'clear': True}

    def attack(self, players):
        self.revealed = {}
        for player in players:
            deck = player.deck
            cards = []
            for i in xrange(3):
                c = deck.peek()
                if c is None:
                    break
                cards.append(deck.library.pop())

            discarded = []
            new_cards = []
            for card in cards:
                if card.is_treasure() or card.is_action():
                    discarded.append(card)
                else:
                    new_cards.append(card)
            deck.discard += discarded
            self.revealed[player.id] = new_cards
            self.game.log.append({
                'pid': player.id,
                'action': 'reveal_top_3',
                'revealed': [x.dict() for x in new_cards],
                'discarded': [x.dict() for x in discarded],
            })
        self.game.add_callback('choose_order', self.choose_order, players)

class RoyalSeal(Treasure):
    def cost(self):
        return 5

    def value(self):
        return 2

    def text(self):
        return [
            "While this is in play, when you gain a card, you may put that " + \
            "card on top of your deck."
        ]

    def put_top(self, pid, payload):
        if payload.get('put_top'):
            deck = self.game.players[pid].deck
            if self.bought in deck.discard:
                deck.library.append(self.bought)
                deck.discard.remove(self.bought)
        return {'clear': True}

    def effect(self, card):
        self.bought = card
        self.game.add_callback('put_top', self.put_top, [self.game.active_player])

    def preplay(self, payload):
        self.game.on_gain(lambda x: True, self.effect)
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
        if not isinstance(payload.get('cards'), list):
            return {'error': 'Cards must be list.'}
        if not payload['cards']:
            return {'clear': True}
        if len(payload['cards']) != 2:
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

    def discard_cards(self, pid, payload):
        if not isinstance(payload.get('cards'), list):
            return {'error': 'Cards must be list.'}

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
        self.game.add_money(len(cards))
        return {'clear': True}

    def play(self, payload):
        self.deck.draw(2)
        self.game.add_callback('discard_cards', self.discard_cards, [self.game.active_player])
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
        while True:
            c = self.deck.peek()
            if c is None:
                break
            self.deck.library.pop()
            if c.is_treasure():
                self.deck.tmp_zone.append(c)
                self.game.log.append({
                    'pid': self.game.active_player.id,
                    'action': 'venture',
                    'played': c.dict(),
                })
                c.play({})
                break
            revealed.append(c)
        self.deck.discard += revealed
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

    def effect(self, card):
        self.game.active_player.victory_tokens += 1

    def preplay(self, payload):
        self.game.add_buys(1)
        self.game.add_money(2)
        self.game.on_buy(lambda x: True, self.effect)
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
        c = self.deck.find_card_in_tmp_zone({'name': 'Copper'})
        if c is not None:
            return {'error': 'Cannot buy Grand Market when Copper in play.'}
        else:
            return {}

    def play(self, payload):
        self.deck.draw()
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

    def effect(self, card):
        self.game.gain(self.deck, 'Gold')

    def preplay(self, payload):
        self.game.on_buy(lambda x: x.is_victory(), self.effect)
        return {}

class Bank(Treasure):
    def cost(self):
        return 7

    def value(self):
        val = 0
        if not self.deck:
            return val
        return len([x for x in self.deck.tmp_zone if x.is_treasure()])

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
                self.deck.hand += cards
                return {'error': 'Invalid card'}
            c = self.deck.find_card_in_hand(card)
            if c is None:
                self.deck.hand += cards
                return {'error': 'Card {0} not in hand'.format(card.get('name'))}
            total_cost += c.cost()
            cards.append(c)
            self.deck.hand.remove(c)

        if gained.cost() != total_cost:
            self.deck.hand += cards
            return {'error': 'Gained card must have equal cost to sum of trashed cards.'}
        c = self.game.gain(self.deck, name)
        if c is None:
            self.deck.hand += cards
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
        if not self.game.active_deck:
            return cost
        for card in self.game.active_deck.tmp_zone:
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
        self.deck.draw()
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
