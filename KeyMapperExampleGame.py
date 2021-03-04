#######################################################################
##                                                                   ##
## An more-advanced example of KeyMapper usage than                  ##
## in KeyMapperTester, and a mini Lander-style game                  ##
##                                                                   ##
## For KeyMapper-specific code, check the following:                 ##
##  - The "CustomisedKeyMapper" class                                ##
##  - Player.update,                                                 ##
##  - KeyMapperTestGame.__init__                                     ##
##  - KeyMapperTestGame.playerHitsWall                               ##
##  - KeyMapperTestGame.playerCollectsGem                            ##
##                                                                   ##
#######################################################################
##                                                                   ##
## Original version written by                                       ##
## Ian Eborn (Thaumaturge) in 2019                                   ##
##                                                                   ##
#######################################################################
##                                                                   ##
## This code is licensed under the MIT license. See the              ##
## license file (LICENSE.md) for details.                            ##
## Link, if available:                                               ##
##  https://github.com/ArsThaumaturgis/KeyMapper/blob/master/LICENSE ##
##                                                                   ##
#######################################################################

### Panda-related importations

from direct.showbase.ShowBase import ShowBase

from panda3d.core import Filename, InputDevice
from panda3d.core import CollisionNode, CollisionTube, CollisionSphere, CollisionTraverser, CollisionHandlerPusher
from panda3d.core import NodePath, Vec4, Vec3
from panda3d.core import WindowProperties
from panda3d.core import TextNode
from panda3d.core import AudioSound
from panda3d.core import BitMask32
from direct.task import Task

### KeyMapper importations.

# The latter importation provides dummy save- and load- callbacks,
# so that the game doesn't produce frequent error-dialogues, and
# does issue a warning on first startup.
from KeyMapper import *
from KeyMapperSaveLoadDummy import SaveLoadDummy

### Some basic Python importations

import random, math

### Constants

# To start with, directories used by the game, and by KeyMapper.
# Note that in this case, we're using the game's directory for
# the "user-profile directory"--in a game intended for full
# release, it might be preferable to use the system-provided
# user-appData directory
GAME_DIRECTORY = "./AdvancedExampleFiles/"
KEYMAP_DEFAULT_PROFILE_DIRECTORY = GAME_DIRECTORY + "DefaultProfiles/"
KEYMAP_USER_PROFILE_DIRECTORY = GAME_DIRECTORY + "UserProfiles/"
print ("Saving files to:", KEYMAP_DEFAULT_PROFILE_DIRECTORY, "and", KEYMAP_USER_PROFILE_DIRECTORY)

# The title of the game!
title = "KeyMapper Advanced Example"

# Our controls. Defining them here and using these constants
# reduces the chances of a typo causing a control to appear
# to not work, or some other such bug.
KEY_THRUST = "thrust"
KEY_TURN_LEFT = "left"
KEY_TURN_RIGHT = "right"
KEY_COLLECT = "collect"
KEY_MENU = "menu"

# The location of our models and sound-effects
ASSET_FILES = GAME_DIRECTORY

# Some collision-related identifiers
COLLECTION_OBJ_NAME = "collectionObj"
PLAYER_NAME = "player"
GEM_NAME = "gem"
WALL_NAME = "wall"

### A customised KeyMapper

# This is a fairly simple customisation, but hopefully it
# shows some of how one goes about changing the appearance
# of KeyMapper.

