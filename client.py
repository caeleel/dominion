import requests
import cmd
import argparse
import json
import readline

gid = None
uuid = None
pid = None
start_key = None
server = 'http://localhost:5000'
curr_state = None
keywords = []

def create():
    global gid, start_key
    resp = requests.post(server + '/create')
    gid = resp.json()['game']
    start_key = resp.json()['start']
    print 'created game {0} with start_key {1}'.format(gid, start_key)

def join(game=None):
    global gid, uuid, pid
    if game is None:
        game = gid
    else:
        gid = game
    resp = requests.post(server + '/join/{0}'.format(gid))
    j = resp.json()
    uuid = j['uuid']
    pid = j['id']
    print 'joined as player {0}'.format(pid)

def start():
    global gid, start_key
    resp = requests.post(server + '/start/{0}/{1}'.format(gid, start_key))
    if not resp.json():
        print 'started'
        poll()
    else:
        print resp.json()

def print_state():
    global curr_state

    if not curr_state:
        return

    j = curr_state

    if j['state'] == 'action':
        if j['actions'] <= 0:
            next()
            return
        found = False
        for card in j['deck']['hand']:
            if 'Action' in card['type']:
                found = True
                break
        if not found:
            next()
            return
    elif j['state'] == 'buy' and j['buys'] <= 0:
        next()
        return

    print 'Supply:'
    print '-------'

    if not keywords:
        for c in j['supply']:
            keywords.append(c['card']['name'])

    for c in j['supply']:
        print '{0}: [{1}] / ({2})'.format(c['card']['name'], c['card']['cost'], c['left'])
    print ''
    print 'Hand: ' + ' '.join([x['name'] for x in j['deck']['hand']])
    print 'Actions: {0}'.format(j['actions'])
    print 'Buys: {0}'.format(j['buys'])
    print 'Money: {0}'.format(j['money'])
    print 'Game state: {0}'.format(j['state'])
    print 'Player {0}s turn'.format(j['turn'])

def read(card):
    global curr_state

    if not curr_state:
        return

    for c in curr_state['supply']:
        if c['card']['name'] == card:
            print '[${0}] --- [VP {1}]'.format(c['card']['value'], c['card']['points'])
            for line in c['card']['text']:
                print ' : {0}'.format(line)
            print '(${0}) ~ {1} ~'.format(c['card']['cost'], c['card']['type'])
            return

    print 'no such card.'

def poll():
    global gid, uuid, pid, curr_state
    resp = requests.get(server + '/poll/{0}?uuid={1}&pid={2}'.format(gid, uuid, pid))
    curr_state = resp.json()
    print_state()

def callback(payload):
    global gid, uuid, pid, curr_state
    resp = requests.post(server + '/game/{0}/callback?uuid={1}&pid={2}'.format(gid, uuid, pid), data=json.dumps(payload), headers={'content-type': 'application/json'})
    if resp.json().get('error'):
        print resp.json()['error']
    else:
        curr_state = resp.json()
        print_state()

def buy(card):
    global gid, uuid, pid, curr_state
    resp = requests.post(server + '/game/{0}/buy/{1}?uuid={2}&pid={3}'.format(gid, card, uuid, pid))
    if resp.json().get('error'):
        print resp.json()['error']
    else:
        curr_state = resp.json()
        print_state()

def play(card, payload={}):
    global gid, uuid, pid, curr_state
    resp = requests.post(server + '/game/{0}/play/{1}?uuid={2}&pid={3}'.format(gid, card, uuid, pid), data=json.dumps(payload), headers={'content-type': 'application/json'})
    if resp.json().get('error'):
        print resp.json()['error']
    else:
        curr_state = resp.json()
        print_state()

def treasures():
    global curr_state

    hand = curr_state['deck']['hand']
    for card in hand:
        if card['type'] == 'Treasure':
            play(card['name'])

def next():
    global gid, uuid, pid, curr_state
    resp = requests.post(server + '/game/{0}/next_phase?uuid={1}&pid={2}'.format(gid, uuid, pid))
    if resp.json().get('error'):
        print resp.json()['error']
    else:
        curr_state = resp.json()
        print_state()

class Client(cmd.Cmd):
    prompt = '> '

    def do_create(self, line):
        """Create a new game"""
        create()

    def do_start(self, line):
        """Starts the created game"""
        start()

    def do_join(self, game):
        """Joins game"""
        if game:
            join(game)
        else:
            join()

    def do_play(self, card):
        """Plays the specified card"""
        args = card.split(' ')
        if len(args) == 1:
            play(card)
        else:
            cmd = args[0]
            if cmd in ('Remodel', 'Mine'):
                if len(args) != 3:
                    print '{0} requires exactly 2 arguments'.format(cmd)
                    return
                play(cmd, {'trash': {'name': args[1]}, 'gain': {'name': args[2]}})
            elif cmd in ('Workshop', 'Feast'):
                if len(args) != 2:
                    print '{0} requires exactly 1 argument'.format(cmd)
                    return
                play(cmd, {'gain': {'name': args[1]}})
            else:
                payload = {'cards': []}
                for c in args[1:]:
                    payload['cards'].append({'name': c})
                play(cmd, payload)

    def complete_play(self, text, line, begidx, endidx):
        if not text:
            return keywords
        else:
            return [x for x in keywords if x.startswith(text)]

    def complete_buy(self, text, line, begidx, endidx):
        return self.complete_play(text, line, begidx, endidx)

    def complete_read(self, text, line, begidx, endidx):
        return self.complete_play(text, line, begidx, endidx)

    def do_buy(self, card):
        """Buys the specified card"""
        buy(card)

    def do_print(self, line):
        """Prints the current state of the game"""
        print_state()

    def do_next(self, line):
        """Go to next stage or next player"""
        next()

    def do_treasure(self, line):
        """Play all treasure cards"""
        treasures()

    def do_read(self, card):
        read(card)

    def do_testgame(self, line):
        create()
        join()
        start()

    def do_EOF(self, line):
        print ''
        return True

if __name__ == "__main__":
    readline.parse_and_bind("bind ^I rl_complete")

    parser = argparse.ArgumentParser(description='Client for dominion server.')
    parser.add_argument('server', type=str, nargs='?', help='server to connect to.', default=server)
    args = parser.parse_args()
    server = args.server

    Client().cmdloop()
