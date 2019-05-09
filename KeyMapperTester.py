#######################################################################
##                                                                   ##
## A simple demonstration of the KeyMapper class                     ##
##                                                                   ##
#######################################################################
##                                                                   ##
## Original version written by                                       ##
## Ian Eborn (Thaumaturge) in 2014                                   ##
## Updated by                                                        ##
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

# Panda-related importations
from direct.showbase.ShowBase import ShowBase
from direct.task import Task

from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode
from panda3d.core import InputDevice

# A system importation
import random

# import KeyMapper!
from KeyMapper import *

from KeyMapperSaveLoadViaGameSaver import saveKeyMapping, loadKeyMapping

class KeyMapperTester(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.accept("escape", base.userExit)
        base.exitFunc = self.quit
        
        # Set up a basic KeyMapper!
        self.keyMapper = KeyMapper("TesterUserProfiles/testBindings.btn",
                                   "TesterDefaultProfiles/", "TesterUserProfiles/",
                                   self, None, None)
        
        ## Here we inform our KeyMapper of the various keys that we use.
        ##  The list here is long simply to demonstrate various features,
        ##  and to have enough keys that the list scrolls
        ##  Note the four types of key-bindings:
        ##  1) HELD_KEY: A variable is set and un-set for the key, and may be polled as desired
        ##  2) EVENT_PRESSED: A callback is called when the key is pressed
        ##  3) EVENT_RELEASED: A callback is called when the key is released
        ##  4) EVEN_PRESSED_AND_RELEASED: callbacks are called on each of the key being pressed and released
        self.keyMapper.addKey("up", "w", InputDevice.DeviceClass.keyboard, KEYMAP_HELD_KEY)
        self.keyMapper.addKey("down", "s", InputDevice.DeviceClass.keyboard, KEYMAP_HELD_KEY)
        self.keyMapper.addKey("left", "a", InputDevice.DeviceClass.keyboard, KEYMAP_HELD_KEY)
        self.keyMapper.addKey("right", "d", InputDevice.DeviceClass.keyboard, KEYMAP_HELD_KEY)
        self.keyMapper.addKey("jump", "space", InputDevice.DeviceClass.keyboard, KEYMAP_HELD_KEY)
        self.keyMapper.addKey("action", "mouse1", InputDevice.DeviceClass.mouse, KEYMAP_EVENT_RELEASED, self.action)
        self.keyMapper.addKey("lean", "mouse3", InputDevice.DeviceClass.mouse, KEYMAP_HELD_KEY)
        self.keyMapper.addKey("crouch", "c", InputDevice.DeviceClass.keyboard, KEYMAP_HELD_KEY)
        self.keyMapper.addKey("inventoryPrev", "q", InputDevice.DeviceClass.keyboard, KEYMAP_EVENT_PRESSED, self.inventoryPrev)
        self.keyMapper.addKey("inventoryNext", "e", InputDevice.DeviceClass.keyboard, KEYMAP_EVENT_PRESSED, self.inventoryNext)
        self.keyMapper.addKey("grenade", "r", InputDevice.DeviceClass.keyboard, KEYMAP_EVENT_PRESSED_AND_RELEASED, [self.grenadeReady, self.grenadeThrow])
        self.keyMapper.addKey("use item", "enter", InputDevice.DeviceClass.keyboard, KEYMAP_EVENT_RELEASED, self.useItem)

        self.keyMapper.setup()
        # And that's pretty much it for setting up our KeyMapper!
        
        #  A few basic GUI objects, through which we can display
        # various key-states and events
        if base.win.hasSize():
            winWidth = base.win.getXSize()
            winHeight = base.win.getYSize()
        else:
            winWidth = 400
            winHeight = 400
        
        self.keyStateText = OnscreenText(
                             style=1, fg=(0,0,0,1), pos=(5, -20, 0),
                             align=TextNode.ALeft, scale = 14, mayChange = 1,
                             parent=pixel2d)
        self.keyEventText = OnscreenText(
                             style=1, fg=(0,0,0,1), pos=(winWidth/2.0, -20, 0),
                             align=TextNode.ACenter, scale = 14, mayChange = 1,
                             parent=pixel2d)
        
        # A timer used to clear the event-text display, above
        self.clearKeyEventTextTimer = -1
        
        # A list of "items" to go with the "use item" command above, for the fun of it
        self.itemList = ["drone", "cute kitty", "string of unknown length", "rubber chicken with a pulley in the middle", "vampire lord", "strange thing", "elder sign"]
        
        # Set up the main update task
        self.updateTask = taskMgr.add(self.update, "main update task")
    
    # The next few methods exist to be called by our various key-events.
    #  Each sets the text in one of our GUI items, and, if called for,
    # a timer is set to clear it
    def action(self, unused):
        self.keyEventText.setText("Action pressed!")
        self.clearKeyEventTextTimer = 3.0
    
    def useItem(self, unused):
        self.keyEventText.setText("You used the " + random.choice(self.itemList) + "!")
        self.clearKeyEventTextTimer = 3.0
    
    def inventoryNext(self, unused):
        self.keyEventText.setText("Next inventory item~")
        self.clearKeyEventTextTimer = 3.0
    
    def inventoryPrev(self, unused):
        self.keyEventText.setText("Previous inventory item~")
        self.clearKeyEventTextTimer = 3.0
    
    def grenadeReady(self, unused):
        self.keyEventText.setText("Grenade ready!")
        #  We want this message to remain until we release the key, so 
        # we set the timer to a negative value
        self.clearKeyEventTextTimer = -1
    
    def grenadeThrow(self, unused):
        self.keyEventText.setText("Grenade out! Fire in the hole! :D")
        self.clearKeyEventTextTimer = 3.0
    
    #  Here we update our various key-state display GUI items;
    # None of this should directly relate to KeyMapper itself,
    # only our demonstration of it.
    def update(self, task):
        dt = globalClock.getDt()
        
        stateText = "KEY-STATES:\n\n"
        
        # Note that we poll KeyMapper's "keys" dictionary for our key-states
        for key, state in list(self.keyMapper.keys.items()):
            stateText += key
            numTildes = 20 - len(key)
            if numTildes < 0:
                numTildes = 2
            for i in range(numTildes):
                stateText += "~"
            stateText += "  "
            stateText += str(state)
            stateText += "\n\n"
            
        self.keyStateText.setText(stateText)
        
        if self.clearKeyEventTextTimer > 0:
            self.clearKeyEventTextTimer -= dt
            if self.clearKeyEventTextTimer <= 0:
                self.clearKeyEventTextTimer = -1
                self.keyEventText.setText("")
        
        return Task.cont
    
    def quit(self):
        print("Quitting")
        # Clean up the KeyMapper after use
        self.keyMapper.destroy()
        self.keyMapper = None

tester = KeyMapperTester()
tester.run()