class CustomisedKeyMapper(KeyMapper):
    def __init__(self, bindingFile, defaultProfileDirectory, userProfileDirectory,
                 eventObject, saveCallback, loadCallback,
                 acceptKeyCombinations=False, useNegativeValuesForNegativeAxes = False):
        KeyMapper.__init__(self, bindingFile, defaultProfileDirectory, userProfileDirectory,
                           eventObject, saveCallback, loadCallback,
                           acceptKeyCombinations, useNegativeValuesForNegativeAxes)

        # Make the buttons a little bigger
        self.buttonSize = 0.075
        self.buttonSpacing = self.buttonSize + 0.075

    # With the profile-save-, binding-, error-, and conflict- dialogues, we'll just change
    # the colours in use for this example. We could enact much mroe significant
    # customisations, but for the purposes of this example, let's just do something
    # simple with these.
    #
    # For this purpose, the "setup" method seems a reasonable location to place the code.
    def setup(self):
        KeyMapper.setup(self)

        self.profileSaveDialogue["frameColor"] = (0.225, 0.5, 0.25, 1)
        self.profileSaveTitle["text_fg"] = (0, 0, 0, 1)

        self.bindingDialogue["frameColor"] = (0.225, 0.5, 0.25, 1)
        self.bindingTitle["text_fg"] = (0, 0, 0, 1)
        self.bindingDescriptionKey["text_fg"] = (0, 0, 0, 1)
        self.bindingDescriptionCurrent["text_fg"] = (0, 0, 0, 1)

        self.errorDoneBtn["text_fg"] = (0, 0, 0, 1)
        self.errorDoneBtn["text_bg"] = (0.4, 0.7, 0.8, 1)
        self.errorDoneBtn["frameColor"] = (0.4, 0.7, 0.8, 1)

        self.conflictDialogue["frameColor"] = (0.3, 0.7, 0.35, 1)
        self.conflictTitle["text_fg"] = (0, 0, 0, 1)
        self.conflictLabel["text_fg"] = (0, 0, 0, 1)
        self.conflictContinueBtn["text_fg"] = (0, 0, 0, 1)
        self.conflictContinueBtn["text_bg"] = (0.35, 0.9, 0.5, 1)
        self.conflictContinueBtn["frameColor"] = (0.35, 0.9, 0.5, 1)
        self.conflictCancelBtn["text_fg"] = (0, 0, 0, 1)
        self.conflictCancelBtn["text_bg"] = (0.35, 0.9, 0.5, 1)
        self.conflictCancelBtn["frameColor"] = (0.35, 0.9, 0.5, 1)

    # Rework the profile-menu and the "add profile" button.
    # In short, this is much like the default code, but
    # with a customised appearance and sounds.
    def buildProfileGUI(self):

        frameBounds = self.list["frameSize"]

        self.profileMenu = DirectOptionMenu(
            parent = self.guiRoot,
            scale = self.buttonSize*0.75,
            frameSize = (-4.7, 4.7, -1, 1.5),
            pos = (0, 0, frameBounds[2] - self.buttonSize*1.5),
            text_align = TextNode.ACenter,
            command = self.loadProfile,
            items = list(self.profileDict.keys()),
            initialitem = -1,
            clickSound = base.btnClickSound,
            highlightColor = (0.4, 0.83, 0.39, 1),
            relief = None,
            geom_pos = (0, 0, 0.3),
            geom_scale = 1.2,
            geom = (
                loader.loadModel(ASSET_FILES + "uiButtonNormal"),
                loader.loadModel(ASSET_FILES + "uiButtonClicked"),
                loader.loadModel(ASSET_FILES + "uiButtonHovered"),
                loader.loadModel(ASSET_FILES + "uiButtonDisabled"),
            ),
            popupMarker_geom = loader.loadModel(ASSET_FILES + "uiMenuIndicator"),
            popupMarker_scale = 1.2,
            popupMarker_relief = None)
        self.profileMenu["text"] = "Load profile..."
        self.profileMenu["textMayChange"] = 0

        self.profileMenu["popupMarker_geom"] = loader.loadModel(ASSET_FILES + "uiMenuIndicator")
        self.profileMenu.popupMarkerPos = (3.55, 0, 0.4)
        self.profileMenu.popupMarker.setPos(3.55, 0, 0.4)

        self.profileAddBtn = DirectButton(text = "Add new",
                                   command = self.addNewProfile,
                                   scale = self.buttonSize*0.75,
                                   text_align = TextNode.ACenter,
                                   pos = (0.475, 0, frameBounds[2] - self.buttonSize*1.5),
                                   parent = self.guiRoot,
                                   clickSound = base.btnClickSound,
                                   relief = None,
                                   geom_pos = (0, 0, 0.3),
                                   geom = (
                                       loader.loadModel(ASSET_FILES + "uiButtonNormal"),
                                       loader.loadModel(ASSET_FILES + "uiButtonClicked"),
                                       loader.loadModel(ASSET_FILES + "uiButtonHovered"),
                                       loader.loadModel(ASSET_FILES + "uiButtonDisabled"),
                                   ))

    # A minor tweak to the default behaviour: we add a label
    # with the text "Controls:" above the main GUI.
    def buildMainGUI(self):
        KeyMapper.buildMainGUI(self)

        self.controlsLabel = DirectLabel(text = "Controls:",
                                         parent = self.guiRoot,
                                         relief = None,
                                         scale = 0.08,
                                         pos = (0, 0, 0.425),
                                         text_fg = (0.13, 0.45, 0.25, 1))

    # Rework the main list-object that holds our key-binding buttons
    # Much as with the profile GUI-elements above, this just amounts
    # to tweaking the default construction
    def buildList(self):

        height = 0.8

        self.list = DirectScrolledFrame(pos = (0, 0, 0),
                                        relief = DGG.FLAT,
                                        frameColor = (0.1, 0.2, 0.15, 1),
                                        frameSize = (-0.7, 0.7, -height*0.5, height*0.5),
                                        parent = self.guiRoot)
        self.list["canvasSize"] = (-0.7, 0.5, -(len(self.keyBindings)-1)*self.buttonSpacing - self.firstButtonTopPadding*2.1 + 0.02, 0)

    # Rework how we represent out key-binding buttons.
    # Once again, this is an alteration of the default behaviour.
    def buildButton(self, keyDescription, bindingEntry, axisDirection, btnCommand, btnExtraArgs = None):

        btn = DirectButton(text = keyDescription, command = btnCommand,
                           scale = self.buttonSize,
                           text_scale = 0.75,
                           text_align = TextNode.ALeft,
                           text_pos = (-6, 0, 0),
                           extraArgs = btnExtraArgs,
                           clickSound = base.btnClickSound,
                           relief = None,
                           geom_pos = (0, 0, 0.175),
                           geom_scale = (1.5, 1, 1),
                           geom = (
                                 loader.loadModel(ASSET_FILES + "uiKeyBindNormal"),
                                 loader.loadModel(ASSET_FILES + "uiKeyBindClicked"),
                                 loader.loadModel(ASSET_FILES + "uiKeyBindHovered"),
                                 loader.loadModel(ASSET_FILES + "uiKeyBindDisabled"),
                           ))

        label = DirectLabel(text = self.getBindingName(bindingEntry.binding, axisDirection), parent = btn,
                            scale = 0.75,
                            text_align = TextNode.ARight,
                            relief = None,
                            pos = (6, 0, 0))

        btnWrapper = BasicKeyBindingButtonWrapper(btn, label)

        return btnWrapper


