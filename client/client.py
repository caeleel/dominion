import requests
import cmd
import argparse
import json
import readline
import sys

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
    global gid, uuid, pid, start_key
    if game is None:
        game = gid
    else:
        gid = game
    resp = requests.post(server + '/join/{0}'.format(gid))
    j = resp.json()
    uuid = j['uuid']
    pid = j['id']
    print 'joined as player {0}'.format(pid)
    if not start_key:
        poll()

def cancel():
    requests.post(server + '/game/{0}/cancel?uuid={1}&pid={2}'.format(gid, uuid, pid))

def start():
    resp = requests.post(server + '/start/{0}/{1}'.format(gid, start_key))
    if not resp.json():
        print 'started'
        poll()
    else:
        print resp.json()

def print_discard():
    if not curr_state:
        return

    print 'Discard'
    print '-------'
    print ', '.join([x['name'] for x in curr_state['deck']['discard']])
    print 'Library size: {0}'.format(curr_state['deck']['library_size'])

def auto_advance():
    if not curr_state:
        return

    j = curr_state

    if j['turn'] == pid:
        if j['state'] == 'action':
            if j['actions'] <= 0:
                next()
                return True
            found = False
            #print j['deck']['hand']
            for card in j['deck']['hand']:
                if 'Action' in card['type']:
                    found = True
                    break
            if not found:
                next()
                return True
        elif j['state'] == 'buy' and j['buys'] <= 0:
            next()
            return True
    return False

def print_state():
    if not curr_state:
        return

    j = curr_state

    print 'Supply:'
    print '-------'

    if not keywords:
        for c in j['supply']:
            keywords.append(c['card']['name'])

    for c in j['supply']:
        print '{0}: [{1}] / ({2})'.format(c['card']['name'], c['card']['cost'], c['left'])
    print ''
    print 'Hand: ' + ' '.join([x['name'] for x in j['deck']['hand']])
    log(-6)
    print 'Actions: {0} / Buys: {1} / Money: {2} / Game state: {3}'.format(
        j['actions'], j['buys'], j['money'], j['state']
    )
    print 'Player {0}s turn'.format(j['turn'])
    if j['callbacks']:
        print 'Callbacks: {0}'.format(j['callbacks'])
    if j['scores']:
        print 'Scores:'
        print '-------'
        for k, v in j['scores'].iteritems():
            print '[{0}]: {1}'.format(k, v)
        sys.exit(0)

def read(card):
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

def log(lines=0):
    if not curr_state or not curr_state.get('log'):
        return

    print ' ~~ Log ~~ '
    for line in curr_state['log'][lines:]:
        print line

def set_state():
    global curr_state

    resp = requests.get(server + '/poll/{0}?uuid={1}&pid={2}'.format(gid, uuid, pid))
    if resp.json().get('cancel'):
        return
    handle_resp(resp)

def wait():
    while True:
        if curr_state['callbacks'] and str(pid) not in curr_state['callbacks']:
            set_state()
        elif curr_state['turn'] != pid:
            if not curr_state['callbacks'] or str(pid) not in curr_state['callbacks']:
                set_state()
            else:
                break
        else:
            break

def poll():
    if not curr_state:
        set_state()
    wait()
    while True:
        if not auto_advance():
            break
        wait()

def handle_resp(resp, do_poll=True):
    global curr_state

    if 'result' in resp.json():
        if resp.json()['result'].get('error'):
            print resp.json()['result']['error']
            return
        else:
            print resp.json()['result']

    curr_state = resp.json()['state']
    print_state()
    if do_poll:
        poll()

def callback(payload):
    resp = requests.post(server + '/game/{0}/callback?uuid={1}&pid={2}'.format(gid, uuid, pid), data=json.dumps(payload), headers={'content-type': 'application/json'})
    handle_resp(resp)

def buy(card):
    resp = requests.post(server + '/game/{0}/buy/{1}?uuid={2}&pid={3}'.format(gid, card, uuid, pid))
    handle_resp(resp)

def play(card, payload={}):
    resp = requests.post(server + '/game/{0}/play/{1}?uuid={2}&pid={3}'.format(gid, card, uuid, pid), data=json.dumps(payload), headers={'content-type': 'application/json'})
    handle_resp(resp)

def treasures():
    global curr_state

    hand = curr_state['deck']['hand']
    for card in hand:
        if card['type'] == 'Treasure':
            play(card['name'])

def list_games():
    resp = requests.get(server + '/list')
    print 'Games:'
    print '------'
    for game in resp.json()['games']:
        active = 'waiting'
        if game['in_progress']:
            active = 'in progress'
        print '{0} -> {1} player(s) | {2}'.format(game['uuid'], game['players'], active)
    print ''

