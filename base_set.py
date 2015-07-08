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
        deck = self.game.active_deck

        if 'cards' not in payload:
            return {'error': 'No cards discarded'}
        for card in payload['cards']:
            if not isinstance(card, dict):
                return {'error': 'Invalid card'}
            if card.get('name') not in deck.hand_names():
                return {'error': '{0} not in hand'.format(card.get('name'))}

        for card in payload['cards']:
            deck.discard(card)
            deck.draw()

        return {}

class Chapel(Action):
    def cost(self):
        return 2

    def text(self):
        return ["Trash up to 4 cards from your hand."]

    def play(self, payload):
        deck = self.game.active_deck

        if 'cards' not in payload:
            return {'error': 'No cards to trash.'}
        if not isinstance(payload['cards'], list):
            return {'error': 'Cards must be list.'}
        if len(payload['cards']) > 4:
            return {'error': 'Cannot trash more than 4 cards.'}

        for card in payload['cards']:
            if not isinstance(card, dict):
                return {'error': 'Invalid card'}
            if card.get('name') not in deck.hand_names():
                return {'error': '{0} not in hand'.format(card.get('name'))}

        for card in payload['cards']:
            deck.trash(card)

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

    def play(self):
        self.game.active_deck.draw(2)
        return {}

class Chancellor(Action):
    def cost(self):
        return 3

    def text(self):
        return ["You may immediately put your deck into your discard pile"]

    def play(self, payload):
        self.game.add_money(2)
        if payload.get('discard_deck'):
            while self.game.active_deck.discard_top():
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
        self.game.active_deck.draw()
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
        if not payload.get('card'):
            return {'error': 'No card gained'}
        card = payload['card']
        if not isinstance(card, dict):
            return {'error': 'Invalid card'}
        c = self.game.card_from_name(card.get('name'))
        if not c:
            return {'error': 'No such card {0}'.format(card.get('name'))}
        if c.cost() > 4:
            return {'error': 'Cannot gain card worth more than $4'}

        if self.game.gain(self.game.active_deck, card['name']):
            return {}
        else:
            return {'error': 'No {0}s left'.format(card['name'])}

class Bureaucrat(Action):
    def cost(self):
        return 4

    def text(self):
        return [
            "Gain a silver card; put it on top of your deck. " + \
            "Each other player reveals a Victory card from his " + \
            "hand and puts it on his deck (or reveals a hand " + \
            "with no Victory cards)."
        ]

    def see_revealed(self, pid, payload):
        self.revealed['clear'] = True
        return self.revealed

    def choose_victory(self, pid, payload):
        card = payload.get('card')
        if not isinstance(card, dict):
            return {'error': 'Invalid card'}
        name = card.get('name')
        deck = self.game.players[pid].deck
        c = deck.hand_to_library(card)
        if c is None:
            return {'error': 'Card {0} not in hand'.format(name)}
        self.revealed[pid] = c.dict()
        if len(self.revealed) == self.num_targets:
            self.game.add_callback('see_revealed', self.see_revealed, self.game.players)
            return {}
        else:
            return {'clear': True}

    def preplay(self, payload):
        self.game.gain(self.game.active_deck, 'Silver')
        deck = self.game.active_deck
        deck.discard_to_library({'name': 'Silver'})

    def attack(self, players):
        self.revealed = {}
        callback_targets = []

        for player in players:
            deck = player.deck
            victory = set()
            for c in deck.hand:
                if c.is_victory():
                    victory.add(c)
            if len(victory) == 1:
                c = victory.pop()
                deck.hand_to_library(c)
                self.revealed[player.id] = c.dict()
            elif len(victory) == 0:
                self.revealed[player.id] = {'hand': deck.dict()['hand']}
            else:
                callback_targets.append(player)

        if callback_targets:
            self.num_targets = len(callback_targets)
            self.game.add_callback('choose_victory', self.choose_victory, callback_targets)
        else:
            self.game.add_callbacks('see_revealed', self.see_revealed, players)

class Feast(Action):
    def cost(self):
        return 4

    def text(self):
        return ["Trash this card. Gain a card costing up to $5"]

    def play(self, payload):
        deck = self.game.active_deck
        gain = payload.get('gain')
        if not gain:
            return {'error': 'No card to gain specified'}
        if not isinstance(gain, dict):
            return {'error': 'Invalid gain card'}
        if not self.game.gain(deck, gain['name']):
            return {'error': 'Could not gain card'}
        deck.trash_tmp_zone({'name': 'Feast'})
        return {}