### A simple particle-explosion class.

# Panda3D does include particle-effect functionality,
# but at time of writing it doesn't have a convenient
# means of creating a sudden burst of particles.

# So, since our game is very, very small, and we don't
# expect to have at any given time many such effects,
# or such effects with a great many particles, we're
# creating our own, very simple and limited alternative.

# Doing this is not recommended for a game of scale
# much bigger than this one!

class Explosion():
    def __init__(self, parent, pos, colour, partCount, scale, speed, lifespan):
        self.root = parent.attachNewNode(PandaNode("explosion"))
        self.root.setPos(pos)
        self.root.setZ(self.root, 0.1)
        self.root.setColorScale(colour)
        self.scale = scale

        self.parts = [[loader.loadModel(ASSET_FILES + "explosion"), None] for i in range(partCount)]
        for modelList in self.parts:
            model = modelList[0]
            model.setScale(scale)
            model.setR(random.uniform(0, 360.0))
            model.reparentTo(self.root)
            if partCount == 1:
                modelList[1] = (0, 0)
            else:
                angle = random.uniform(0, 6.283)
                x = math.sin(angle)*speed
                y = math.cos(angle)*speed
                modelList[1] = (x, y)

        self.timer = lifespan

    def update(self, dt):
        self.timer -= dt
        [np.setScale(np, 1.0 - dt*7.0) for np, (x, y) in self.parts]
        [np.setPos(np, x*dt, 0, y*dt) for np, (x, y) in self.parts]

### The player-character.

# In essence, this is a sort of lander-vehicle: it falls
# under (low) gravity, can thrust upwards, and can turn left or right.
# It can also collect gems--but when doing so, it can no
# longer turn or thrust!