def next():
    resp = requests.post(server + '/game/{0}/next_phase?uuid={1}&pid={2}'.format(gid, uuid, pid))
    handle_resp(resp, False)
    wait()

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

    def parse_cmd(self, args):
        if len(args) == 1:
            return args[0], {}
        else:
            cmd = args[0]
            if cmd == 'Chancellor':
                if len(args) > 2:
                    print '{0} requires 0 or 1 argument'.format(cmd)
                    return None, None
                return cmd, {'discard_deck': len(args) == 2}
            elif cmd == 'CountingHouse':
                if len(args) > 2:
                    print '{0} requires exactly 1 argument'.format(cmd)
                    return None, None
                count = 0
                try:
                    count = int(args[1])
                except ValueError:
                    print '{0} requires an integer argument'.format(cmd)
                    return None, None
                return cmd, {'count': count}
            elif cmd in ('Bishop', 'TradeRoute', 'Mint'):
                if len(args) != 2:
                    print '{0} requires exactly 1 argument'.format(cmd)
                    return None, None
                return cmd, {'card': {'name': args[1]}}
            elif cmd in ('Remodel', 'Mine', 'Expand'):
                if len(args) != 3:
                    print '{0} requires exactly 2 arguments'.format(cmd)
                    return None, None
                return cmd, {'trash': {'name': args[1]}, 'gain': {'name': args[2]}}
            elif cmd in ('Workshop', 'Feast'):
                if len(args) != 2:
                    print '{0} requires exactly 1 argument'.format(cmd)
                    return None, None
                return cmd, {'gain': {'name': args[1]}}
            elif cmd in ('ThroneRoom', 'KingsCourt'):
                cmd2, payload = self.parse_cmd(args[1:])
                return cmd, {'card': {'name': cmd2}, 'payload': payload}
            elif cmd == 'Forge':
                if len(args) < 2:
                    print 'Forge requires at least 1 argument'
                    return None, None
                payload = {
                    'cards': [],
                    'gain': {'name': args[1]},
                }
                for c in args[2:]:
                    payload['cards'].append({'name': c})
                return cmd, payload
            else:
                payload = {'cards': []}
                for c in args[1:]:
                    payload['cards'].append({'name': c})
                return cmd, payload

    def do_play(self, card):
        """Plays the specified card"""
        args = card.split(' ')
        cmd, payload = self.parse_cmd(args)
        if cmd is None:
            return
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

    def do_spend(self, line):
        """Play all treasure cards"""
        treasures()

    def do_read(self, card):
        """Read information about a card"""
        read(card)

    def do_discard(self, line):
        """Inspect your discard pile and library"""
        print_discard()

    def do_testgame(self, line):
        create()
        join()
        start()

    def do_EOF(self, line):
        print ''
        return True

    def do_log(self, line):
        """Read the game log"""
        try:
            line = int(line)
        except ValueError:
            line = 0
        log(-line)

    def do_responses(self, line):
        """Respond to callbacks"""
        args = line.split(' ')
        if not line:
            callback({'cards': []})
        else:
            payload = {'cards': []}
            for c in args:
                payload['cards'].append({'name': c})
            callback(payload)

    def do_response(self, line):
        """Respond to callback"""
        callback({'card': {'name': line}})

    def do_throne2(self, line):
        """Execute secondary throneroom actions"""
        args = line.split(' ')
        cmd, payload = self.parse_cmd(args)
        callback(payload)

    def do_spy(self, line):
        """Finish spying"""
        if not line:
            callback({'discard': []})
            return

        pids = line.split(' ')
        try:
            pids = [int(x) for x in pids]
        except ValueError:
            print 'spy arguments must be ints'
            return
        callback({'discard': pids})

    def do_puttop(self, line):
        """Respond to RoyalSeal"""
        if not line or line == 'no':
            callback({})
        else:
            callback({'put_top': True})

    def do_thief(self, line):
        """Finish thieving"""
        if line == '':
            callback({'to_trash': {}})
            return

        trashes = line.split(',')
        to_trash = {}
        for trash in trashes:
            cmd = trash.split(' ')
            if len(cmd) != 3:
                print 'thief arguments must be sets of 3'
                return
            try:
                cmd[0] = int(cmd[0])
            except ValueError:
                print 'first argument in set must be int'
                return
            to_trash[cmd[0]] = {'name': cmd[2], 'keep': cmd[1] == 'keep'}

        callback({'to_trash': to_trash})

    def do_watchtower(self, line):
        """Respond to watchtower callback"""
        response = {}
        if line == 'trash':
            response = {'trash': True}
        elif line == 'top':
            response = {'put_top': True}
        callback(response)

    def do_library(self, line):
        """Respond to library callback"""
        callback({'keep': line == 'keep'})

    def do_cancel(self, line):
        """Cancel active polls"""
        cancel()

    def do_list(self, line):
        """List active games"""
        list_games()

    def do_resume(self, line):
        """Go back into a game in case it crashes"""
        global gid, uuid, pid

        gid, uuid, pid = line.split(' ')
        pid = int(pid)

if __name__ == "__main__":
    readline.parse_and_bind("bind ^I rl_complete")

    parser = argparse.ArgumentParser(description='Client for dominion server.')
    parser.add_argument('server', type=str, nargs='?', help='server to connect to.', default=server)
    args = parser.parse_args()
    server = args.server

    Client().cmdloop()
