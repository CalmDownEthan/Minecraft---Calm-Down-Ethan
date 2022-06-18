from typing import Any
import requests
import socket
import sqlite3
import sys
if 'win' in sys.platform:
    import msvcrt


from client import *
from model import *


class Hunter(object):
    def __init__(self):

        # Instance of the model that handles the world.
        self.model = Model()

        # commands callback
        self.commands = {
            YOU: self.on_you,
            NICK: self.on_nick,
            # AUTHENTICATE: self.on_authenticate,
            # CHUNK: self.on_chunk,
            BLOCK: self.on_block,
            # LIGHT: self.on_light,
            POSITION: self.on_position,
            TALK: self.on_talk,
            # SIGN: self.on_sign,
            # VERSION: self.on_version,
            DISCONNECT: self.on_disconnect,
        }

        # players
        self.players = {}

        # init self player
        self.players[0] = Player()

        # time elapse seconds
        self.time_elapse = 0.0

    def run(self, client):

        # time slice
        dt = 1/TICKS_PER_SEC
        self.time_elapse += dt
        time.sleep(dt)

        # socket recv
        data = None
        try:
            data = client.conn.recv(1024)
        except BlockingIOError as e:
            data = None
        if None != data:
            #print(data.decode())
            self.on_data(client, data.decode())

        # update self player
        self.players[self.players[0].clientid] = self.players[0]

        # send position to server
        if self.players[0].position != self.players[0].previous_position:
            client.send_position(self.players[0].position[0], self.players[0].position[1],
                                 self.players[0].position[2], self.players[0].rotation[0], self.players[0].rotation[1])
            self.players[0].previous_position = self.players[0].position

        # players collition
        if 3 <= len(self.players):
            # captured by hunter
            if True == self.players_collided():
                if PLAYER_STEALER == self.players[0].player_type:
                    self.players[0].time_remain -= MAX_PLAY_SEC
                    client.send_position(self.players[0].position[0], self.players[0].position[1],
                                         self.players[0].position[2], self.players[0].rotation[0], self.players[0].rotation[1])
                    print("captured by hunter, go to the spawn point")
                    time.sleep(3)
                    self.players[0].position = (
                        SPAWN_POINT[0]-8, SPAWN_POINT[1], SPAWN_POINT[2])
                if PLAYER_HUNTER == self.players[0].player_type:
                    self.players[0].time_remain += MAX_PLAY_SEC
                    client.send_position(self.players[0].position[0], self.players[0].position[1],
                                         self.players[0].position[2], self.players[0].rotation[0], self.players[0].rotation[1])
                    print("captured stealer, go to the spawn point")
                    time.sleep(3)
                    self.players[0].position = (
                        SPAWN_POINT[0]+8, SPAWN_POINT[1], SPAWN_POINT[2])

            # steal time from hunter
            # if PLAYER_STEALER == self.players[0].player_type:
            #    self.players[0].time_remain += dt/2
            # if PLAYER_HUNTER == self.players[0].player_type:
            #    self.players[0].time_remain -= dt/2

        # chase stealer
        #second_sliced = self.time_elapse % 0.1
        second_sliced = 0.0
        if second_sliced < dt:
            self.chase()

    def chase(self):
        for client_id, player in self.players.items():
            if 0 == client_id or self.players[0].clientid == client_id:
                continue
            if PLAYER_STEALER == player.player_type:
                sp = list(self.players[0].position)
                for dimension in range(3):
                    gap = player.position[dimension] - sp[dimension]
                    step = 0.03
                    if gap < 0:
                        step *= -1
                    if abs(gap) > 1:
                        sp[dimension] += step
                self.players[0].position = self.collide(tuple(sp), PLAYER_HEIGHT)
                break

    def collide(self, position, height):
        """ Checks to see if the player at the given `position` and `height`
        is colliding with any blocks in the world.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position to check for collisions at.
        height : int or float
            The height of the player.

        Returns
        -------
        position : tuple of len 3
            The new position of the player taking into account collisions.

        """
        # How much overlap with a dimension of a surrounding block you need to
        # have to count as a collision. If 0, touching terrain at all counts as
        # a collision. If .49, you sink into the ground, as if walking through
        # tall grass. If >= .5, you'll fall through the ground.
        pad = 0.25
        p = list(position)
        np = normalize(position)
        for face in FACES:  # check all surrounding blocks
            for i in range(3):  # check each dimension independently
                if not face[i]:
                    continue
                # How much overlap you have with this dimension.
                d = (p[i] - np[i]) * face[i]
                if d < pad:
                    continue
                for dy in range(height):  # check each height
                    op = list(np)
                    op[1] -= dy
                    op[i] += face[i]
                    if tuple(op) not in self.model.world:
                        continue
                    p[i] -= (d - pad) * face[i]
                    if face == (0, -1, 0) or face == (0, 1, 0):
                        # You are colliding with the ground or ceiling, so stop
                        # falling / rising.
                        self.dy = 0
                    break
        return tuple(p)

    def players_collided(self):
        """ Checks to see if the player at the given `position` and `height`
        is colliding with other players in the world.

        Inner Parameters
        ----------
        active : hunters,  list of Player
        passive : stealer, tuple of len 3
            The (x, y, z) position to check for collisions at.
        PLAYER_HEIGHT : int
            The height of the player.

        Returns
        -------
        True: players collided

        """
        px, py, pz = map(
            int, (self.players[0].position[0], self.players[0].position[1], self.players[0].position[2]))
        if SPAWN_POINT[0] == px or SPAWN_POINT[2] == pz:
            return

        # How much overlap with a dimension of a surrounding block you need to
        # have to count as a collision. If 0, touching terrain at all counts as
        # a collision. If .49, you sink into the ground, as if walking through
        # tall grass. If >= .5, you'll fall through the ground.
        for activekey, active in self.players.items():
            for passivekey, passive in self.players.items():
                if active.clientid == passive.clientid or \
                active.player_type == PLAYER_HUNTER and passive.player_type == PLAYER_HUNTER or \
                active.player_type == PLAYER_STEALER and passive.player_type == PLAYER_STEALER:
                    continue
                pad = 0.25
                p = list(active.position)
                np = normalize(active.position)
                np_passive = normalize(passive.position)
                for face in FACES:  # check all surrounding blocks
                    for i in range(3):  # check each dimension independently
                        if not face[i]:
                            continue
                        # How much overlap you have with this dimension.
                        d = (p[i] - np[i]) * face[i]
                        if d < pad:
                            continue
                        for dy in range(PLAYER_HEIGHT):  # check each height
                            op = list(np)
                            op[1] -= dy
                            op[i] += face[i]
                            # You are colliding with the other player
                            if tuple(op) == np_passive:
                                return True
        return False

    def on_data(self, client, data):
        buf = []
        buf.extend(data.replace('\r\n', '\n'))
        lines = []
        while '\n' in buf:
            index = buf.index('\n')
            line = ''.join(buf[:index])
            buf = buf[index + 1:]
            if not line:
                continue
            lines.append(line)
        for line_index in range(len(lines)):
            line = lines[line_index]
            if line_index+2 <= len(lines)-1:
                if (BLOCK == line[0] and TALK == lines[line_index+2][0]):
                    print("Invalid : ", line)
                    continue
            args = line.split(',')
            command, args = args[0], args[1:]

            if command in self.commands:
                func = self.commands[command]
                try:
                    func(client, *args)
                except Exception as e:
                    print("on_data::func Exception:", e)

    def on_you(self, client, client_id, p, q, x, y, z):
        client_id, p, q, x, y, z = map(int, (client_id, p, q, x, y, z))
        self.players[0].clientid = client_id
        # if PLAYER_STEALER == self.players[0].clientid:
        #self.prompt_text = 'you are STEALER'
        #print ("%s : %d" % (self.prompt_text, self.players[0].clientid))
        #self.eggs_list = eggs_list_1
        #self.eggs_map = eggs_map_1
        # elif PLAYER_HUNTER <= self.players[0].clientid:
        #self.prompt_text = 'you are HUNTER'
        #print ("%s : %d" % (self.prompt_text, self.players[0].clientid))
        #self.players[0].time_remain += MAX_PLAY_SEC
        #self.eggs_list = eggs_list_2
        #self.eggs_map = eggs_map_2
        # else:
        #    print ("unknown clientid : ", self.players[0].clientid)

    def on_nick(self, client, client_id, nick):
        client_id = int(client_id)
        if client_id not in self.players:
            self.players[client_id] = Player()
        self.players[client_id].clientid = client_id
        self.players[client_id].nick = nick

        self.players[client_id].player_type = PLAYER_HUNTER
        print("hunter joined : [%d,%s]" % (client_id, nick))

        if client_id == self.players[0].clientid:
            self.players[0] = self.players[client_id]
            #self.prompt_text = self.players[0].nick + ',' + self.prompt_text

    def on_block(self, client, p, q, x, y, z, w):
        p, q, x, y, z, w = map(int, (p, q, x, y, z, w))
        block_position = (x, y, z)
        if 0 == w:
           self.model.remove_block(block_position, immediate=True)
        elif 1 <= w:
           self.model.add_block(block_position, w, immediate=True)

    def on_position(self, client, client_id, x, y, z, rx, ry):
        client_id = int(client_id)
        x, y, z, rx, ry = map(float, (x, y, z, rx, ry))
        if client_id in self.players:
            self.players[client_id].position = (x, y, z)
            self.players[client_id].rotation = (rx, ry)
            # if self.players[client_id].position != self.players[client_id].previous_position:
            #    self.show_player(client_id, self.players[client_id].position)
            #    self.hide_player(client_id, self.players[client_id].previous_position)
            self.players[client_id].previous_position = self.players[client_id].position
        return

    def on_talk(self, client, *args):
        text = ','.join(args)
        print ("on_talk : ", text)
        self.prompt_text = text
        other_nick = text.split('>',1)[0]
        if other_nick != self.players[0].nick:
            if '#' in text:
                plus_time = int(text.split('#',1)[1])
                self.players[0].time_remain += plus_time
                self.prompt_text = '@you have more time %d seconds' % plus_time
            if len(text.split('@',1)) > 1 and len(text.split('@',1)[1].split(' ',1)) > 1:
                if '?' == text.split('@',1)[1].split(' ',1)[1]:
                    player_status = '@%s (%d %d %d) %d %d %d' % \
                        (other_nick, \
                        self.players[0].position[0], self.players[0].position[1], self.players[0].position[2], \
                        self.players[0].time_remain, self.players[0].addable_blocks, self.players[0].removeable_blocks)
                    client.send_talk(player_status)

    def on_disconnect(self, client, client_id):
        client_id = int(client_id)
        if client_id in self.players:
            print("disconnect : [%d,%s]" %
                  (client_id, self.players[client_id].nick))
            #self.hide_player(client_id, self.players[client_id].position)
            self.players.pop(client_id)


def main():
    default_args = [DEFAULT_HOST, DEFAULT_PORT]
    args = sys.argv[1:] + [None] * len(default_args)
    host, port = [a or b for a, b in zip(args, default_args)]
    client = Client(host, int(port), username='hunter')
    hunter = Hunter()
    print("press ESC to exit...")
    while True:
        hunter.run(client)
        if 'win' in sys.platform:
            if msvcrt.kbhit():
                if ord(msvcrt.getch()) == 27:
                    print("msvcrt.kbhit()")
                    break
    hunter.model.frozen_world()
    if None != client:
        client.conn.close()


if __name__ == '__main__':
    main()