class Player():
    def __init__(self, parent):
        self.root = parent.attachNewNode(PandaNode("player"))

        # Make a collision object used to detect
        # collisions with walls
        shape = CollisionSphere(0, 0, 0, 0.15)
        node = CollisionNode(PLAYER_NAME)
        node.addSolid(shape)
        node.setIntoCollideMask(BitMask32(1))
        node.setFromCollideMask(BitMask32(1))
        self.collider = self.root.attachNewNode(node)
        #self.collider.show()

        base.pusher.addCollider(self.collider, self.root)
        base.cTrav.addCollider(self.collider, base.pusher)

        # Make a collision object used to detect
        # collisions with the gems that we collect
        # in this game
        shape = CollisionSphere(0, 0, 0, 0.4)
        shape.setTangible(False)
        node = CollisionNode(COLLECTION_OBJ_NAME)
        node.addSolid(shape)
        node.setIntoCollideMask(BitMask32(0))
        node.setFromCollideMask(BitMask32(2))
        self.collectionCollider = NodePath(node)
        #self.collectionCollider.show()

        base.pusher.addCollider(self.collectionCollider, self.root)
        base.cTrav.addCollider(self.collectionCollider, base.pusher)

        # A visualisation of being in "collection" mode,
        # and of the radius in which we can collect gems
        self.collectionCircle = loader.loadModel(ASSET_FILES + "circle")
        self.collectionCircle.setScale(0.4)
        self.collectionCircle.reparentTo(self.root)
        self.collectionCircle.hide()

        self.collectionColour1 = Vec4(0.1, 0.2, 0.6, 1)
        self.collectionColour2 = Vec4(0.3, 0.6, 1, 1)

        # Our player-character's model
        self.model = loader.loadModel(ASSET_FILES + "player")
        self.model.setScale(0.2)
        self.model.setColorScale(0, 1, 0.3, 1)
        self.model.reparentTo(self.root)

        # A visualisation of the player-character
        # thrusting upwards
        self.flame = loader.loadModel(ASSET_FILES + "flame")
        self.flame.setScale(0.4)
        self.flame.setColorScale(0, 1, 0.3, 1)
        self.flame.setZ(-0.2)
        self.flame.reparentTo(self.root)
        self.flame.hide()

        self.flameColour1 = Vec4(0, 1, 0, 1)
        self.flameColour2 = Vec4(0.1, 0.5, 0.3, 1)

        # Movement-related values
        self.velocity = Vec3(0, 0, 0)
        self.acceleration = 16.0
        self.maxSpeed = 5.0
        self.turnRate = 200.0

        # Whether or not we're in the "collection" state
        self.collecting = False

        # Various sound effects
        self.deathSound = loader.loadSfx(ASSET_FILES + "playerDeath.ogg")
        self.collectionSound = loader.loadSfx(ASSET_FILES + "chimeSingle.ogg")
        self.collectionActiveSound = loader.loadSfx(ASSET_FILES + "loopingHum.ogg")
        self.collectionActiveSound.setLoop(True)
        self.collectionActiveSound.setVolume(0.4)
        self.winSound = loader.loadSfx(ASSET_FILES + "chimesWin.ogg")
        self.flightSound = loader.loadSfx(ASSET_FILES + "fly.ogg")
        self.flightSound.setLoop(True)

    # Update our player-character!
    # In short, apply gravity, apply thrust if applicable,
    # turn if applicable, make sure that we don't go too fast,
    # and update our position. All the while, update the playing
    # and stopping of various sound-effects, and the visibility of
    # the "collection circle" and the "thrust flame".
    #
    # It's here that we use our KeyMapper's "thrust" and "turn" keys
    def update(self, dt, keyMapper):
        speed = self.velocity.length()

        self.velocity.addZ(-4.8*dt)

        self.flame.hide()
        if not self.collecting:
            if self.collectionActiveSound.status() == AudioSound.PLAYING:
                self.collectionActiveSound.stop()

            # KEYMAPPER STUFF! Get the value of the "thrust" key, and apply it--
            # along with an acceleration-value and the delta-time--to the
            # character's "up"-vector. Thus the character thrusts "upwards".
            self.velocity += self.root.getQuat(render).getUp()*keyMapper.keys[KEY_THRUST]*self.acceleration*dt
            if keyMapper.keyIsHeld(KEY_THRUST):
                self.flame.show()
                if self.flightSound.status() != AudioSound.PLAYING:
                    self.flightSound.play()
            else:
                if self.flightSound.status() == AudioSound.PLAYING:
                    self.flightSound.stop()

            # KEYMAPPER STUFF! The the values of the "turn left" and "turn right"
            # keys, and apply them--along with a turn-rate and the delta-time--
            # to the character's rotation (specifically, it's "roll", hence "setR").
            self.root.setR(self.root,
                           keyMapper.keys[KEY_TURN_RIGHT]*self.turnRate*dt - \
                           keyMapper.keys[KEY_TURN_LEFT]*self.turnRate*dt)
        else:
            if self.collectionActiveSound.status() != AudioSound.PLAYING:
                self.collectionActiveSound.play()
            if self.flightSound.status() == AudioSound.PLAYING:
                self.flightSound.stop()

        if speed > self.maxSpeed:
            self.velocity.normalize()
            self.velocity *= self.maxSpeed
            speed = self.maxSpeed

        self.root.setPos(render, self.root.getPos(render) + self.velocity*dt)
        self.root.setY(0)

        perc = math.sin(globalClock.getRealTime()*17.0)*0.5 + 0.5
        self.collectionCircle.setColorScale(self.collectionColour1*perc + self.collectionColour2*(1.0 - perc))
        self.flame.setColorScale(self.flameColour1*perc + self.flameColour2*(1.0 - perc))

    # This is called by the game when the player presses the
    # "collection" key. The actual method called by KeyMapper
    # is in the KeyMapperTestGame class
    def startCollecting(self):
        self.collecting = True
        self.collectionCollider.reparentTo(self.root)
        self.collectionCircle.show()

    # This is called by the game when the player releases the
    # "collection" key. The actual method called by KeyMapper
    # is in the KeyMapperTestGame class
    def endCollecting(self):
        self.collecting = False
        self.collectionCollider.detachNode()
        self.collectionCircle.hide()

    # Clean up our player-object.
    def destroy(self):
        if self.collider is not None:
            base.pusher.removeCollider(self.collider)
            base.cTrav.removeCollider(self.collider)
            self.collider = None

        if self.collectionCollider is not None:
            base.pusher.removeCollider(self.collectionCollider)
            base.cTrav.removeCollider(self.collectionCollider)
            self.collectionCollider = None

        if self.root is not None:
            self.root.removeNode()
            self.root = None


