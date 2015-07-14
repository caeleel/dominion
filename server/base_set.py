from cards_and_decks import *
from collections import defaultdict

class Cellar(Action):
    def cost(self):
        return 2

    def text(self):
        return [
            "+1 Action",
            "Discard any number of cards",
            "+1 Card per card discarded.",
        ]

    def play(self, payload):
        cards = []

        if 'cards' not in payload:
            return {'error': 'No cards discarded'}
        if not isinstance(payload['cards'], list):
            return {'error': 'Cards must be list.'}
        for card in payload['cards']:
            if not isinstance(card, dict):
                self.deck.hand += cards
                return {'error': 'Invalid card'}
            c = self.deck.find_card_in_hand(card)
            if c is None:
                self.deck.hand += cards
                return {'error': '{0} not in hand'.format(card.get('name'))}
            cards.append(c)
            self.deck.hand.remove(c)

        self.deck.discard += cards
        self.deck.draw(len(payload['cards']))

        self.game.add_actions(1)
        return {}

class Chapel(Action):
    def cost(self):
        return 2

    def text(self):
        return ["Trash up to 4 cards from your hand."]

    def play(self, payload):
        cards = []

        if 'cards' not in payload:
            return {'error': 'No cards to trash.'}
        if not isinstance(payload['cards'], list):
            return {'error': 'Cards must be list.'}
        if len(payload['cards']) > 4:
            return {'error': 'Cannot trash more than 4 cards.'}

        for card in payload['cards']:
            if not isinstance(card, dict):
                self.deck.hand += cards
                return {'error': 'Invalid card'}
            c = self.deck.find_card_in_hand(card)
            if c is None:
                self.deck.hand += cards
                return {'error': '{0} not in hand'.format(card.get('name'))}
            cards.append(c)
            self.deck.hand.remove(c)

        self.game.trash += cards
        return {}

class Moat(Reaction):
    def cost(self):
        return 2

    def reacts_to(self):
        return ['attack']

    def text(self):
        return [
            "+2 Cards",
            "When another player plays an Attack card, you may " + \
            "reveal this from your hand. If you do, you are " + \
            "unaffected by that Attack."
        ]

    def react(self, pid, payload):
        return True

    def play(self, payload):
        self.deck.draw(2)
        return {}

class Chancellor(Action):
    def cost(self):
        return 3

    def text(self):
        return ["You may immediately put your deck into your discard pile"]

    def play(self, payload):
        self.game.add_money(2)
        if payload.get('discard_deck'):
            while self.deck.discard_top():
                pass
        return {}

class Village(Action):
    def cost(self):
        return 3

    def text(self):
        return [
            "+1 Card",
            "+2 Actions",
        ]

    def play(self, payload):
        self.deck.draw()
        self.game.add_actions(2)
        return {}

class Woodcutter(Action):
    def cost(self):
        return 3

    def text(self):
        return [
            "+1 Buy",
            "+$2",
        ]

    def play(self, payload):
        self.game.add_buys(1)
        self.game.add_money(2)
        return {}

class Workshop(Action):
    def cost(self):
        return 3

    def text(self):
        return ["Gain a card costing up to $4"]

    def play(self, payload):
        if not payload.get('gain'):
            return {'error': 'No card gained'}
        card = payload['gain']
        if not isinstance(card, dict):
            return {'error': 'Invalid card'}
        c = self.game.card_from_name(card.get('name'))
        if not c:
            return {'error': 'No such card {0}'.format(card.get('name'))}
        if c.cost() > 4:
            return {'error': 'Cannot gain card worth more than $4'}

        if self.game.gain(self.deck, card['name']):
            return {}
        else:
            return {'error': 'No {0}s left'.format(card['name'])}

class Bureaucrat(Attack):
    def cost(self):
        return 4

    def text(self):
        return [
            "Gain a silver card; put it on top of your deck. " + \
            "Each other player reveals a Victory card from his " + \
            "hand and puts it on his deck (or reveals a hand " + \
            "with no Victory cards)."
        ]

    def choose_victory(self, pid, payload):
        card = payload.get('card')
        if not isinstance(card, dict):
            return {'error': 'Invalid card'}
        name = card.get('name')
        deck = self.game.players[pid].deck
        c = deck.hand_to_library(card)
        if c is None:
            return {'error': 'Card {0} not in hand'.format(name)}
        return {'clear': True}

    def preplay(self, payload):
        self.game.gain(self.deck, 'Silver')
        self.deck.discard_to_library({'name': 'Silver'})
        return {}

    def attack(self, players):
        callback_targets = []

        for player in players:
            deck = player.deck
            victory = set()
            for c in deck.hand:
                if c.is_victory():
                    victory.add(c)
            if len(victory) == 0:
                self.game.log.append({
                    'pid': player.id,
                    'action': 'show_hand',
                    'hand': deck.dict()['hand']
                })
            else:
                callback_targets.append(player)

        if callback_targets:
            self.num_targets = len(callback_targets)
            self.game.add_callback('choose_victory', self.choose_victory, callback_targets)

