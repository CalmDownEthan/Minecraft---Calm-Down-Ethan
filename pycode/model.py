from __future__ import division
from logging import exception
from re import T

import sys
import math
import random
import time

from collections import deque
if 'win' in sys.platform:
    from pyglet import image
    from pyglet.graphics import TextureGroup
    from pyglet.gl import *

from client import *

SPAWN_POINT = (0, 9, 0)
MAX_PLAY_SEC = 5*60   # seconds
PLAYER_UNKNOWN = 0
PLAYER_STEALER = 1
PLAYER_HUNTER = 2


TICKS_PER_SEC = 60

# Size of sectors used to ease block loading.
SECTOR_SIZE = 16

WALKING_SPEED = 5
FLYING_SPEED = 15

GRAVITY = 20.0
MAX_JUMP_HEIGHT = 1.0 # About the height of a block.
# To derive the formula for calculating jump speed, first solve
#    v_t = v_0 + a * t
# for the time at which you achieve maximum height, where a is the acceleration
# due to gravity and v_t = 0. This gives:
#    t = - v_0 / a
# Use t and the desired MAX_JUMP_HEIGHT to solve for v_0 (jump speed) in
#    s = s_0 + v_0 * t + (a * t^2) / 2
JUMP_SPEED = math.sqrt(2 * GRAVITY * MAX_JUMP_HEIGHT)
TERMINAL_VELOCITY = 50

PLAYER_HEIGHT = 2



def cube_vertices(x, y, z, n):
    """ Return the vertices of the cube at position x, y, z with size 2*n.

    """
    return [
        x-n,y+n,z-n, x-n,y+n,z+n, x+n,y+n,z+n, x+n,y+n,z-n,  # top
        x-n,y-n,z-n, x+n,y-n,z-n, x+n,y-n,z+n, x-n,y-n,z+n,  # bottom
        x-n,y-n,z-n, x-n,y-n,z+n, x-n,y+n,z+n, x-n,y+n,z-n,  # left
        x+n,y-n,z+n, x+n,y-n,z-n, x+n,y+n,z-n, x+n,y+n,z+n,  # right
        x-n,y-n,z+n, x+n,y-n,z+n, x+n,y+n,z+n, x-n,y+n,z+n,  # front
        x+n,y-n,z-n, x-n,y-n,z-n, x-n,y+n,z-n, x+n,y+n,z-n,  # back
    ]


def tex_coord(x, y, n=4):
    """ Return the bounding vertices of the texture square.

    """
    m = 1.0 / n
    dx = x * m
    dy = y * m
    return dx, dy, dx + m, dy, dx + m, dy + m, dx, dy + m


def tex_coords(top, bottom, side):
    """ Return a list of the texture squares for the top, bottom and side.

    """
    top = tex_coord(*top)
    bottom = tex_coord(*bottom)
    side = tex_coord(*side)
    result = []
    result.extend(top)
    result.extend(bottom)
    result.extend(side * 4)
    return result


TEXTURE_PATH = 'texture.png'
TEXTURE_LIST = [None]*64
TEXTURE_LIST[EMPTY] = None

GRASS_COORDS = tex_coords((1, 0), (0, 1), (0, 0))
#TEXTURE_LIST.append(GRASS_COORDS)
#GRASS_INDEX = len(TEXTURE_LIST)-1
TEXTURE_LIST[GRASS] = GRASS_COORDS

SAND_COORDS = tex_coords((1, 1), (1, 1), (1, 1))
#TEXTURE_LIST.append(SAND_COORDS)
#SAND_INDEX = len(TEXTURE_LIST)-1
TEXTURE_LIST[SAND] = SAND_COORDS

STONE_COORDS = tex_coords((2, 1), (2, 1), (2, 1))
#TEXTURE_LIST.append(STONE_COORDS)
#STONE_INDEX = len(TEXTURE_LIST)-1
TEXTURE_LIST[STONE] = STONE_COORDS

