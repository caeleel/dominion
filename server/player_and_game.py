from cards_and_decks import *
from base_set import *
from prosperity import *
import random
import uuid
import time

class Player(object):
    def __init__(self, game, id, name=None):
        self.id = id
        self.name = name
        self.uuid = uuid.uuid4().hex
        self.deck = Deck(self, game)
        self.game = game
        self.durations = []
        self.discounts = []
        self.contraband = set()
        self.victory_tokens = 0
        self.start_turn()

    def start_turn(self):
        self.actions = 1
        self.buys = 1
        self.money = 0
        for card in self.durations:
            card.duration()
        self.duration = []

    def finish_turn(self):
        self.discounts = []
        self.contraband = set()
        self.deck.redraw()

    def add_contraband(self, card):
        if not self.game.card_from_name(card.get('name')):
            return False
        self.contraband.add(card.get('name'))
        return True

    def buy(self, card):
        if self.buys < 1:
            return {'error': 'No remaining buys.'}
        name = card.get('name')
        if name in self.contraband:
            return {'error': 'That item is contraband.'}
        c = self.game.card_from_name(name)
        if not c:
            return {'error': 'No such card {0} to buy.'.format(name)}
        cost = c.effective_cost(self)
        if cost > self.money:
            return {'error': 'Not enough money to buy {0}.'.format(name)}
        if not self.game.gain(self.deck, card.get('name'), True):
            return {'error': 'Could not buy card {0}.'.format(name)}

        for fits_criteria, effect in self.game.buy_callbacks:
            if fits_criteria(c):
                effect(c)

        self.game.log.append({
            'pid': self.id,
            'action': 'buy',
            'card': name,
        })
        self.buys -= 1
        self.money -= cost
        return {}