class Gardens(Card):
    def cost(self):
        return 4

    def text(self):
        return ["Worth 1 Victory for every 10 cards in your deck (rounded down)."]

    def points(self):
        if not self.game.active_deck:
            return 0
        return self.game.active_deck.size()/10

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

    def discard_down(self, pid, payload):
        cards = payload.get('cards')
        if not isinstance(cards, list):
            return {'error': 'Invalid cards'}

        deck = self.game.players[pid].deck
        if len(deck.hand) - len(cards) != 3:
            return {'error': 'Must discard down to 3 cards'}

        for card in cards:
            if not isinstance(cards, dict):
                return {'error': 'Invalid card'}
            name = card.get('name')
            if deck.find_card_in_hand(card) is None:
                return {'error': 'Card {0} not in hand'.format(name)}

        for card in cards:
            c = deck.discard_hand(card)

        return {'clear': True}

    def attack(self, players):
        for player in players:
            self.game.add_callback("discard_to_3", self.discard_down, players)
        return {}

class Moneylender(Action):
    def cost(self):
        return 4

    def text(self):
        return ["Trash a Copper from your hand. If you do, +$3."]

    def play(self, payload):
        deck = self.game.active_deck
        if 'Copper' not in deck.hand_names():
            return {'error': 'No coppers in hand'}
        deck.trash_hand({'name': 'Copper'})
        self.game.add_money(3)
        return {}

class Remodel(Action):
    def cost(self):
        return 4

    def text(self):
        return ["Trash a card from your hand. Gain a card costing up to $2 " + \
                "more than the trashed card."]

    def play(self, payload):
        deck = self.game.active_deck
        trash = payload.get('trash')
        gain = payload.get('gain')

        if not isinstance(trash, dict) or not isinstance(gain, dict):
            return {'error': 'Invalid trash or gain card'}

        c1 = deck.find_card_in_hand(trash)
        if not c1:
            return {'error': 'Could not trash {0}'.format(trash.get('name'))}

        c2 = self.game.card_from_name(gain.get('name'))
        if not c2:
            return {'error': 'No such card {0}'.format(gain.get('name'))}
        if c1.cost() + 2 < c2.cost():
            return {'error': 'Gained card must not cost $3 or more than trashed card'}
        if not self.game.gain(deck, gain['name']):
            return {'error': 'Could not gain {0}'.format(gain.get('name'))}
        deck.trash_hand(trash)
        return {}