BRICK_COORDS = tex_coords((2, 0), (2, 0), (2, 0))
#TEXTURE_LIST.append(BRICK_COORDS)
#BRICK_INDEX = len(TEXTURE_LIST)-1
TEXTURE_LIST[BRICK] = BRICK_COORDS

WOOD_COORDS = tex_coords((2, 0), (2, 0), (2, 0))
TEXTURE_LIST[WOOD] = WOOD_COORDS

CEMENT_COORDS = tex_coords((2, 0), (2, 0), (2, 0))
TEXTURE_LIST[CEMENT] = CEMENT_COORDS

DIRT_COORDS = tex_coords((2, 0), (2, 0), (2, 0))
TEXTURE_LIST[DIRT] = DIRT_COORDS

PLANK_COORDS = tex_coords((2, 0), (2, 0), (2, 0))
TEXTURE_LIST[PLANK] = PLANK_COORDS

SNOW_COORDS = tex_coords((2, 0), (2, 0), (2, 0))
TEXTURE_LIST[SNOW] = SNOW_COORDS

GLASS_COORDS = tex_coords((2, 0), (2, 0), (2, 0))
TEXTURE_LIST[GLASS] = GLASS_COORDS

COBBLE_COORDS = tex_coords((2, 0), (2, 0), (2, 0))
TEXTURE_LIST[COBBLE] = COBBLE_COORDS

LIGHT_STONE_COORDS = tex_coords((2, 0), (2, 0), (2, 0))
TEXTURE_LIST[LIGHT_STONE] = LIGHT_STONE_COORDS

DARK_STONE_COORDS = tex_coords((2, 0), (2, 0), (2, 0))
TEXTURE_LIST[DARK_STONE] = DARK_STONE_COORDS

CHEST_COORDS = tex_coords((2, 0), (2, 0), (2, 0))
TEXTURE_LIST[CHEST] = CHEST_COORDS

LEAVES_COORDS = tex_coords((2, 0), (2, 0), (2, 0))
TEXTURE_LIST[LEAVES] = LEAVES_COORDS

CLOUD_COORDS = tex_coords((2, 0), (2, 0), (2, 0))
TEXTURE_LIST[CLOUD] = CLOUD_COORDS

TALL_GRASS_COORDS = tex_coords((2, 0), (2, 0), (2, 0))
TEXTURE_LIST[TALL_GRASS] = TALL_GRASS_COORDS

YELLOW_FLOWER_COORDS = tex_coords((2, 0), (2, 0), (2, 0))
TEXTURE_LIST[YELLOW_FLOWER] = YELLOW_FLOWER_COORDS

RED_FLOWER_COORDS = tex_coords((2, 0), (2, 0), (2, 0))
TEXTURE_LIST[RED_FLOWER] = RED_FLOWER_COORDS

PURPLE_FLOWER_COORDS = tex_coords((2, 0), (2, 0), (2, 0))
TEXTURE_LIST[PURPLE_FLOWER] = PURPLE_FLOWER_COORDS

SUN_FLOWER_COORDS = tex_coords((2, 0), (2, 0), (2, 0))
TEXTURE_LIST[SUN_FLOWER] = SUN_FLOWER_COORDS

WHITE_FLOWER_COORDS = tex_coords((2, 0), (2, 0), (2, 0))
TEXTURE_LIST[WHITE_FLOWER] = WHITE_FLOWER_COORDS

BLUE_FLOWER_COORDS = tex_coords((2, 0), (2, 0), (2, 0))
TEXTURE_LIST[BLUE_FLOWER] = BLUE_FLOWER_COORDS

ALLOWED_ITEMS_START1 = 32

FAKESTONE_COORDS = tex_coords((0, 3), (1, 1), (1, 1))
#TEXTURE_LIST.append(FAKESTONE_COORDS)
#FAKESTONE_INDEX = len(TEXTURE_LIST)-1
FAKESTONE_INDEX = ALLOWED_ITEMS_START1
TEXTURE_LIST[FAKESTONE_INDEX] = FAKESTONE_COORDS