class Game(object):
    def __init__(self, sets=['base_set', 'prosperity']):
        action_amount = 10

        self.cards = {
            'Copper': (Copper(self), 60),
            'Silver': (Silver(self), 40),
            'Gold': (Gold(self), 30),
            'Estate': (Estate(self), 24),
            'Duchy': (Duchy(self), 12),
            'Province': (Province(self), 8),
            'Curse': (Curse(self), 10),
        }

        base_set = {
            'Adventurer': (Adventurer(self), action_amount),
            'Bureaucrat': (Bureaucrat(self), action_amount),
            'Cellar': (Cellar(self), action_amount),
            'Chancellor': (Chancellor(self), action_amount),
            'Chapel': (Chapel(self), action_amount),
            'CouncilRoom': (CouncilRoom(self), action_amount),
            'Feast': (Feast(self), action_amount),
            'Gardens': (Gardens(self), 12),
            'Festival': (Festival(self), action_amount),
            'Laboratory': (Laboratory(self), action_amount),
            'Market': (Market(self), action_amount),
            'Militia': (Militia(self), action_amount),
            'Mine': (Mine(self), action_amount),
            'Moat': (Moat(self), action_amount),
            'Moneylender': (Moneylender(self), action_amount),
            'Remodel': (Remodel(self), action_amount),
            'Smithy': (Smithy(self), action_amount),
            'Spy': (Spy(self), action_amount),
            'Thief': (Thief(self), action_amount),
            'ThroneRoom': (ThroneRoom(self), action_amount),
            'Village': (Village(self), action_amount),
            'Witch': (Witch(self), action_amount),
            'Woodcutter': (Woodcutter(self), action_amount),
            'Workshop': (Workshop(self), action_amount),
        }

        prosperity = {
            'Loan': (Loan(self), action_amount),
            'TradeRoute': (TradeRoute(self), action_amount),
            'Watchtower': (Watchtower(self), action_amount),
            'Bishop': (Bishop(self), action_amount),
            'Monument': (Monument(self), action_amount),
            'Quarry': (Quarry(self), action_amount),
            'Talisman': (Talisman(self), action_amount),
            'WorkersVillage': (WorkersVillage(self), action_amount),
            'City': (City(self), action_amount),
            'Contraband': (Contraband(self), action_amount),
            'CountingHouse': (CountingHouse(self), action_amount),
            'Mint': (Mint(self), action_amount),
            'Mountebank': (Mountebank(self), action_amount),
            'Rabble': (Rabble(self), action_amount),
            'RoyalSeal': (RoyalSeal(self), action_amount),
            'Vault': (Vault(self), action_amount),
            'Venture': (Venture(self), action_amount),
            'Goons': (Goons(self), action_amount),
            'GrandMarket': (GrandMarket(self), action_amount),
            'Hoard': (Hoard(self), action_amount),
            'Bank': (Bank(self), action_amount),
            'Expand': (Expand(self), action_amount),
            'Forge': (Forge(self), action_amount),
            'KingsCourt': (KingsCourt(self), action_amount),
            'Peddler': (Peddler(self), action_amount),
        }

        if 'base_set' in sets:
            self.cards.update(base_set)
        if 'prosperity' in sets:
            self.cards.update(prosperity)

        self.num_players = 0
        self.players = []
        self.victories_gained = set()
        self.buy_callbacks = []
        self.gain_callbacks = []
        self.callbacks = {}
        self.callbacks_queue = []
        self.active_player = None
        self.active_deck = None
        self.active_player_index = -1
        self.is_last_round = False
        self.empty_stacks = 0
        self.stacks = []
        self.trash = []
        self.scores = {}
        self.log = []
        self.updated_at = time.time()
        self.state = 'pregame'

        for card in self.cards:
            if card not in ['Copper', 'Silver', 'Gold',
                            'Estate', 'Duchy', 'Province', 'Curse']:
                self.stacks.append(card)
        for i in xrange(len(self.stacks)):
            j = random.randint(i, len(self.stacks) - 1)
            tmp = self.stacks[i]
            self.stacks[i] = self.stacks[j]
            self.stacks[j] = tmp
        for card in self.stacks[10:]:
            del self.cards[card]
        if self.stacks[0] in prosperity:
            self.cards['Colony'] = (Colony(self), 8)
            self.cards['Platinum'] = (Platinum(self), 12)

    def card_from_name(self, name):
        if name in self.cards:
            return self.cards[name][0]
        else:
            return None

    def opponents(self, pid=None):
        if not pid:
            pid = self.active_player_index

        result = []
        for x in xrange(pid + 1, pid + self.num_players):
            result.append(self.players[x % self.num_players])
        return result

    def add_player(self, name):
        player = Player(self, self.num_players, name)
        self.players.append(player)
        self.num_players += 1
        if self.num_players == 3:
            self.cards['Province'] = (Province(self), 12)
            if 'Colony' in self.cards:
                self.cards['Colony'] = (Colony(self), 12)
        if self.num_players > 2:
            curses = self.cards['Curse']
            self.cards['Curse'] = (curses[0], curses[1] + 10)
        return (player.id, player.uuid)

    def start_game(self):
        if self.num_players < 1:
            return False
        self.next_turn()
        self.victories_gained = set()
        return True

    def finish_game(self):
        self.state = 'finished'
        for player in self.players:
            self.active_player = player
            self.active_deck = player.deck
            self.scores[player.id] = player.deck.score() + player.victory_tokens

    def next_turn(self):
        self.log.append({
            'pid': self.active_player_index,
            'action': 'end_turn',
        })
        self.active_player_index = (self.active_player_index + 1) % self.num_players
        if self.active_player:
            self.active_player.finish_turn()
        self.active_player = self.players[self.active_player_index]
        self.active_deck = self.active_player.deck
        self.buy_callbacks = []
        self.gain_callbacks = []
        if self.is_last_round:
            self.finish_game()
            return {}
        self.active_player.start_turn()
        self.state = 'action'
        return {}

    def buy_phase(self):
        if self.state != 'action':
            return {'error': 'Not in the action phase'}
        self.state = 'buy'
        self.log.append({
            'pid': self.active_player_index,
            'action': 'end_actions',
        })
        return {}

    def add_money(self, money):
        self.active_player.money += money

    def add_callback(self, name, callback, players):
        for p in players:
            self.callbacks[p.id] = (name, callback)
        if players:
            self.state = 'callback'

    def queue_callback(self, name, callback, players):
        if not self.callbacks:
            self.add_callback(name, callback, players)
            return

        callbacks = {}
        for p in players:
            callbacks[p.id] = (name, callback)
        self.callbacks_queue.append(callbacks)

    def add_buys(self, buys):
        self.active_player.buys += buys

    def add_actions(self, actions):
        self.active_player.actions += actions

    def last_round(self):
        self.is_last_round = True

    def ungain(self, deck, card):
        if not deck.find_card_in_hand(c):
            return None

        card_name = c.get('name')
        card = self.cards[card_name]
        self.cards[card_name] = (card[0], card[1] + 1)
        if card[1] == 0:
            self.empty_stacks -= 1

        for x in deck.hand:
            if x.name() == card_name:
                deck.hand.remove(x)
                break
        return card[0]

    def on_buy(self, fits_criteria, effect):
        self.buy_callbacks.append((fits_criteria, effect))

    def on_gain(self, fits_criteria, effect):
        self.gain_callbacks.append((fits_criteria, effect))

    def gain(self, deck, card_name, bought=False):
        if card_name not in self.cards:
            return None
        card = self.cards[card_name]
        if card[1] <= 0:
            return None

        new_card = card[0].__class__(self)
        new_card.set_deck(deck)
        if bought:
            result = new_card.on_buy()
            if 'error' in result:
                return None

        self.log.append({
            'pid': deck.player.id,
            'action': 'gain',
            'card': card_name,
        })

        for fits_criteria, effect in self.gain_callbacks:
            if fits_criteria(new_card):
                effect(new_card)
        for c in deck.hand:
            if 'gain' in c.reacts_to():
                c.register_reaction(deck.player.id, new_card)
        if new_card.is_victory():
            self.victories_gained.add(card[0])

        self.cards[card_name] = (card[0], card[1] - 1)
        if card[1] == 1:
            self.empty_stacks += 1
            if self.empty_stacks == 3 or card_name == 'Province':
                self.last_round()
            if card_name == 'Colony':
                self.last_round()

        deck.discard.append(new_card)
        return new_card

    def buy(self, card):
        if not isinstance(card, dict):
            return {'error': 'Invalid card specified'}
        if self.state != 'buy':
            return {'error': 'Not in buy phase'}
        return self.active_player.buy(card)

    def play(self, card, payload):
        if not isinstance(card, dict):
            return {'error': 'Invalid card specified'}
        if not isinstance(payload, dict):
            return {'error': 'Invalid payload'}
        return self.active_deck.play(card, payload)

    def callback(self, pid, payload):
        if not isinstance(payload, dict):
            return {'error': 'Invalid payload'}
        if pid not in self.callbacks:
            return {'error': 'No callbacks registered for player {0}'.format(pid)}
        name, callback = self.callbacks[pid]
        result = callback(pid, payload)
        if 'error' not in result:
            self.log.append({
                'pid': pid,
                'action': 'callback',
                'callback_name': name,
                'payload': payload,
                'result': result,
            })
        if result.get('clear'):
            del self.callbacks[pid]
            if not self.callbacks:
                if not self.callbacks_queue:
                    self.state = 'action'
                else:
                    self.callbacks = self.callbacks_queue.pop(0)
        return result

    def check_reaction(self, pid, payload):
        if 'cards' not in payload:
            return {'error': 'Required param cards missing.'}
        cards = payload['cards']
        if not isinstance(cards, list):
            return {'error': 'Param cards must be list'}

        for card in cards:
            if not isinstance(card, dict):
                return {'error': 'Card must be dict'}
            deck = self.players[pid].deck
            name = card.get('name')
            c = deck.find_card_in_hand(card)
            if c is None:
                return {'error': 'Card {0} not in hand'.format(name)}
            if not c.is_reaction():
                return {'error': 'Card {0} is not a reaction'.format(name)}
            if trigger not in c.reacts_to():
                return {'error': 'Card {0} does not react to {1}'.format(name, trigger)}

        block = False
        for card in cards:
            deck = self.players[pid].deck
            name = card.get('name')
            c = deck.find_card_in_hand(card)
            block = block = c.react(pid)

        self.resolver.resolve(pid, block)
        return {'clear': True}

    def callback_reaction(self, resolver, players, trigger):
        self.resolver = resolver
        self.trigger = trigger
        self.add_callback('check_reaction', self.check_reaction, players)

    def dict(self, player_id=None):
        if player_id is None:
            player_id = self.active_player_index
        if player_id >= self.num_players:
            return {}

        supply = [{'card': x[0].dict(), 'left': x[1]} for x in self.cards.values()]
        supply = sorted(supply, key=lambda x: x['card'].get('cost'))

        if player_id < 0:
            return {'supply': supply}

        callbacks = {}
        player = self.players[player_id]
        deck = player.deck.dict()

        for pid, callback in self.callbacks.iteritems():
            callbacks[pid] = callback[0]

        trash = [x.dict() for x in self.trash]
        opponents = [
            {
                'id': x.id,
                'name': x.name,
                'hand_size': len(x.deck.hand),
                'vp_tokens': x.victory_tokens,
                'discard': [y.dict() for y in x.deck.discard],
                'in_play': [y.dict() for y in x.deck.tmp_zone],
                'library_size': len(x.deck.library),
            } for x in self.opponents(player_id)
        ]

        return {
            'deck': deck,
            'vp_tokens': player.victory_tokens,
            'supply': supply,
            'trash': trash,
            'trade_route_tokens': len(self.victories_gained),
            'opponents': opponents,
            'state': self.state,
            'scores': self.scores,
            'actions': player.actions,
            'buys': player.buys,
            'money': player.money,
            'turn': self.active_player_index,
            'callbacks': callbacks,
            'log': self.log,
        }
