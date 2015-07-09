from flask import Flask, Response, request
from functools import wraps
from player_and_game import *
import uuid
import time
import json

app = Flask(__name__)
game_map = {}
POLL_INTERVAL = 2

def json_response(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        r = f(*args, **kwargs)
        return Response(json.dumps(r), content_type='application/json; charset=utf-8')
    return decorated_function

class GameManager(object):
    def __init__(self):
        global game_map

        self.uuid = uuid.uuid4().hex
        self.starter = uuid.uuid4().hex
        game_map[self.uuid] = self
        self.game = Game()
        self.changed = {}
        self.cancel = {}

    def cancel_poll(self):
        for pid in self.changed:
            self.cancel[pid] = True

    def poll(self, pid):
        while not self.changed[pid]:
            time.sleep(POLL_INTERVAL)
            if self.cancel.get(pid):
                self.cancel[pid] = False
                return {'cancel': True}

        self.changed[pid] = False
        return {'state': self.game.dict(pid), 'result': {}}

    def num_players(self):
        return self.game.num_players

    def has_changed(self):
        for p in self.changed:
            self.changed[p] = True

    def join_game(self):
        if self.game.num_players >= 4:
            return {'error': 'Already at max players'}
        if self.game.state != 'pregame':
            return {'error': 'Game already in progress'}

        pid, uuid = self.game.add_player()
        self.changed[pid] = False
        self.has_changed()

        return {'id': pid, 'uuid': uuid}

    def start_game(self):
        if self.game.start_game():
            self.has_changed()
            return {}
        else:
            return {'error': 'Could not start game'}

def validate_player(game):
    global game_map

    if game not in game_map:
        return None, None

    pid = request.args.get('pid')
    uuid = request.args.get('uuid')

    try:
        pid = int(pid)
    except ValueError:
        return None, None

    game = game_map[game]
    if game.num_players() <= pid:
        return None, None
    if game.game.players[pid].uuid != uuid:
        return None, None
    return pid, game

@app.route('/create', methods=['POST'])
@json_response
def create_game():
    new_game = GameManager()
    return {'game': new_game.uuid, 'start': new_game.starter}

@app.route('/join/<game>', methods=['POST'])
@json_response
def join_game(game):
    global game_map
    if game not in game_map:
        return {'error': 'No such game'}
    return game_map[game].join_game()

@app.route('/start/<game>/<starter>', methods=['POST'])
@json_response
def start_game(game, starter):
    global game_map
    if game not in game_map:
        return {'error': 'No such game'}
    if game_map[game].starter != starter:
        return {'error': 'Incorrect starter key'}
    return game_map[game].start_game()

@app.route('/game/<game>/callback', methods=['POST'])
@json_response
def callback(game):
    pid, game_manager = validate_player(game)
    if game_manager is None:
        return {'error': 'Invalid game / pid / uuid'}
    game = game_manager.game
    payload = {}
    if request.data:
        payload = request.get_json(force=True)

    result = game.callback(pid, payload)
    if 'error' not in result:
        game_manager.has_changed()
    return {'state': game.dict(pid), 'result': result}

@app.route('/game/<game>/cancel', methods=['POST'])
@json_response
def cancel_poll(game):
    pid, game_manager = validate_player(game)
    if game_manager is None:
        return {'error': 'Invalid game / pid / uuid'}
    game_manager.cancel_poll()
    return {}

@app.route('/game/<game>/play/<card>', methods=['POST'])
@json_response
def play_card(game, card):
    pid, game_manager = validate_player(game)
    if game_manager is None:
        return {'error': 'Invalid game / pid / uuid'}
    game = game_manager.game
    if pid != game.active_player_index:
        return {'error': 'Not your turn'}

    payload = {}
    if request.data:
        payload = request.get_json(force=True)
    result = game.play({'name': card}, payload)
    if 'error' not in result:
        game_manager.has_changed()
    return {'state': game.dict(pid), 'result': result}

@app.route('/game/<game>/buy/<card>', methods=['POST'])
@json_response
def buy_card(game, card):
    pid, game_manager = validate_player(game)
    if game_manager is None:
        return {'error': 'Invalid game / pid / uuid'}
    game = game_manager.game
    if pid != game.active_player_index:
        return {'error': 'Not your turn'}

    result = game.buy({'name': card})
    if result == {}:
        game_manager.has_changed()
    return {'state': game.dict(pid), 'result': result}

@app.route('/game/<game>/next_phase', methods=['POST'])
@json_response
def next_phase(game):
    pid, game_manager = validate_player(game)
    if game_manager is None:
        return {'error': 'Invalid game / pid / uuid'}
    game = game_manager.game
    if pid != game.active_player_index:
        return {'error': 'Not your turn'}

    if game.state == 'action':
        result = game.buy_phase()
    elif game.state == 'buy':
        result = game.next_turn()

    if result == {}:
        game_manager.has_changed()
    return {'state': game.dict(pid), 'result': result}

@app.route('/poll/<game>', methods=['GET'])
@json_response
def poll_game(game):
    pid, game = validate_player(game)
    if game is None:
        return {'error': 'Invalid game / pid / uuid'}
    return game.poll(pid)

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', threaded=True)