FIRERAIN_COORDS = tex_coords((1, 3), (1, 3), (1, 3))
#TEXTURE_LIST.append(FIRERAIN_COORDS)
#FIRERAIN_INDEX = len(TEXTURE_LIST)-1
FIRERAIN_INDEX = ALLOWED_ITEMS_START1+1
TEXTURE_LIST[FIRERAIN_INDEX] = FIRERAIN_COORDS

TIPS0_COORDS = tex_coords((0, 2), (0, 1), (0, 0))
#TEXTURE_LIST.append(TIPS0_COORDS)
#TIPS0_INDEX = len(TEXTURE_LIST)-1
TIPS0_INDEX = ALLOWED_ITEMS_START1+2
TEXTURE_LIST[TIPS0_INDEX] = TIPS0_COORDS


TIPS1_COORDS = tex_coords((3, 1), (3, 1), (3, 1))
#TEXTURE_LIST.append(TIPS1_COORDS)
#TIPS1_INDEX = len(TEXTURE_LIST)-1
TIPS1_INDEX = ALLOWED_ITEMS_START1+3
TEXTURE_LIST[TIPS1_INDEX] = TIPS1_COORDS

TIPS2_COORDS = tex_coords((1, 0), (2, 2), (2, 2))
#TEXTURE_LIST.append(TIPS2_COORDS)
#TIPS2_INDEX = len(TEXTURE_LIST)-1
TIPS2_INDEX = ALLOWED_ITEMS_START1+4
TEXTURE_LIST[TIPS2_INDEX] = TIPS2_COORDS

TIPS3_COORDS = tex_coords((1, 0), (3, 2), (3, 2))
#TEXTURE_LIST.append(TIPS3_COORDS)
#TIPS3_INDEX = len(TEXTURE_LIST)-1
TIPS3_INDEX = ALLOWED_ITEMS_START1+5
TEXTURE_LIST[TIPS3_INDEX] = TIPS3_COORDS

EASTEREGG0_COORDS = tex_coords((1, 0), (3, 0), (0, 0))
#TEXTURE_LIST.append(EASTEREGG0_COORDS)
#EASTEREGG0_INDEX = len(TEXTURE_LIST)-1
EASTEREGG0_INDEX = ALLOWED_ITEMS_START1+6
TEXTURE_LIST[EASTEREGG0_INDEX] = EASTEREGG0_COORDS


EASTEREGG1_COORDS = tex_coords((3, 1), (3, 1), (3, 1))
#TEXTURE_LIST.append(EASTEREGG1_COORDS)
#EASTEREGG1_INDEX = len(TEXTURE_LIST)-1
EASTEREGG1_INDEX = ALLOWED_ITEMS_START1+7
TEXTURE_LIST[EASTEREGG1_INDEX] = EASTEREGG1_COORDS


PLAYER1_COORDS = tex_coords((2, 3), (2, 3), (2, 3))
#TEXTURE_LIST.append(PLAYER1_COORDS)
#PLAYER1_INDEX = len(TEXTURE_LIST)-1
PLAYER1_INDEX = ALLOWED_ITEMS_START1+8
TEXTURE_LIST[PLAYER1_INDEX] = PLAYER1_COORDS

PLAYER2_COORDS = tex_coords((3, 3), (3, 3), (3, 3))
#TEXTURE_LIST.append(PLAYER2_COORDS)
#PLAYER2_INDEX = len(TEXTURE_LIST)-1
PLAYER2_INDEX = ALLOWED_ITEMS_START1+9
TEXTURE_LIST[PLAYER2_INDEX] = PLAYER2_COORDS




FACES = [
    ( 0, 1, 0),
    ( 0,-1, 0),
    (-1, 0, 0),
    ( 1, 0, 0),
    ( 0, 0, 1),
    ( 0, 0,-1),
]


def normalize(position):
    """ Accepts `position` of arbitrary precision and returns the block
    containing that position.

    Parameters
    ----------
    position : tuple of len 3

    Returns
    -------
    block_position : tuple of ints of len 3

    """
    x, y, z = position
    x, y, z = (int(round(x)), int(round(y)), int(round(z)))
    return (x, y, z)