class Feast(Action):
    def cost(self):
        return 4

    def text(self):
        return ["Trash this card. Gain a card costing up to $5"]

    def play(self, payload):
        gain = payload.get('gain')
        if not gain:
            return {'error': 'No card to gain specified'}
        if not isinstance(gain, dict):
            return {'error': 'Invalid gain card'}
        if not self.game.gain(self.deck, gain['name']):
            return {'error': 'Could not gain card'}
        self.deck.trash_tmp_zone({'name': 'Feast'})
        return {}

class Gardens(Victory):
    def cost(self):
        return 4

    def text(self):
        return ["Worth 1 Victory for every 10 cards in your deck (rounded down)."]

    def points(self):
        if not self.deck:
            return 0
        return self.deck.size()/10

class Militia(Attack):
    def cost(self):
        return 4

    def text(self):
        return [
            "+$2",
            "Each other player discards down to 3 cards in his hand.",
        ]

    def preplay(self, payload):
        self.game.add_money(2)
        return {}

    def discard_down(self, pid, payload):
        cards = payload.get('cards')
        if not isinstance(cards, list):
            return {'error': 'Invalid cards'}

        deck = self.game.players[pid].deck
        if len(deck.hand) - len(cards) != 3:
            return {'error': 'Must discard down to 3 cards'}

        discarded = []
        for card in cards:
            if not isinstance(card, dict):
                deck.hand += discarded
                return {'error': 'Invalid card'}
            name = card.get('name')
            c = deck.find_card_in_hand(card)
            if c is None:
                deck.hand += discarded
                return {'error': 'Card {0} not in hand'.format(name)}
            deck.hand.remove(c)
            discarded.append(c)

        deck.discard += discarded
        return {'clear': True}

    def attack(self, players):
        self.game.add_callback("discard_to_3", self.discard_down, players)
        return {}

class Moneylender(Action):
    def cost(self):
        return 4

    def text(self):
        return ["Trash a Copper from your hand. If you do, +$3."]

    def play(self, payload):
        if 'Copper' not in self.deck.hand_names():
            return {'warn': 'no Copper to trash'}
        self.deck.trash_hand({'name': 'Copper'})
        self.game.add_money(3)
        return {}

class Remodel(Action):
    def __init__(self, game, n=2):
        super(Remodel, self).__init__(game)
        self.jump = n

    def cost(self):
        return 4

    def text(self):
        return [
            "Trash a card from your hand. Gain a card costing up " + \
            "to ${0} more than the trashed card.".format(self.jump)
        ]

    def play(self, payload):
        trash = payload.get('trash')
        gain = payload.get('gain')

        if len(self.deck.hand) == 0 and not trash and not gain:
            return {}

        if not isinstance(trash, dict) or not isinstance(gain, dict):
            return {'error': 'Invalid trash or gain card'}

        c1 = self.deck.find_card_in_hand(trash)
        if not c1:
            return {'error': 'Could not trash {0}'.format(trash.get('name'))}

        c2 = self.game.card_from_name(gain.get('name'))
        if not c2:
            return {'error': 'No such card {0}'.format(gain.get('name'))}
        if c1.cost() + self.jump < c2.cost():
            return {'error': 'Gained card must cost ${0} or less than trashed card'.format(self.jump)}
        if not self.game.gain(self.deck, gain['name']):
            return {'error': 'Could not gain {0}'.format(gain.get('name'))}
        self.deck.trash_hand(trash)
        return {}

class Smithy(Action):
    def cost(self):
        return 4

    def text(self):
        return ["+3 Cards."]

    def play(self, payload):
        self.deck.draw(3)
        return {}