class Smithy(Action):
    def cost(self):
        return 4

    def text(self):
        return ["+3 Cards."]

    def play(self, payload):
        self.game.active_deck.draw(3)
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
        self.game.active_deck.draw()
        self.game.add_actions(1)

    def choose_discard(self, pid, payload):
        if pid != self.game.active_player.pid:
            return {'error': 'Invalid pid'}
        if 'discard' not in payload or not isinstance(payload['discard'], list):
            return {'error': 'Parameter discard must be a list of pids'}
        for pid in payload['discard']:
            if pid not in self.revealed:
                return {'error': 'Invalid pid selected'}
        for pid in payload['discard']:
            self.game.players[pid].deck.discard_top()
        return {'clear': True}

    def spy_cards(self, pid, payload):
        result = {}
        for k, v in self.revealed:
            result[k] = v.dict()
        if pid == self.game.active_player.pid:
            self.game.add_callback(
                'choose_discard',
                self.choose_discard,
                [self.game.active_player]
            )
        else:
            result['clear'] = True
        return result

    def attack(self, players):
        self.revealed = {}
        for player in self.game.players:
            self.revealed[player.pid] = player.deck.peek()
        self.game.add_callback('spy_cards', self.spy_cards, self.game.players)

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
        if pid != self.game.active_player.pid:
            return {'error': 'You are not the active player.'}
        if 'to_trash' not in payload:
            return {'error': 'Param to_trash is required.'}
        to_trash = payload['to_trash']
        if not isinstance(to_trash, dict):
            return {'error': 'Param to_trash must be dict.'}

        names = {}
        for k, v in self.revealed:
            names[k] = {}
            for card in v:
                names[k][x.__class__.__name__] = card
        for opp, trash in to_trash:
            if opp not in self.revealed:
                return {'error': 'Invalid pid in to_trash.'}
            if not isinstance(trash, dict):
                return {'error': 'Trashed card must be dict.'}
            name = trash.get('name')
            if name not in names[opp]:
                return {'error': 'Card {0} was not trashed'.format(name)}
            if not names[opp][name].is_treasure():
                return {'error': 'Cannot trash non-treasure {0}.'.format(name)}

        for opp, trash in to_trash:
            card = names[opp][trash.get('name')]
            self.revealed[opp].remove(card)
            if trash.get('keep'):
                self.game.active_deck.discard.append(card)
            else:
                self.game.trash.append(card)
        for opp, cards in self.revealed:
            self.game.players[opp].deck.discard += cards
        return {'clear': True}

    def show_thieved(self, pid, payload):
        revealed = {}
        for k, v in self.revealed:
            revealed[k] = [x.dict() for x in v]
        result = {'revealed': revealed}
        if pid == self.game.active_player.pid:
            self.game.add_callback('steal_cards', self.steal_cards, [self.game.active_player])
        else:
            result['clear'] = True
        return result

    def attack(self):
        self.revealed = defaultdict(list)
        for player in self.game.opponents():
            deck = player.deck
            pid = player.pid
            for i in range(2):
                c = deck.peek()
                if c is not None:
                    self.revealed[pid].append(c)
                    deck.library.pop()
        self.game.add_callback('show_thieved', self.show_thieved, [self.game.active_player])
        self.game.queue_callback('show_thieved', self.show_thieved, self.game.opponents())

class ThroneRoom(Action):
    def cost(self):
        return 4

    def text(self):
        return ["Choose an Action card in your hand. Play it twice."]

    def play_next(self, pid, payload):
        if pid != self.game.active_player.pid:
            return {'error': 'Invalid player id'}
        result = self.c1.play(payload)
        if 'error' not in result:
            result['clear'] = True
        return result

    def play(self, payload):
        deck = self.game.active_deck
        card = payload.get('card')
        payload1 = payload.get('payload1', {})

        if not isinstance(card, dict):
            return {'error': 'Target is not valid card'}
        if not isinstance(payload1, dict):
            return {'error': 'Secondary payloads not valid'}

        name = card.get('name')
        c1 = deck.find_card_in_hand(card)

        if not c1:
            return {'error': '{0} not in hand'.format(name)}
        if not c1.is_action():
            return {'error': '{0} is not an action'.format(name)}

        deck.tmp_zone.append(c1)
        deck.hand.remove(c1)

        self.c1 = c1.__class__(self.game)

        result = self.c1.play(payload1)
        if 'error' in result:
            deck.tmp_zone.remove(c1)
            deck.hand.append(c1)
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
        self.game.active_deck.draw(4)
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
        self.game.active_deck.draw(2)
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

    def draw_card(self, payload):
        if 'keep' not in payload:
            return {'error': 'Need to specify keep parameter.'}

        deck = self.game.active_deck
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
        deck = self.game.active_deck
        c = deck.peek()
        self.set_aside = []

        if c is not None and len(deck.hand) < 7:
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
        self.game.active_deck.draw(1)
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
        if not isinstance(card, dict) or not isinstance(gain, dict):
            return {'error': 'Invalid trash or gain card'}

        deck = self.game.active_deck
        c1 = deck.find_card_in_hand(trash)
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
        if not self.game.gain(deck, gain['name']):
            return {'error': 'Could not gain {0}'.format(gain.get('name'))}

        deck.discard_to_hand(gain)
        deck.trash_hand(trash)
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
        self.game.active_deck.draw(2)

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

    def show_revealed(self, pid, payload):
        return {
            'revealed': self.revealed,
            'clear': True,
        }

    def play(self):
        deck = self.game.active_deck
        self.revealed = []
        discard = []
        num_treasures = 0

        while True:
            c = deck.peek()
            if c is None:
                break
            if c.is_treasure():
                deck.draw()
                num_treasures += 1
            else:
                discard.append(deck.library.pop())
            self.revealed.append(c.dict())

        deck.discard += discard
        self.game.add_callback('show_revealed', self.show_revealed, self.game.players)
        return {}