def sectorize(position):
    """ Returns a tuple representing the sector for the given `position`.

    Parameters
    ----------
    position : tuple of len 3

    Returns
    -------
    sector : tuple of len 3

    """
    x, y, z = normalize(position)
    x, y, z = x // SECTOR_SIZE, y // SECTOR_SIZE, z // SECTOR_SIZE
    return (x, 0, z)


eggs_list_1 = []
eggs_map_1 = {}
eggs_list_2 = []
eggs_map_2 = {}

english_list = []


import pandas as pd
import sympy
class Model(object):

    def __init__(self):

        if 'win' in sys.platform:
            # A Batch is a collection of vertex lists for batched rendering.
            self.batch = pyglet.graphics.Batch()

            # A TextureGroup manages an OpenGL texture.
            self.group = TextureGroup(image.load(TEXTURE_PATH).get_texture())

        # A mapping from position to the texture_index of the block at that position.
        # This defines all the blocks that are currently in the world.
        self.world = {}

        # Same mapping as `world` but only contains blocks that are shown.
        self.shown = {}

        # Mapping from position to a pyglet `VertextList` for all shown blocks.
        self._shown = {}

        # Mapping from sector to a list of positions inside that sector.
        self.sectors = {}

        # Simple function queue implementation. The queue is populated with
        # _show_block() and _hide_block() calls
        self.queue = deque()

        
        self._initialize()
        

    def _initialize(self):
        """ Initialize the world by placing all the blocks.

        """


        # Initialize the previous world by loding csv file
        world_previous = False
        try:
            dfWorld = pd.read_csv(r'./world.csv')
            for csv_index in range(0, len(dfWorld)):
                p_x = int(dfWorld['position_x'][csv_index])
                p_y = int(dfWorld['position_y'][csv_index])
                p_z = int(dfWorld['position_z'][csv_index])
                t_i = int(dfWorld['texture_index'][csv_index])
                self.add_block((p_x, p_y, p_z), t_i, immediate=False)
            world_previous = True
        except Exception as e:
            print ("load world from csv : ", e)

        #n = 80  # 1/2 width and height of world
        n = 120
        s = 1  # step size
        y = SPAWN_POINT[1]  # initial y height
        for x in range(-n, n + 1, s):
            for z in range(-n, n + 1, s):
                # create a layer stone an grass & sand & brick everywhere.
                self.add_block((x, y - 2, z), GRASS, immediate=False)
                self.add_block((x, y - 3, z), SAND, immediate=False)
                self.add_block((x, y - 4, z), BRICK, immediate=False)
                self.add_block((x, y - 5, z), STONE, immediate=False)
                # a secret layer stone an firerain everywhere 
                self.add_block((x, y - 6, z), FIRERAIN_INDEX, immediate=False)
                self.add_block((x, y - 7, z), FIRERAIN_INDEX, immediate=False)
                self.add_block((x, y - 8, z), STONE, immediate=False)

                if x in (-n, n) or z in (-n, n):
                    # create outer walls.
                    #for dy in range(-2, 3):
                    for dy in range(-7, 3):
                        self.add_block((x, y + dy, z), STONE, immediate=False)
        
        # the secret entry of dark layer
        self.add_block((n/2-6, y - 5, n/2-6), FAKESTONE_INDEX, immediate=False)

        # tips start point
        tipstart_x_1 = -int(n/2)
        tipstart_z_1 = -int(n/2)
        tipstart_x_2 = int(n/2)
        tipstart_z_2 = int(n/2)

        # if the world is loaded prvious, do not generate hills
        if False == world_previous:
            # generate the hills randomly
            o = n - 10
            for _ in range(120):
                a = random.randint(-o, o)  # x position of the hill
                b = random.randint(-o, o)  # z position of the hill
                c = y-1  # base of the hill
                h = random.randint(1, 6)  # height of the hill
                s = random.randint(4, 8)  # 2 * s is the side length of the hill
                d = 1  # how quickly to taper off the hills
                t = random.choice([GRASS, SAND, BRICK])
                for yy in range(c, c + h):
                    for xx in range(a - s, a + s + 1):
                        for zz in range(b - s, b + s + 1):
                            if (xx - a) ** 2 + (zz - b) ** 2 > (s + 1) ** 2:
                                continue
                            if (xx - 0) ** 2 + (zz - 0) ** 2 < 5 ** 2:
                                continue
                            self.add_block((xx, yy, zz), t, immediate=False)
                    s -= d  # decrement side lenth so hills taper off

            # generate the mountain of tips0 starting
            for _ in range(1):
                a = tipstart_x_1  # x position of the hill
                b = tipstart_z_1  # z position of the hill
                c = y-1  # base of the hill
                h = random.randint(10, 15)  # height of the hill
                s = random.randint(6, 10)  # 2 * s is the side length of the hill
                d = 1  # how quickly to taper off the hills
                for yy in range(c, c + h):
                    for xx in range(a - s, a + s + 1):
                        for zz in range(b - s, b + s + 1):
                            t = random.choice([GRASS, SAND, BRICK])
                            if (xx - a) ** 2 + (zz - b) ** 2 > (s + 1) ** 2:
                                continue
                            if (xx - 0) ** 2 + (zz - 0) ** 2 < 5 ** 2:
                                continue
                            self.add_block((xx, yy, zz), t, immediate=False)
                    s -= d  # decrement side lenth so hills taper off
            for _ in range(1):
                a = tipstart_x_2  # x position of the hill
                b = tipstart_z_2  # z position of the hill
                c = y-1  # base of the hill
                h = random.randint(10, 15)  # height of the hill
                s = random.randint(6, 10)  # 2 * s is the side length of the hill
                d = 1  # how quickly to taper off the hills
                for yy in range(c, c + h):
                    for xx in range(a - s, a + s + 1):
                        for zz in range(b - s, b + s + 1):
                            t = random.choice([GRASS, SAND, BRICK])
                            if (xx - a) ** 2 + (zz - b) ** 2 > (s + 1) ** 2:
                                continue
                            if (xx - 0) ** 2 + (zz - 0) ** 2 < 5 ** 2:
                                continue
                            self.add_block((xx, yy, zz), t, immediate=False)
                    s -= d  # decrement side lenth so hills taper off

        # generate tips


        # start tips at mountain top
        self.add_block((tipstart_x_1, y+15, tipstart_z_1), PLAYER1_INDEX, immediate=False)
        self.add_block((tipstart_x_1, y+14, tipstart_z_1), TIPS0_INDEX, immediate=False)
        eggs_list_1.append (((tipstart_x_1, y+14, tipstart_z_1), TIPS0_INDEX, '0', 'Next Position : sink in', MAX_PLAY_SEC/2))
        curr_x_1 = tipstart_x_1
        curr_z_1 = tipstart_z_1
        curr_y_1 = y - 3
        rational = sympy.core.numbers.Rational(0,1)
        div_mod_1 = divmod(rational.p, rational.q)


        # start tips at mountain top
        self.add_block((tipstart_x_2, y+15, tipstart_z_2), PLAYER2_INDEX, immediate=False)
        self.add_block((tipstart_x_2, y+14, tipstart_z_2), TIPS0_INDEX, immediate=False)
        eggs_list_2.append (((tipstart_x_2, y+14, tipstart_z_2), TIPS0_INDEX, '0', 'Next Position : sink in', MAX_PLAY_SEC/2))
        curr_x_2 = tipstart_x_2
        curr_z_2 = tipstart_z_2
        curr_y_2 = y - 3
        rational = sympy.core.numbers.Rational(0,1)
        div_mod_2 = divmod(rational.p, rational.q)


        # load puzzles from csv file
        puzzles = []
        df = pd.read_csv(r'./puzzles.csv')
        for csv_index in range(0, len(df)):
            p = str(df['puzzle'][csv_index])
            t = str(df['tip'][csv_index])
            s = int(df['timeout'][csv_index])
            c = str(df['class'][csv_index])
            puzzles.append((p, t, s, c))


        # puzzels of english
        for puzzles_index in range(0, len(puzzles)):
            if 'english' == puzzles[puzzles_index][3]:
                english_list.append((puzzles[puzzles_index][0], puzzles[puzzles_index][1], puzzles[puzzles_index][2]))


        # puzzles and tips
        for puzzles_index in range(0, len(puzzles)):
            if 'math' != puzzles[puzzles_index][3]:
                continue
            curr_x_1 = curr_x_1 + int(int(div_mod_1[0])%100/10)
            curr_z_1 = curr_z_1 + int(div_mod_1[0])%10
            curr_y_1 = curr_y_1 + div_mod_1[1]%10
            # call add_block after removing previous
            #self.add_block(eggs_list[curr_index][0], eggs_list[curr_index][1], immediate=False)
            eggs_list_1.append (((curr_x_1, curr_y_1, curr_z_1), TIPS1_INDEX, puzzles[puzzles_index][0], puzzles[puzzles_index][1], puzzles[puzzles_index][2]))
            curr_index = len(eggs_list_1)-1
            eggs_map_1[eggs_list_1[curr_index][0]] = eggs_list_1[curr_index]
            rational = sympy.simplify(eggs_list_1[curr_index][2])
            div_mod_1 = divmod(rational.p, rational.q)

        for puzzles_index in range(0, len(puzzles)):
            if 'math' != puzzles[puzzles_index][3]:
                continue
            curr_x_2 = curr_x_2 - int(int(div_mod_2[0])%100/10)
            curr_z_2 = curr_z_2 - int(div_mod_2[0])%10
            curr_y_2 = curr_y_2 + div_mod_2[1]%10
            # call add_block after removing previous
            #self.add_block(eggs_list[curr_index][0], eggs_list[curr_index][1], immediate=False)
            eggs_list_2.append (((curr_x_2, curr_y_2, curr_z_2), TIPS1_INDEX, puzzles[puzzles_index][0], puzzles[puzzles_index][1], puzzles[puzzles_index][2]))
            curr_index = len(eggs_list_2)-1
            eggs_map_2[eggs_list_2[curr_index][0]] = eggs_list_2[curr_index]
            rational = sympy.simplify(eggs_list_2[curr_index][2])
            div_mod_2 = divmod(rational.p, rational.q)


        # generate easter egg0
        curr_x_1 = curr_x_1 + int(int(div_mod_1[0])%100/10)
        curr_z_1 = curr_z_1 + int(div_mod_1[0])%10
        curr_y_1 = curr_y_1 + div_mod_1[1]%10
        eggs_list_1.append (((curr_x_1, curr_y_1, curr_z_1), EASTEREGG0_INDEX, '','unlimited blocks', 10*60)) # call add_block after removing previous
        curr_index = len(eggs_list_1)-1
        eggs_map_1[eggs_list_1[curr_index][0]] = eggs_list_1[curr_index]

        curr_x_2 = curr_x_2 - int(int(div_mod_2[0])%100/10)
        curr_z_2 = curr_z_2 - int(div_mod_2[0])%10
        curr_y_2 = curr_y_2 + div_mod_2[1]%10
        eggs_list_2.append (((curr_x_2, curr_y_2, curr_z_2), EASTEREGG0_INDEX, '','unlimited blocks', 10*60)) # call add_block after removing previous
        curr_index = len(eggs_list_2)-1
        eggs_map_2[eggs_list_2[curr_index][0]] = eggs_list_2[curr_index]

        global egg1_position, egg2_position
        # easter eggs1
        egg1_position = (x-3, y-7, z-3)
        eggs_list_1.append ((egg1_position, EASTEREGG1_INDEX, '','try to fly', 30*60)) # call add_block after removing previous
        curr_index = len(eggs_list_1)-1
        eggs_map_1[eggs_list_1[curr_index][0]] = eggs_list_1[curr_index]
        # easter eggs2
        egg2_position = (x, y-7, z)
        eggs_list_1.append((egg2_position, EASTEREGG1_INDEX,'','', 30*60))  # call add_block after removing previous
        curr_index = len(eggs_list_1)-1
        eggs_map_1[eggs_list_1[curr_index][0]] = eggs_list_1[curr_index]


    def hit_test(self, position, vector, max_distance=8):
        """ Line of sight search from current position. If a block is
        intersected it is returned, along with the block previously in the line
        of sight. If no block is found, return None, None.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position to check visibility from.
        vector : tuple of len 3
            The line of sight vector.
        max_distance : int
            How many blocks away to search for a hit.

        """
        m = 8
        x, y, z = position
        dx, dy, dz = vector
        previous = None
        for _ in range(max_distance * m):
            key = normalize((x, y, z))
            if key != previous and key in self.world:
                return key, previous
            previous = key
            x, y, z = x + dx / m, y + dy / m, z + dz / m
        return None, None

    def exposed(self, position):
        """ Returns False is given `position` is surrounded on all 6 sides by
        blocks, True otherwise.

        """
        x, y, z = position
        for dx, dy, dz in FACES:
            if (x + dx, y + dy, z + dz) not in self.world:
                return True
        return False

    def add_block(self, position, texture_index, immediate=True):
        """ Add a block with the given `texture` and `position` to the world.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position of the block to add.
        texture_index : index of list of len 3
            The index of coordinates of the texture squares. Use `tex_coords()` to
            generate.
        immediate : bool
            Whether or not to draw the block immediately.

        """
        if position in self.world:
            self.remove_block(position, immediate)
        self.world[position] = texture_index
        self.sectors.setdefault(sectorize(position), []).append(position)
        if immediate:
            if self.exposed(position):
                self.show_block(position)
            self.check_neighbors(position)

    def remove_block(self, position, immediate=True):
        """ Remove the block at the given `position`.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position of the block to remove.
        immediate : bool
            Whether or not to immediately remove block from canvas.

        """
        if position not in self.world:
            return
        del self.world[position]
        self.sectors[sectorize(position)].remove(position)
        if immediate:
            if position in self.shown:
                self.hide_block(position)
            self.check_neighbors(position)

    def check_neighbors(self, position):
        """ Check all blocks surrounding `position` and ensure their visual
        state is current. This means hiding blocks that are not exposed and
        ensuring that all exposed blocks are shown. Usually used after a block
        is added or removed.

        """
        x, y, z = position
        for dx, dy, dz in FACES:
            key = (x + dx, y + dy, z + dz)
            if key not in self.world:
                continue
            if self.exposed(key):
                if key not in self.shown:
                    self.show_block(key)
            else:
                if key in self.shown:
                    self.hide_block(key)

    def show_block(self, position, immediate=True):
        """ Show the block at the given `position`. This method assumes the
        block has already been added with add_block()

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position of the block to show.
        immediate : bool
            Whether or not to show the block immediately.

        """
        texture = TEXTURE_LIST[self.world[position]]
        self.shown[position] = texture
        if immediate:
            self._show_block(position, texture)
        else:
            self._enqueue(self._show_block, position, texture)

    def _show_block(self, position, texture):
        """ Private implementation of the `show_block()` method.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position of the block to show.
        texture : list of len 3
            The coordinates of the texture squares. Use `tex_coords()` to
            generate.

        """
        x, y, z = position
        vertex_data = cube_vertices(x, y, z, 0.5)
        texture_data = list(texture)
        if 'win' in sys.platform:
            # create vertex list
            # FIXME Maybe `add_indexed()` should be used instead
            self._shown[position] = self.batch.add(24, GL_QUADS, self.group,
                ('v3f/static', vertex_data),
                ('t2f/static', texture_data))

    def hide_block(self, position, immediate=True):
        """ Hide the block at the given `position`. Hiding does not remove the
        block from the world.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position of the block to hide.
        immediate : bool
            Whether or not to immediately remove the block from the canvas.

        """
        if position not in self.shown:
            return
        self.shown.pop(position)
        if immediate:
            self._hide_block(position)
        else:
            self._enqueue(self._hide_block, position)

    def _hide_block(self, position):
        """ Private implementation of the 'hide_block()` method.

        """
        if position not in self._shown:
            return
        self._shown.pop(position).delete()

    def show_sector(self, sector):
        """ Ensure all blocks in the given sector that should be shown are
        drawn to the canvas.

        """
        for position in self.sectors.get(sector, []):
            if position not in self.shown and self.exposed(position):
                self.show_block(position, False)

    def hide_sector(self, sector):
        """ Ensure all blocks in the given sector that should be hidden are
        removed from the canvas.

        """
        for position in self.sectors.get(sector, []):
            if position in self.shown:
                self.hide_block(position, False)

    def change_sectors(self, before, after):
        """ Move from sector `before` to sector `after`. A sector is a
        contiguous x, y sub-region of world. Sectors are used to speed up
        world rendering.

        """
        before_set = set()
        after_set = set()
        pad = 4
        for dx in range(-pad, pad + 1):
            for dy in [0]:  # range(-pad, pad + 1):
                for dz in range(-pad, pad + 1):
                    if dx ** 2 + dy ** 2 + dz ** 2 > (pad + 1) ** 2:
                        continue
                    if before:
                        x, y, z = before
                        before_set.add((x + dx, y + dy, z + dz))
                    if after:
                        x, y, z = after
                        after_set.add((x + dx, y + dy, z + dz))
        show = after_set - before_set
        hide = before_set - after_set
        for sector in show:
            self.show_sector(sector)
        for sector in hide:
            self.hide_sector(sector)

    def _enqueue(self, func, *args):
        """ Add `func` to the internal queue.

        """
        self.queue.append((func, args))

    def _dequeue(self):
        """ Pop the top function from the internal queue and call it.

        """
        func, args = self.queue.popleft()
        func(*args)

    def process_queue(self):
        """ Process the entire queue while taking periodic breaks. This allows
        the game loop to run smoothly. The queue contains calls to
        _show_block() and _hide_block() so this method should be called if
        add_block() or remove_block() was called with immediate=False

        """
        #start = time.clock()
        #while self.queue and time.clock() - start < 1.0 / TICKS_PER_SEC:
        start = time.perf_counter()
        while self.queue and time.perf_counter() - start < 1.0 / TICKS_PER_SEC:
            self._dequeue()

    def process_entire_queue(self):
        """ Process the entire queue with no breaks.

        """
        while self.queue:
            self._dequeue()

    def frozen_world(self):
        """ write the world to the csv file.

        """
        data = []
        for key,value in self.world.items():
            data.append([key[0], key[1], key[2], value])
        df = pd.DataFrame(data, columns = ['position_x','position_y','position_z','texture_index'], dtype=int)
        print ("frozen_world")
        df.to_csv(r'./world.csv', index=False)


class Player(object):

    def __init__(self):

        # client id
        self.clientid = 0

        # nick
        self.nick = ''

        # The player time remaining
        self.time_remain = MAX_PLAY_SEC/2

        # Current (x, y, z) position in the world, specified with floats. Note
        # that, perhaps unlike in math class, the y-axis is the vertical axis.
        self.position = SPAWN_POINT
        self.previous_position = (-1,-1,-1)

        # First element is rotation of the player in the x-z plane (ground
        # plane) measured from the z-axis down. The second is the rotation
        # angle from the ground plane up. Rotation is in degrees.
        #
        # The vertical plane rotation ranges from -90 (looking straight down) to
        # 90 (looking straight up). The horizontal rotation range is unbounded.
        self.rotation = (0, 0)

        # player type : 0-UNKNOWN, 1-STEALER, 2-HUNTER
        self.player_type = PLAYER_UNKNOWN

        # enable fly mode
        self.enable_flymode = 0

        # blocks limit
        self.removeable_blocks = 10
        self.addable_blocks = 10