class Spy(Attack):
    def cost(self):
        return 4

    def text(self):
        return [
            "+1 Card",
            "+1 Action",
            "Each player (including you) reveals the top card of his deck " + \
            "and either discards it or puts it back, your choice."
        ]

    def preplay(self, payload):
        self.deck.draw()
        self.game.add_actions(1)
        return {}

    def choose_discard(self, pid, payload):
        if 'discard' not in payload or not isinstance(payload['discard'], list):
            return {'error': 'Parameter discard must be a list of pids'}
        for pid in payload['discard']:
            if pid not in self.revealed:
                return {'error': 'Invalid pid selected'}
        for pid in payload['discard']:
            self.game.players[pid].deck.discard_top()
        return {'clear': True}

    def attack(self, players):
        players.append(self.game.active_player)
        self.revealed = {}
        for player in players:
            self.revealed[player.id] = player.deck.peek().dict()
        self.game.log.append({
            'pid': self.game.active_player.id,
            'action': 'spy_cards',
            'revealed': self.revealed,
        })
        self.game.add_callback('choose_discard', self.choose_discard, [self.game.active_player])

class Thief(Attack):
    def cost(self):
        return 4

    def text(self):
        return [
            "Each other player reveals the top 2 cards of his deck. " + \
            "If they revealed any Treasure cards, they trash one of them " + \
            "that you choose. You may gain any or all of these trashed " + \
            "cards. They discard the other revealed cards."
        ]

    def steal_cards(self, pid, payload):
        if 'to_trash' not in payload:
            return {'error': 'Param to_trash is required.'}
        to_trash = payload['to_trash']
        if not isinstance(to_trash, dict):
            return {'error': 'Param to_trash must be dict.'}

        names = {}
        for k, v in self.revealed.iteritems():
            names[k] = {}
            for card in v:
                names[k][card.name()] = card
        for opp, trash in to_trash.iteritems():
            try:
                opp = int(opp)
            except ValueError:
                return {'error': 'Keys must be ints'}
            if opp not in self.revealed:
                return {'error': 'Invalid pid in to_trash.'}
            if not isinstance(trash, dict):
                return {'error': 'Trashed card must be dict.'}
            name = trash.get('name')
            if name not in names[opp]:
                return {'error': 'Card {0} was not trashed'.format(name)}
            if not names[opp][name].is_treasure():
                return {'error': 'Cannot trash non-treasure {0}.'.format(name)}

        for opp, trash in to_trash.iteritems():
            opp = int(opp)
            card = names[opp][trash.get('name')]
            self.revealed[opp].remove(card)
            if trash.get('keep'):
                self.deck.discard.append(card)
            else:
                self.game.trash.append(card)
        for opp, cards in self.revealed.iteritems():
            self.game.players[opp].deck.discard += cards
        return {'clear': True}

    def attack(self, players):
        self.revealed = defaultdict(list)
        for player in players:
            deck = player.deck
            pid = player.id
            for i in range(2):
                c = deck.peek()
                if c is not None:
                    self.revealed[pid].append(c)
                    deck.library.pop()

        revealed = {}
        for k, v in self.revealed.iteritems():
            revealed[k] = [x.dict() for x in v]

        self.game.log.append({
            'pid': self.game.active_player.id,
            'action': 'show_thieved',
            'revealed': revealed,
        })
        self.game.add_callback('steal_cards', self.steal_cards, [self.game.active_player])

class ThroneRoom(Action):
    def __init__(self, game, n=1):
        super(ThroneRoom, self).__init__(game)
        self.repeat = n

    def cost(self):
        return 4

    def text(self):
        if self.repeat == 1:
            adverb = "twice"
        elif self.repeat == 2:
            adverb = "three times"
        return ["Choose an Action card in your hand. Play it {0}.".format(adverb)]

    def play_next(self, pid, payload):
        result = self.c1.play(payload)
        if 'error' not in result:
            self.repeats -= 1
            if self.repeats <= 0:
                result['clear'] = True
        return result

    def play(self, payload):
        card = payload.get('card')
        if not card:
            return {}

        payload1 = payload.get('payload', {})

        if not isinstance(card, dict):
            return {'error': 'Target is not valid card'}
        if not isinstance(payload1, dict):
            return {'error': 'Secondary payloads not valid'}

        name = card.get('name')
        c1 = self.deck.find_card_in_hand(card)

        if not c1:
            return {'error': '{0} not in hand'.format(name)}
        if not c1.is_action():
            return {'error': '{0} is not an action'.format(name)}

        self.deck.tmp_zone.append(c1)
        self.deck.hand.remove(c1)
        self.c1 = c1
        self.repeats = self.repeat

        result = self.c1.play(payload1)
        if 'error' in result:
            self.deck.tmp_zone.remove(c1)
            self.deck.hand.append(c1)
            return result

        self.game.queue_callback(
            'play_next',
            self.play_next,
            [self.game.active_player]
        )
        return result

