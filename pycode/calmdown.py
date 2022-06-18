from model import *
from pyglet.window import key, mouse

import win32com.client
speaker = win32com.client.Dispatch("SAPI.SpVoice")

import azure.cognitiveservices.speech as speechsdk
speech_key, service_region = "**************", "southeastasia" # registe your speech_key from microsoft azure speech service
service_speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region, speech_recognition_language=None)
speech_recognizer = speechsdk.SpeechRecognizer(speech_config=service_speech_config)
import winsound
import difflib

class Window(pyglet.window.Window):

    def __init__(self, *args, **kwargs):
        super(Window, self).__init__(*args, **kwargs)

        # Whether or not the window exclusively captures the mouse.
        self.exclusive = False

        # When flying gravity has no effect and speed is increased.
        self.flying = False

        # Strafing is moving lateral to the direction you are facing,
        # e.g. moving to the left or right while continuing to face forward.
        #
        # First element is -1 when moving forward, 1 when moving back, and 0
        # otherwise. The second element is -1 when moving left, 1 when moving
        # right, and 0 otherwise.
        self.strafe = [0, 0]

        # Current (x, y, z) position in the world, specified with floats. Note
        # that, perhaps unlike in math class, the y-axis is the vertical axis.
        #self.position = SPAWN_POINT
        #self.previous_position = self.players[0].position

        # First element is rotation of the player in the x-z plane (ground
        # plane) measured from the z-axis down. The second is the rotation
        # angle from the ground plane up. Rotation is in degrees.
        #
        # The vertical plane rotation ranges from -90 (looking straight down) to
        # 90 (looking straight up). The horizontal rotation range is unbounded.
        #self.players[0].rotation = (0, 0)

        # Which sector the player is currently in.
        self.sector = None

        # The crosshairs at the center of the screen.
        self.reticle = None

        # Velocity in the y (upward) direction.
        self.dy = 0

        # A list of blocks the player can place. Hit num keys to cycle.
        self.inventory = [GRASS, SAND, BRICK, STONE]

        # The current block the user can place. Hit num keys to cycle.
        self.block = self.inventory[0]

        # Convenience list of num keys.
        self.num_keys = [
            key._1, key._2, key._3, key._4, key._5,
            key._6, key._7, key._8, key._9, key._0]

        # Instance of the model that handles the world.
        self.model = Model()

        # The label that is displayed in the top left of the canvas.
        self.label = pyglet.text.Label('', font_name='Arial', font_size=18,
            x=10, y=self.height - 10, anchor_x='left', anchor_y='top',
            color=(0, 0, 0, 255))

        self.talk_label = pyglet.text.Label('', font_name='Arial', font_size=18,
            x=10, y=self.height - 40, anchor_x='left', anchor_y='top',
            color=(0, 0, 0, 255))

        # This call schedules the `update()` method to be called
        # TICKS_PER_SEC. This is the main game event loop.
        pyglet.clock.schedule_interval(self.update, 1.0 / TICKS_PER_SEC)

        # commands callback
        self.commands = {
            YOU: self.on_you,
            NICK: self.on_nick,
            #AUTHENTICATE: self.on_authenticate,
            #CHUNK: self.on_chunk,
            BLOCK: self.on_block,
            #LIGHT: self.on_light,
            POSITION: self.on_position,
            TALK: self.on_talk,
            #SIGN: self.on_sign,
            #VERSION: self.on_version,
            DISCONNECT: self.on_disconnect,
            }
        
        # easter eggs
        self.eggs_list = []
        self.eggs_map = {}

        # prompt text at top label
        self.prompt_text = ''
        self.previous_prompt_text = ''
        self.talk_text = ''

        # players
        self.players = {}

        # init self player
        self.players[0] = Player()

        # client
        self.client = None

        # time elapse seconds
        self.time_elapse = 0.0

        # english puzzle's index
        self.english_list_index = 0

    def set_client(self, client):
        self.client = client

    def set_exclusive_mouse(self, exclusive):
        """ If `exclusive` is True, the game will capture the mouse, if False
        the game will ignore the mouse.

        """
        super(Window, self).set_exclusive_mouse(exclusive)
        self.exclusive = exclusive

    def get_sight_vector(self):
        """ Returns the current line of sight vector indicating the direction
        the player is looking.

        """
        x, y = self.players[0].rotation
        # y ranges from -90 to 90, or -pi/2 to pi/2, so m ranges from 0 to 1 and
        # is 1 when looking ahead parallel to the ground and 0 when looking
        # straight up or down.
        m = math.cos(math.radians(y))
        # dy ranges from -1 to 1 and is -1 when looking straight down and 1 when
        # looking straight up.
        dy = math.sin(math.radians(y))
        dx = math.cos(math.radians(x - 90)) * m
        dz = math.sin(math.radians(x - 90)) * m
        return (dx, dy, dz)

    def get_motion_vector(self):
        """ Returns the current motion vector indicating the velocity of the
        player.

        Returns
        -------
        vector : tuple of len 3
            Tuple containing the velocity in x, y, and z respectively.

        """
        if any(self.strafe):
            x, y = self.players[0].rotation
            strafe = math.degrees(math.atan2(*self.strafe))
            y_angle = math.radians(y)
            x_angle = math.radians(x + strafe)
            if self.flying:
                m = math.cos(y_angle)
                dy = math.sin(y_angle)
                if self.strafe[1]:
                    # Moving left or right.
                    dy = 0.0
                    m = 1
                if self.strafe[0] > 0:
                    # Moving backwards.
                    dy *= -1
                # When you are flying up or down, you have less left and right
                # motion.
                dx = math.cos(x_angle) * m
                dz = math.sin(x_angle) * m
            else:
                dy = 0.0
                dx = math.cos(x_angle)
                dz = math.sin(x_angle)
        else:
            dy = 0.0
            dx = 0.0
            dz = 0.0
        return (dx, dy, dz)

    def update(self, dt):
        """ This method is scheduled to be called repeatedly by the pyglet
        clock.

        Parameters
        ----------
        dt : float
            The change in time since the last call.

        """

        # time elapse
        self.players[0].time_remain -= dt
        self.time_elapse += dt
        second_sliced = self.time_elapse % 1.0

        # on timer 1 second
        if second_sliced < dt:
            # egg's tip text
            egg = self.eggs_map.get(normalize(self.players[0].position))
            if (egg != None):
                self.prompt_text = egg[3]
                self.label.text = self.prompt_text
            # speak prompt text
            if self.prompt_text != self.previous_prompt_text:
                self.previous_prompt_text = self.prompt_text
                speak_text = self.prompt_text.split('@',1)
                if 1 < len(speak_text):
                    speaker.Speak(speak_text[1])
            # out of playing time
            if self.players[0].time_remain <= 0:
                self.prompt_text = "Out of playing time, byebye!"
                speaker.Speak(self.prompt_text)
                pyglet.app.exit()

        # socket recv
        if None != self.client:
            data = None
            try:
                data = self.client.conn.recv(1024)
            except:
                data = None
            if None != data:
                #print (data.decode())
                self.on_data(self.client, data.decode())

        # update self player
        self.players[self.players[0].clientid] = self.players[0]

        # send position to server
        if self.players[0].position != self.players[0].previous_position:
            self.client.send_position(self.players[0].position[0], self.players[0].position[1], self.players[0].position[2], self.players[0].rotation[0], self.players[0].rotation[1])
            self.players[0].previous_position = self.players[0].position

        # players collition
        if 3 <= len(self.players):
            # captured by hunter
            if True == self.players_collided():
                if PLAYER_STEALER == self.players[0].player_type:
                    self.players[0].time_remain -= MAX_PLAY_SEC
                    #self.players[0].position = self.players[0].previous_position
                    self.client.send_position(self.players[0].position[0], self.players[0].position[1], self.players[0].position[2], self.players[0].rotation[0], self.players[0].rotation[1])
                    self.prompt_text = "Gosh! You have been captured!"
                    #time.sleep(3)
                    self.players[0].position = (SPAWN_POINT[0]-8,SPAWN_POINT[1],SPAWN_POINT[2])
                if PLAYER_HUNTER == self.players[0].player_type:
                    #self.players[0].time_remain += MAX_PLAY_SEC
                    self.client.send_position(self.players[0].position[0], self.players[0].position[1], self.players[0].position[2], self.players[0].rotation[0], self.players[0].rotation[1])
                    self.prompt_text = "Wow! Capture stealer!"
                    #time.sleep(3)
                    self.players[0].position = (SPAWN_POINT[0]+8,SPAWN_POINT[1],SPAWN_POINT[2])
                print (self.prompt_text)
                speaker.Speak(self.prompt_text)
                #self.prompt_text = '@%s' % english_list[self.english_list_index][1]
                speaker.Speak(english_list[self.english_list_index][1])

            # steal time from hunter
            if PLAYER_STEALER == self.players[0].player_type:
                self.players[0].time_remain += dt/2
            if PLAYER_HUNTER == self.players[0].player_type:
                self.players[0].time_remain -= dt/2
            
        # process window
        self.model.process_queue()
        sector = sectorize(self.players[0].position)
        if sector != self.sector:
            self.model.change_sectors(self.sector, sector)
            if self.sector is None:
                self.model.process_entire_queue()
            self.sector = sector
        m = 8
        dt = min(dt, 0.2)
        for _ in range(m):
            self._update(dt / m)

    def _update(self, dt):
        """ Private implementation of the `update()` method. This is where most
        of the motion logic lives, along with gravity and collision detection.

        Parameters
        ----------
        dt : float
            The change in time since the last call.

        """
        # walking
        speed = FLYING_SPEED if self.flying else WALKING_SPEED
        d = dt * speed # distance covered this tick.
        dx, dy, dz = self.get_motion_vector()
        # New position in space, before accounting for gravity.
        dx, dy, dz = dx * d, dy * d, dz * d
        # gravity
        if not self.flying:
            # Update your vertical speed: if you are falling, speed up until you
            # hit terminal velocity; if you are jumping, slow down until you
            # start falling.
            self.dy -= dt * GRAVITY
            self.dy = max(self.dy, -TERMINAL_VELOCITY)
            dy += self.dy * dt
        # collisions
        x, y, z = self.players[0].position
        x, y, z = self.collide((x + dx, y + dy, z + dz), PLAYER_HEIGHT)
        self.players[0].position = (x, y, z)

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

    def on_mouse_press(self, x, y, button, modifiers):
        """ Called when a mouse button is pressed. See pyglet docs for button
        amd modifier mappings.

        Parameters
        ----------
        x, y : int
            The coordinates of the mouse click. Always center of the screen if
            the mouse is captured.
        button : int
            Number representing mouse button that was clicked. 1 = left button,
            4 = right button.
        modifiers : int
            Number representing any modifying keys that were pressed when the
            mouse button was clicked.

        """
        if self.exclusive:
            vector = self.get_sight_vector()

            # hit player test
            player = self.hitplayer_test(vector, max_distance=4)

            # speak by mirophone
            if player and button == mouse.LEFT and modifiers & key.MOD_CTRL:
                #speaker.Speak('Speak aloud!')
                winsound.Beep(440, 500)
                print ('Speak aloud...')
                result = speech_recognizer.recognize_once()
                if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                    print("Recognized: {}".format(result.text))
                    # match the puzzle's answer
                    diffA = ''.join(char for char in english_list[self.english_list_index][0].upper() if char.isalnum())
                    diffB = ''.join(char for char in result.text.upper() if char.isalnum())
                    match_ratio = difflib.SequenceMatcher(None, diffA, diffB).quick_ratio()
                    self.prompt_text = result.text
                    speaker.Speak('%d分' % int(match_ratio*100))
                    if match_ratio >= 0.9 or english_list[self.english_list_index][0].upper() in result.text.upper():
                        self.matched_pazzle(True)
                    elif match_ratio <= 0.6:
                        self.matched_pazzle(False)
                elif result.reason == speechsdk.ResultReason.NoMatch:
                    print("No speech could be recognized: {}".format(result.no_match_details))
                elif result.reason == speechsdk.ResultReason.Canceled:
                    cancellation_details = result.cancellation_details
                    print("Speech Recognition canceled: {}".format(cancellation_details.reason))
                    if cancellation_details.reason == speechsdk.CancellationReason.Error:
                        print("Error details: {}".format(cancellation_details.error_details))


            # hit player
            if player and button == pyglet.window.mouse.LEFT:
                #self.prompt_text = '@%s' % english_list[self.english_list_index][1]
                speaker.Speak(english_list[self.english_list_index][1])
                return

            block, previous = self.model.hit_test(self.players[0].position, vector)
            if button == mouse.RIGHT:
                # ON OSX, control + left click = right click.
                if previous:
                    # count the addable blocks
                    if self.players[0].addable_blocks != 0:
                        self.model.add_block(previous, self.block)
                        self.client.set_block(previous[0], previous[1], previous[2], self.block)  # send to server
                        if len(self.eggs_list)>0:
                            if previous == self.eggs_list[0][0]:      # add next tips/egg block after removing previous
                                self.model.add_block(self.eggs_list[0][0], self.eggs_list[0][1])
                                self.client.set_block(self.eggs_list[0][0][0], self.eggs_list[0][0][1], self.eggs_list[0][0][2], self.eggs_list[0][1])  # send to server
                        self.players[0].addable_blocks -= 1
            elif button == pyglet.window.mouse.LEFT and block:
                texture_index = self.model.world[block]
                if texture_index != STONE:
                    # count the removeable blocks
                    if self.players[0].removeable_blocks != 0:
                        self.model.remove_block(block)
                        self.client.set_block(block[0], block[1], block[2], 0)  # send remove-action to server
                        self.players[0].removeable_blocks -= 1
                        if block == self.eggs_list[0][0]:
                            if EASTEREGG0_INDEX == self.eggs_list[0][1]:        # egg0 unlimited blocks
                                self.players[0].removeable_blocks = -1
                                self.players[0].addable_blocks = -1
                                self.players[0].time_remain = sum(self.eggs_map.values())   # = recude(labda x,y:x+y, self.eggs_map.values())
                            if EASTEREGG1_INDEX == self.eggs_list[0][1]:        # egg1 enable fly mode
                                self.players[0].enable_flymode = 1
                            self.players[0].time_remain = self.eggs_list[0][4] # gift of this puzzle's time
                            self.eggs_list.pop(0)            # remove egg
                            self.prompt_text = '@congratulations, only left %d eggs now' % len(self.eggs_list)
                            if len(self.eggs_list)>0:        # next egg
                                #self.players[0].time_remain += self.eggs_list[0][4] # if find prvious egg, increase the play seconds
                                if self.eggs_list[0][0] in self.model.world:
                                    self.model.add_block(self.eggs_list[0][0], self.eggs_list[0][1])  # gen new egg
                                    self.client.set_block(self.eggs_list[0][0][0], self.eggs_list[0][0][1], self.eggs_list[0][0][2], self.eggs_list[0][1])  # send to server

        else:
            self.set_exclusive_mouse(True)

    def on_mouse_motion(self, x, y, dx, dy):
        """ Called when the player moves the mouse.

        Parameters
        ----------
        x, y : int
            The coordinates of the mouse click. Always center of the screen if
            the mouse is captured.
        dx, dy : float
            The movement of the mouse.

        """
        if self.exclusive:
            m = 0.15
            x, y = self.players[0].rotation
            x, y = x + dx * m, y + dy * m
            y = max(-90, min(90, y))
            self.players[0].rotation = (x, y)

    def on_key_press(self, symbol, modifiers):
        """ Called when the player presses a key. See pyglet docs for key
        mappings.

        Parameters
        ----------
        symbol : int
            Number representing the key that was pressed.
        modifiers : int
            Number representing any modifying keys that were pressed.

        """
        if symbol == key.ESCAPE:
            self.set_exclusive_mouse(False)

        # talking
        if symbol == key.RETURN:
            if '' != self.talk_text:
                # match the puzzle's answer
                if english_list[self.english_list_index][0] == self.talk_text[1:]:
                    self.matched_pazzle(matched=True)
                else:
                    #self.matched_pazzle(matched=False)
                    self.client.send_talk(self.talk_text)
                self.talk_text = ''

        if '' != self.talk_text:
            return



        if symbol == key.W:
            self.strafe[0] -= 1
        elif symbol == key.S:
            self.strafe[0] += 1
        elif symbol == key.A:
            self.strafe[1] -= 1
        elif symbol == key.D:
            self.strafe[1] += 1
        elif symbol == key.SPACE:
            if self.dy == 0:
                self.dy = JUMP_SPEED
        elif symbol == key.TAB:
            if self.players[0].enable_flymode > 0:
                self.flying = not self.flying
        elif symbol in self.num_keys:
            index = (symbol - self.num_keys[0]) % len(self.inventory)
            self.block = self.inventory[index]

    def matched_pazzle(self, matched):
        factor = [1, -1][not matched]
        self.players[0].time_remain += english_list[self.english_list_index][2] * factor
        self.players[0].removeable_blocks += 10 * factor
        self.players[0].addable_blocks += 10 * factor
        if self.players[0].position[2] == SPAWN_POINT[2]:
            if self.players[0].player_type == PLAYER_STEALER and int(self.players[0].position[0]) == int(SPAWN_POINT[0]-8) \
                or self.players[0].player_type == PLAYER_HUNTER and int(self.players[0].position[0]) == int(SPAWN_POINT[0]+8):
                self.players[0].time_remain += 120 * factor
                self.players[0].removeable_blocks += 20 * factor
                self.players[0].addable_blocks += 20 * factor
        # next puzzle prompt
        if matched:
            self.english_list_index = (self.english_list_index+1) % len(english_list)
            #self.previous_prompt_text = ''
            #self.prompt_text = '@%s' % english_list[self.english_list_index][1]
            speaker.Speak(english_list[self.english_list_index][1])


    def on_key_release(self, symbol, modifiers):
        """ Called when the player releases a key. See pyglet docs for key
        mappings.

        Parameters
        ----------
        symbol : int
            Number representing the key that was pressed.
        modifiers : int
            Number representing any modifying keys that were pressed.

        """

        # talking
        if '' != self.talk_text:
            return

        if symbol == key.W:
            self.strafe[0] += 1
        elif symbol == key.S:
            self.strafe[0] -= 1
        elif symbol == key.A:
            self.strafe[1] += 1
        elif symbol == key.D:
            self.strafe[1] -= 1

    def on_text(self, text):
        if '' == self.talk_text:
            if 'T' == text.upper():
                self.talk_text = '@'
            if '/' == text.upper():
                self.talk_text = '/'
        else:
            self.talk_text += text

    def on_text_motion(self, motion):
        if motion == key.MOTION_BACKSPACE:
            if '' != self.talk_text:
                self.talk_text = self.talk_text[:-1]

    def on_resize(self, width, height):
        """ Called when the window is resized to a new `width` and `height`.

        """
        # label
        self.label.y = height - 10
        # reticle
        if self.reticle:
            self.reticle.delete()
        x, y = self.width // 2, self.height // 2
        n = 10
        self.reticle = pyglet.graphics.vertex_list(4,
            ('v2i', (x - n, y, x + n, y, x, y - n, x, y + n))
        )

    def set_2d(self):
        """ Configure OpenGL to draw in 2d.

        """
        width, height = self.get_size()
        glDisable(GL_DEPTH_TEST)
        viewport = self.get_viewport_size()
        glViewport(0, 0, max(1, viewport[0]), max(1, viewport[1]))
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, max(1, width), 0, max(1, height), -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    def set_3d(self):
        """ Configure OpenGL to draw in 3d.

        """
        width, height = self.get_size()
        glEnable(GL_DEPTH_TEST)
        viewport = self.get_viewport_size()
        glViewport(0, 0, max(1, viewport[0]), max(1, viewport[1]))
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(65.0, width / float(height), 0.1, 60.0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        x, y = self.players[0].rotation
        glRotatef(x, 0, 1, 0)
        glRotatef(-y, math.cos(math.radians(x)), 0, math.sin(math.radians(x)))
        x, y, z = self.players[0].position
        glTranslatef(-x, -y, -z)

    def on_draw(self):
        """ Called by pyglet to draw the canvas.

        """
        self.clear()
        self.set_3d()
        glColor3d(1, 1, 1)
        self.model.batch.draw()
        self.draw_focused_block()
        self.set_2d()
        self.draw_label()
        self.draw_reticle()

    def draw_focused_block(self):
        """ Draw black edges around the block that is currently under the
        crosshairs.

        """
        vector = self.get_sight_vector()
        block = self.model.hit_test(self.players[0].position, vector)[0]
        if block:
            x, y, z = block
            vertex_data = cube_vertices(x, y, z, 0.51)
            glColor3d(0, 0, 0)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            pyglet.graphics.draw(24, GL_QUADS, ('v3f/static', vertex_data))
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

    def draw_label(self):
        """ Draw the label in the top left of the screen.

        """
        x, y, z = self.players[0].position
        #self.label.text = '%02d (%.2f, %.2f, %.2f) %d / %d' % (
        #    pyglet.clock.get_fps(), x, y, z,
        #    len(self.model._shown), len(self.model.world))
        play_time = divmod(self.players[0].time_remain, 60)
        self.label.text = '%02d:%02d (%d, %d, %d) [%s]' % (
            play_time[0], play_time[1], x, y, z,
            self.prompt_text)
        self.label.draw()

        self.talk_label.text = '%s' % (self.talk_text)
        self.talk_label.draw()

    def draw_reticle(self):
        """ Draw the crosshairs in the center of the screen.

        """
        glColor3d(0, 0, 0)
        self.reticle.draw(GL_LINES)

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
                    print ("Invalid : ", line)
                    continue
            args = line.split(',')
            command, args = args[0], args[1:]

            if command in self.commands:
                func = self.commands[command]
                try:
                    func(client, *args)
                except Exception as e:
                    print ("on_data::func Exception:", e)

    def on_you (self, client, client_id, p, q, x, y, z):
        p, q, x, y, z = map(float, (p, q, x, y, z))
        client_id = int(client_id)
        self.players[0].clientid = client_id
        if PLAYER_STEALER == self.players[0].clientid:
            self.eggs_list = eggs_list_1
            self.eggs_map = eggs_map_1
        elif PLAYER_HUNTER <= self.players[0].clientid:
            self.eggs_list = eggs_list_2
            self.eggs_map = eggs_map_2
        else:
            print ("unknown clientid : ", self.players[0].clientid)
            
    def on_nick (self, client, client_id, nick):
        client_id = int(client_id)
        if client_id not in self.players:
            self.players[client_id] = Player()
        self.players[client_id].clientid = client_id
        self.players[client_id].nick = nick
        if 0 != client_id % 2:
            self.players[client_id].player_type = PLAYER_STEALER
            self.players[client_id].position = (SPAWN_POINT[0], 50, SPAWN_POINT[2])
            self.prompt_text = self.players[client_id].nick + ', you are STEALER'
            print ("%s : %d" % (self.prompt_text, client_id))
        if 0 == client_id % 2:
            self.players[client_id].player_type = PLAYER_HUNTER
            self.prompt_text = self.players[client_id].nick + ', you are HUNTER'
            print ("%s : %d" % (self.prompt_text, client_id))
            self.players[client_id].time_remain += MAX_PLAY_SEC

        if client_id == self.players[0].clientid:
            self.players[0] = self.players[client_id]
            speaker.Speak(self.prompt_text)

    def on_block(self, client, p, q, x, y, z, w):
        p, q, x, y, z = map(float, (p, q, x, y, z))
        w = int(w)
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
            if self.players[client_id].position != self.players[client_id].previous_position:
                self.show_player(client_id, self.players[client_id].position)
                self.hide_player(client_id, self.players[client_id].previous_position)
            self.players[client_id].previous_position = self.players[client_id].position
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
                    play_time = divmod(self.players[0].time_remain, 60)
                    player_status = '@%s %s is %s (%d; %d; %d) %02d:%02d %d %d' % \
                        (other_nick, self.players[0].nick, ['stealer','hunter'][not (PLAYER_STEALER==self.players[0].player_type)], \
                        self.players[0].position[0], self.players[0].position[1], self.players[0].position[2], \
                        play_time[0], play_time[1], self.players[0].addable_blocks, self.players[0].removeable_blocks)
                    client.send_talk(player_status)
    def on_disconnect(self, client, client_id):
        client_id = int(client_id)
        if client_id in self.players:
            print ("disconnect : [%d,%s]" % (client_id, self.players[client_id].nick))
            self.hide_player(client_id, self.players[client_id].position)
            self.players.pop(client_id)


    def show_player(self, client_id, position):
        """ Show the player at the given `position`. the
        block of player hasn't been added with add_block()

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position of the player to show.

        """
        if position in self.model.world:
            return
        texture_index = PLAYER1_INDEX + self.players[client_id].player_type - 1
        self.model.shown[position] = TEXTURE_LIST[texture_index]
        self.model._show_block(position, TEXTURE_LIST[texture_index])
    def hide_player(self, client_id, position):
        """ Hide the player at the given `position`. 

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position of the player to hide.

        """
        if position in self.model.world:
            return
        if position in self.model.shown:
            self.model.shown.pop(position)
            self.model._hide_block(position)

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
        px,py,pz = map(int, (self.players[0].position[0],self.players[0].position[1],self.players[0].position[2]))
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

    def hitplayer_test(self, vector, max_distance=8):
        """ Line of sight search from current position. If a player is
        intersected it is returned, along with the block previously in the line
        of sight. If no player is found, return None.

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
        x, y, z = self.players[0].position
        dx, dy, dz = vector
        previous = None
        for _ in range(max_distance * m):
            key = normalize((x, y, z))
            if key != previous:
                if key in self.model.world:
                    return None
                for player_id, player in self.players.items():
                    if player.clientid == self.players[0].clientid:
                        continue
                    if key == normalize(player.position):
                        return player
            previous = key
            x, y, z = x + dx / m, y + dy / m, z + dz / m
        return None
        
def setup_fog():
    """ Configure the OpenGL fog properties.

    """
    # Enable fog. Fog "blends a fog color with each rasterized pixel fragment's
    # post-texturing color."
    glEnable(GL_FOG)
    # Set the fog color.
    glFogfv(GL_FOG_COLOR, (GLfloat * 4)(0.5, 0.69, 1.0, 1))
    # Say we have no preference between rendering speed and quality.
    glHint(GL_FOG_HINT, GL_DONT_CARE)
    # Specify the equation used to compute the blending factor.
    glFogi(GL_FOG_MODE, GL_LINEAR)
    # How close and far away fog starts and ends. The closer the start and end,
    # the denser the fog in the fog range.
    glFogf(GL_FOG_START, 20.0)
    glFogf(GL_FOG_END, 60.0)


def setup():
    """ Basic OpenGL configuration.

    """
    # Set the color of "clear", i.e. the sky, in rgba.
    glClearColor(0.5, 0.69, 1.0, 1)
    # Enable culling (not rendering) of back-facing facets -- facets that aren't
    # visible to you.
    glEnable(GL_CULL_FACE)
    # Set the texture minification/magnification function to GL_NEAREST (nearest
    # in Manhattan distance) to the specified texture coordinates. GL_NEAREST
    # "is generally faster than GL_LINEAR, but it can produce textured images
    # with sharper edges because the transition between texture elements is not
    # as smooth."
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    setup_fog()


import datetime
def expire():
    df = pd.read_csv(r'./calmdown.csv')
    #print (df)
    value_today = str(df['value'][0])
    today = datetime.datetime.today().strftime('%Y%m%d')

    if (value_today == today):
        play_count = int(df['value'][1])
        if (play_count <= 0):
            print ("expired")
            return -1
        df.loc[1,'value'] = str(play_count-1)
    else:
        df.loc[0,'value'] = today
        df.loc[1,'value'] = 3

    df.to_csv(r'./calmdown.csv', index=False)
    return 0



def main():
    
    #if (0 > expire()):
    #    return

    client = None
    try:
        default_args = [DEFAULT_HOST, DEFAULT_PORT]
        args = sys.argv[1:] + [None] * len(default_args)
        host, port = [a or b for a, b in zip(args, default_args)]
        client = Client(host, int(port))
    except Exception as e:
        print ("client conn : ", e)

    window = Window(width=800, height=600, caption='Calm down, Ethan!', resizable=True)
    # set client
    window.set_client(client)
    # Hide the mouse cursor and prevent the mouse from leaving the window.
    window.set_exclusive_mouse(True)
    setup()
    pyglet.app.run()

    window.model.frozen_world()

    if None != client:
        client.conn.close()

if __name__ == '__main__':
    main()