### The game itself.

# This implements the bulk of our little Lander-game,
# and includes our KeyMapper setup (the latter in
# the "__init__" method, just below).

class KeyMapperTestGame(ShowBase):
    def __init__(self):
        # (Note: The KeyMapper-related stuff in this method
        # is found at its end.)

        # Basic Panda setup
        ShowBase.__init__(self)
        self.disableMouse()
        self.exitFunc = self.cleanup

        winProps = WindowProperties()
        winProps.setTitle(title)
        self.win.requestProperties(winProps)

        self.win.setClearColor(Vec4(0.1, 0.1, 0.1, 1))

        # A convenience, allowing us to check the frame-rate
        # if so desired.
        self.accept("f", self.toggleFrameRateMeter)
        self.showFrameRateMeter = False

        self.cam.setPos(0, -20, 0)

        ## The game!

        self.playing = False

        # A list in which to keep active
        # explosions, so that we can update
        # and destroy them, as appropriate
        self.explosions = []

        # Collision-related setup
        base.cTrav = CollisionTraverser()
        self.pusher = CollisionHandlerPusher()
        self.pusher.setHorizontal(True)
        self.pusher.addInPattern("%fn-into-%in")

        # We're interested in two types of collisions: the player's collector
        # hitting a gem (in which case the player gets closer to winning),
        # and the player's collider hitting a wall (in which case the player
        # loses).
        self.accept(COLLECTION_OBJ_NAME + "-into-" + GEM_NAME, self.playerCollectsGem)
        self.accept(PLAYER_NAME + "-into-" + WALL_NAME, self.playerHitsWall)

        # A common node for our level. Putting it into the "unsorted"
        # bin and disabling depth -testing/-writing causes everything
        # to be simply rendered in the order in which it's added to the
        # scene, which is handy for this art-style.
        self.objectRoot = render.attachNewNode(PandaNode("object root"))
        self.objectRoot.setBin("unsorted", 0, 1)
        self.objectRoot.setDepthTest(False)
        self.objectRoot.setDepthWrite(False)
        self.objectRoot.hide()

        # Our level.
        # This model contains the visible geometry of the level,
        # its collision geometry, and empty-nodes enoting spawn-points
        # for gems
        self.levelGeometry = loader.loadModel(ASSET_FILES + "level")
        self.levelGeometry.reparentTo(self.objectRoot)

        self.levelColour1 = Vec4(0.5, 0.3, 0.4, 1)
        self.levelColour2 = Vec4(0.3, 0.2, 0.3, 1)

        # Find the colliders, and give them a name that the
        # collision-system will recognise.
        colliders = self.levelGeometry.findAllMatches("**/+CollisionNode")
        for collider in colliders:
            collider.setName("wall")

        # Set up our gem spawn-points.
        # In short, we sort them into nine "boxes", allowing
        # us to pick one apart from the player's "box". It's
        # not perfect, but it works well enough.
        self.gemSpawnPoints = [
            [ [], [], [] ],
            [ [], [], [] ],
            [ [], [], [] ]
        ]

        spawnNPs = self.levelGeometry.findAllMatches("**/gemSpawn*")
        for np in spawnNPs:
            pos = np.getPos(render)
            rowIndex, colIndex = self.getGemSpawnTile(pos)
            self.gemSpawnPoints[rowIndex][colIndex].append(pos)
            np.removeNode()

        # Set up our player
        self.player = Player(self.objectRoot)
        self.player.root.setBin("fixed", 0)

        # Set up our gem, the item collected
        # by the player. Since there's only
        # ever one gem on-screen at a time,
        # we just re-use the same gem repeatedly.
        self.gemColour = (0.2, 0.5, 1, 1)

        self.gem = loader.loadModel(ASSET_FILES + "gem")
        self.gem.setP(90)
        self.gem.setScale(0.3)
        self.gem.setColorScale(self.gemColour)
        self.gem.reparentTo(self.objectRoot)

        shape = CollisionSphere(0, 0, 0, 0.9)
        node = CollisionNode(GEM_NAME)
        node.addSolid(shape)
        node.setIntoCollideMask(BitMask32(2))
        node.setFromCollideMask(BitMask32(0))
        self.gemCollider = self.gem.attachNewNode(node)
        #self.gemCollider.show()

        # The number of gems required to win
        self.gemCounter = 0
        self.gemTotal = 10

        # The game's UI
        self.btnClickSound = loader.loadSfx(ASSET_FILES + "uiClick.ogg")

        self.gemLabel = DirectLabel(text = "",
                                    scale = 0.07,
                                    text_fg = (1, 1, 1, 1),
                                    text_align = TextNode.ALeft,
                                    pos = (0.01, 0, 0.03),
                                    parent = self.a2dBottomLeft)
        self.gemLabel.hide()

        self.loseText = "You have died! D:\n\n(Press {0})"
        self.winText = "YOU WIN! :D\n\n(Press {0})"

        self.winLabel = DirectLabel(text = self.winText,
                                    scale = 0.1,
                                    text_fg = (0, 1, 0, 1),
                                    text_pos = (0, 0.775),
                                    frameColor = (0, 0, 0, 1),
                                    frameSize = (-7, 7, -2.25, 2.25),
                                    relief = DGG.FLAT,
                                    pos = (0, 0, 0))
        self.winLabel.hide()

        self.loseLabel = DirectLabel(text = self.loseText,
                                    scale = 0.1,
                                    text_fg = (1, 0, 0, 1),
                                    text_pos = (0, 0.775),
                                    frameColor = (0, 0, 0, 1),
                                    frameSize = (-7, 7, -2.25, 2.25),
                                    relief = DGG.FLAT,
                                    pos = (0, 0, 0))
        self.loseLabel.hide()

        self.updateTask = taskMgr.add(self.update, "update")

        self.mainMenuBackdrop = DirectFrame(parent = render2d,
                                            frameSize = (-1, 1, -1, 1),
                                            frameColor = (0, 0, 0, 1))
        self.mainMenu = DirectFrame()

        self.title = DirectLabel(text = title,
                                 scale = 0.12,
                                 pos = (0, 0, 0.85),
                                 relief = None,
                                 parent = self.mainMenu,
                                 text_fg = (0.15, 0.7, 0.18, 1))

        self.startBtn = DirectButton(text = "Start Game",
                                     parent = self.mainMenu,
                                     scale = 0.1,
                                     command = self.newGame,
                                     pos = (0, 0, 0.58),
                                     clickSound = self.btnClickSound,
                                     relief = None,
                                     geom_pos = (0, 0, 0.3),
                                     geom = (
                                         loader.loadModel(ASSET_FILES + "uiButtonNormal"),
                                         loader.loadModel(ASSET_FILES + "uiButtonClicked"),
                                         loader.loadModel(ASSET_FILES + "uiButtonHovered"),
                                         loader.loadModel(ASSET_FILES + "uiButtonDisabled"),
                                     ))

        self.quitBtn = DirectButton(text = "Quit",
                                    parent = self.mainMenu,
                                    scale = 0.1,
                                    command = base.userExit,
                                    pos = (0, 0, -0.9),
                                    clickSound = self.btnClickSound,
                                    relief = None,
                                    geom_pos = (0, 0, 0.3),
                                    geom = (
                                        loader.loadModel(ASSET_FILES + "uiButtonNormal"),
                                        loader.loadModel(ASSET_FILES + "uiButtonClicked"),
                                        loader.loadModel(ASSET_FILES + "uiButtonHovered"),
                                        loader.loadModel(ASSET_FILES + "uiButtonDisabled"),
                                    ))

        # KEYMAPPER STUFF! Here we instantiate our customised KeyMapper,
        # add some controls to it, call its setup method, and seat it in
        # our main menu.
        self.keyMapper = CustomisedKeyMapper(KEYMAP_USER_PROFILE_DIRECTORY + "currentBindings.btn",
                                             KEYMAP_DEFAULT_PROFILE_DIRECTORY, KEYMAP_USER_PROFILE_DIRECTORY,
                                             self, SaveLoadDummy.saveKeyMapping, SaveLoadDummy.loadKeyMapping)

        # Note the "axisDirection" parameter. This is only used for axial inputs--
        # things like gamepad thumb-sticks. A value of "1" indicates the positive
        # axial-direction, and a value of "-1" indicates the negative axial-direction.
        self.keyMapper.addKey(KEY_TURN_LEFT, "Axis.left_x", InputDevice.DeviceClass.gamepad,
                              KEYMAP_HELD_KEY, axisDirection = -1)
        self.keyMapper.addKey(KEY_TURN_RIGHT, "Axis.left_x", InputDevice.DeviceClass.gamepad,
                              KEYMAP_HELD_KEY, axisDirection = 1)
        self.keyMapper.addKey(KEY_THRUST, "face_a", InputDevice.DeviceClass.gamepad, KEYMAP_HELD_KEY)
        self.keyMapper.addKey(KEY_COLLECT, "rtrigger", InputDevice.DeviceClass.gamepad, KEYMAP_EVENT_PRESSED_AND_RELEASED,
                              (self.collectPressed, self.collectReleased))
        self.keyMapper.addKey(KEY_MENU, "back", InputDevice.DeviceClass.gamepad, KEYMAP_EVENT_RELEASED, self.returnToMenu)

        self.keyMapper.setup()

        self.keyMapper.guiRoot.reparentTo(self.mainMenu)
        self.keyMapper.guiRoot.setZ(-0.06)

    def toggleFrameRateMeter(self):
        self.showFrameRateMeter = not self.showFrameRateMeter

        self.setFrameRateMeter(self.showFrameRateMeter)

    def returnToMenu(self, unused = None):
        winProps = WindowProperties()
        winProps.setCursorHidden(False)
        self.win.requestProperties(winProps)

        self.mainMenu.show()

        self.gemLabel.hide()
        self.objectRoot.hide()
        self.winLabel.hide()
        self.loseLabel.hide()

    # Reset the game to its starting-state, and start play.
    def newGame(self):
        self.mainMenu.hide()
        self.mainMenuBackdrop.hide()

        winProps = WindowProperties()
        winProps.setCursorHidden(True)
        self.win.requestProperties(winProps)

        self.objectRoot.show()
        self.player.root.setPos(0, 0, 0)
        self.player.root.setR(0)
        self.player.velocity.set(0, 0, 0)
        self.player.root.show()
        self.player.endCollecting()

        self.gemCounter = self.gemTotal

        self.gem.show()
        self.setNewGemPos()

        self.gemLabel.show()
        self.winLabel.hide()
        self.loseLabel.hide()

        self.updateGemLabelText()

        self.playing = True

    # KEYMAPPER STUFF! This is the method called by KeyMapper
    # when the "collect" key is pressed.
    # We're not using the "key" parameter in this case.
    def collectPressed(self, key):
        if self.playing:
            self.player.startCollecting()

    # KEYMAPPER STUFF! This is the method called by KeyMapper
    # when the "collect" key is released.
    # We're not using the "key" parameter in this case.
    def collectReleased(self, key):
        if self.playing:
            self.player.endCollecting()

    # When the player hits a wall, spawn some explosions, and end the game
    def playerHitsWall(self, entry):
        self.playing = False
        self.explosions.append(Explosion(self.objectRoot, self.player.root.getPos(render), (1, 0, 0, 1), 5, 0.4, 1, 1.7))
        self.explosions.append(Explosion(self.objectRoot, self.player.root.getPos(render), (1, 0, 0, 1), 12, 0.4, 15, 1.7))
        self.player.root.hide()
        # KEYMAPPER STUFF!
        # Here, we fetch the display-name for the input bound to
        # the "menu" control, and use that in our loss-text to tell
        # the player what to press to return to the menu.
        self.loseLabel["text"] = self.loseText.format( \
            self.keyMapper.getBindingName(self.keyMapper.keyBindings[KEY_MENU].binding, 0))
        # (It's perhaps not ideal to have returning to the menu be the
        #  only option here--it might be preferable to allow the player
        #  to more-quickly restart. However, this isn't intended to teach
        #  game-design, and the focus is on the KeyMapper, so we'll leave
        #  it like this.)
        self.loseLabel.show()
        self.player.deathSound.play()
        self.player.collectionActiveSound.stop()
        self.player.flightSound.stop()

    # When the player collects a gem, spawn a blue explosion, update
    # the counter that indicates how many gems remain, and move the
    # gem to give the impression of a new one having spawned.
    def playerCollectsGem(self, entry):
        self.explosions.append(Explosion(self.objectRoot, self.gem.getPos(render), self.gemColour, 12, 0.2, 20, 0.3))
        self.gemCounter -= 1
        self.setNewGemPos()
        self.updateGemLabelText()
        if self.gemCounter <= 0:
            self.playing = False
            self.gem.hide()
            self.winLabel.show()
            # KEYMAPPER STUFF!
            # Here, we fetch the display-name for the input bound to
            # the "menu" control, and use that in our win-text to tell
            # the player what to press to return to the menu.
            self.winLabel["text"] = self.winText.format( \
                self.keyMapper.getBindingName(self.keyMapper.keyBindings[KEY_MENU].binding, 0))
            self.player.winSound.play()
            self.player.collectionActiveSound.stop()
            self.player.flightSound.stop()
        else:
            self.player.collectionSound.play()

    # Figure out which of the nine gem-spawn "boxes"
    # a given position falls within
    def getGemSpawnTile(self, pos):
        rowIndex = int((pos.z + 1.67)/3.333 + 1)
        colIndex = int((pos.x + 1.67)/3.333 + 1)

        return rowIndex, colIndex

    # Place the gem, trying to avoid the player's current- and near- locations
    def setNewGemPos(self):
        playerRow, playerCol = self.getGemSpawnTile(self.player.root.getPos(render))
        spawnList = []
        for rowIndex in range(len(self.gemSpawnPoints)):
            for colIndex in range(len(self.gemSpawnPoints[rowIndex])):
                if rowIndex != playerRow and colIndex != playerCol:
                    spawnList += self.gemSpawnPoints[rowIndex][colIndex]
        self.gem.setPos(random.choice(spawnList))

    def updateGemLabelText(self):
        self.gemLabel.setText("Gems Remaining: {0}/{1}".format(self.gemCounter, self.gemTotal))

    # The core update-method for the game!
    def update(self, task):
        dt = globalClock.getDt()

        # Make the level-geometry fade its colour back and forth.
        perc = math.sin(globalClock.getRealTime()*0.5)*0.5 + 0.5
        self.levelGeometry.setColorScale(self.levelColour1*perc + self.levelColour2*(1.0 - perc))

        # Update our explosions, and remove any that have finished
        [explosion.update(dt) for explosion in self.explosions]
        deadExplosions = [explosion for explosion in self.explosions if explosion.timer <= 0]
        self.explosions = [explosion for explosion in self.explosions if not explosion in deadExplosions]

        for explosion in deadExplosions:
            explosion.root.removeNode()

        # Don't update the player if we're not playing
        if not self.mainMenu.isHidden() or not self.playing:
            return Task.cont

        # Otherwise, >do< update the player.
        self.player.update(dt, self.keyMapper)

        return Task.cont

    # Get rid of all of our explosions
    def cleanupExplosions(self):
        for explosion in self.explosions:
            explosion.root.removeNode()
        self.explosions = []

    # Clean up the game
    def cleanup(self):
        self.cleanupExplosions()

        if self.gem is not None:
            self.gem.removeNode()
            self.gem = None

        if self.player is not None:
            self.player.destroy()
            self.player = None

        if self.mainMenu is not None:
            self.mainMenu.destroy()
            self.mainMenu.removeNode()
            self.mainMenu = None

        if self.gemLabel is not None:
            self.gemLabel.destroy()
            self.gemLabel.removeNode()
            self.gemLabel = None

# Instantiate our game, and run it!
game = KeyMapperTestGame()
game.run()