class CouncilRoom(Action):
    def cost(self):
        return 5

    def text(self):
        return [
            "+4 Cards",
            "+1 Buy",
            "Each other player draws a card.",
        ]

    def play(self, payload):
        self.deck.draw(4)
        self.game.add_buys(1)
        for opp in self.game.opponents():
            opp.deck.draw()
        return {}

class Festival(Action):
    def cost(self):
        return 5

    def text(self):
        return [
            "+2 Actions",
            "+1 Buy",
            "+$2",
        ]

    def play(self, payload):
        self.game.add_actions(2)
        self.game.add_buys(1)
        self.game.add_money(2)
        return {}

class Laboratory(Action):
    def cost(self):
        return 5

    def text(self):
        return [
            "+2 Cards",
            "+1 Action",
        ]

    def play(self, payload):
        self.deck.draw(2)
        self.game.add_actions(1)
        return {}

class Library(Action):
    def cost(self):
        return 5

    def text(self):
        return [
            "Draw until you have 7 cards in hand. You may set aside any " + \
            "Action cards drawn in this way, as you draw them; discard " + \
            "the set aside cards after you finish drawing."
        ]

    def draw_card(self, pid, payload):
        if 'keep' not in payload:
            return {'error': 'Need to specify keep parameter.'}

        deck = self.game.player[pid].deck
        c = deck.peek()
        if not payload['keep'] and not c.is_action():
            return {'error': 'Cannot discard a non-action card.'}
        if payload['keep']:
            deck.draw()
            if len(deck.hand) >= 7:
                deck.discard += self.set_aside
                return {'clear': True}
        else:
            self.set_aside.append(deck.library.pop())

        c = deck.peek()
        if c is not None:
            return {'card': c.dict()}
        else:
            return {'clear': True}

    def play(self, payload):
        c = self.deck.peek()
        self.set_aside = []

        if c is not None and len(self.deck.hand) < 7:
            self.game.add_callback(
                'draw_card',
                self.draw_card,
                [self.game.active_player]
            )
            return {'card': c.dict()}
        else:
            return {}

class Market(Action):
    def cost(self):
        return 5

    def text(self):
        return [
            "+1 Card",
            "+1 Action",
            "+1 Buy",
            "+$1",
        ]

    def play(self, payload):
        self.deck.draw()
        self.game.add_actions(1)
        self.game.add_buys(1)
        self.game.add_money(1)
        return {}

class Mine(Action):
    def cost(self):
        return 5

    def text(self):
        return [
            "Trash a Treasure card from your hand. Gain a Treasure card " + \
            "costing up to $3 more; put it into your hand."
        ]

    def play(self, payload):
        trash = payload.get('trash')
        gain = payload.get('gain')
        if not isinstance(trash, dict) or not isinstance(gain, dict):
            return {'error': 'Invalid trash or gain card'}

        c1 = self.deck.find_card_in_hand(trash)
        if not c1:
            return {'error': 'No such card {0} in hand'.format(trash.get('name'))}
        if not c1.is_treasure():
            return {'error': 'Card is not treasure'}

        c2 = self.game.card_from_name(gain.get('name'))
        if not c2:
            return {'error': 'No such card {0}'.format(gain.get('name'))}
        if c1.cost() + 3 < c2.cost():
            return {'error': 'Gained card must not cost $4 or more than trashed card'}
        if not c2.is_treasure():
            return {'error': 'Gained card is not treasure'}
        if not self.game.gain(self.deck, gain['name']):
            return {'error': 'Could not gain {0}'.format(gain.get('name'))}

        self.deck.discard_to_hand(gain)
        self.deck.trash_hand(trash)
        return {}

class Witch(Attack):
    def cost(self):
        return 5

    def text(self):
        return [
            "+2 Cards",
            "Each other player gains a Curse card.",
        ]

    def preplay(self, payload):
        self.deck.draw(2)
        return {}

    def attack(self, players):
        for player in players:
            self.game.gain(player.deck, 'Curse')

class Adventurer(Action):
    def cost(self):
        return 6

    def text(self):
        return [
            "Reveal cards from your deck until you reveal 2 Teasure cards. " + \
            "Put those Treasure cards in your hand and discard the other " + \
            "revealed cards."
        ]

    def play(self, payload):
        revealed = []
        discard = []
        num_treasures = 0

        while True:
            c = self.deck.peek()
            if c is None:
                break
            if c.is_treasure():
                self.deck.draw()
                num_treasures += 1
            else:
                discard.append(self.deck.library.pop())
            revealed.append(c.dict())

        self.deck.discard += discard
        return {'revealed': revealed}
