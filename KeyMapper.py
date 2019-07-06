#######################################################################
##                                                                   ##
## KeyMapper - a module for handling keys and key-bindings           ##
## v1.0                                                              ##
##                                                                   ##
#######################################################################
##                                                                   ##
## Original version (0.8) written by                                 ##
## Ian Eborn (Thaumaturge) in 2014                                   ##
## Major updates (to v1.0) by Ian Eborn in 2019                      ##
##                                                                   ##
#######################################################################
##                                                                   ##
## This code is licensed under the MIT license. See the              ##
## license file (LICENSE.md) for details.                            ##
## Link, if available:                                               ##
##  https://github.com/ArsThaumaturgis/KeyMapper/blob/master/LICENSE ##
##                                                                   ##
#######################################################################

from direct.gui.DirectGui import *
from panda3d.core import TextNode, PandaNode, ModifierButtons
from panda3d.core import Filename, VirtualFileSystem
from panda3d.core import InputDevice, ButtonThrower, InputDeviceNode
from panda3d.core import BitMask32

from direct.task import Task

"""The four types of key-binding curently supported. Respectively:
 * Event-released----------------a callback is called on key-release
 * Event-pressed-----------------a callback is called on key-press
 * Event-pressed-and-released----callbacks are called for both key -press and -release
 * Held--------------------------a variable is created to represent the key's state, with
                                 a value of True indicating that it is held and False
                                 indicating that it is not. The variable may then be polled at will"""
KEYMAP_EVENT_RELEASED = 0
KEYMAP_EVENT_PRESSED = 1
KEYMAP_EVENT_PRESSED_AND_RELEASED = 2
KEYMAP_HELD_KEY = 3

DEVICE_TYPE_TAG = "deviceTag"

class KeyBindingButtonWrapper():
    """The base class from which KeyMapper's button-wrappers
    are intended to be derived.
    
    KeyMapper stores all of the buttons in its binding list,
    each intended to be in a wrapper such as this. When a
    key-binding is changed, the wrapper's "setBindingText" method
    is called, allowing the wrapper to update the button's
    representation of that key-binding in whatever way makes sense
    for the approach to the binding buttons that it is intended to
    deal with.
    
    All of the methods of this base class are stubs; it is
    intended only as the template for more-complete wrappers."""
    
    def __init__(self):
        pass
    
    def setBindingText(self, newText):
        """Update the button's representation of the currentBinding.
        
        Params: newText -- The new representation of the binding"""
        
        pass
    
    def destroy(self):
        pass

class BasicKeyBindingButtonWrapper(KeyBindingButtonWrapper):
    """A button-wrapper representing the default approach to
    KeyMapper's list-buttons: a button with an attached label,
    the latter of which displays the key to which the control
    is bound."""
    
    def __init__(self, btn, label):
        KeyBindingButtonWrapper.__init__(self)
        
        self.button = btn
        self.label = label
    
    def setZ(self, newZ):
        """Set the button's z-position.
        
        Params: newZ -- The new z-position
        
        A convenience method used by KeyMapper's default
        implementation of the binding buttons."""
        
        self.button.setZ(newZ)
    
    def reparentTo(self, newParent):
        """Give the button a new parent.
        
        Params: newParent -- The NodePath to become the parent of the button
        
        A convenience method used by KeyMapper's default
        implementation of the binding buttons."""
        
        self.button.reparentTo(newParent)
    
    def setBindingText(self, newText):
        """Update the button's representation of the currentBinding.
        
        Params: newText -- The new representation of the binding"""
        
        self.label["text"] = newText
        self.label.setText()
        self.label.resetFrameSize()

    def destroy(self):
        """Clean up the button wrapper, as well as its button and label."""
        
        KeyBindingButtonWrapper.destroy(self)
        
        if self.button is not None:
            if not self.button.isEmpty():
                self.button["extraArgs"] = None
                self.button.destroy()
                self.button.removeNode()
            self.button = None
        if self.label is not None:
            if not self.label.isEmpty():
                self.label.destroy()
                self.label.removeNode()
            self.label = None

class KeyBinding():
    def __init__(self):
        self.keyDescription = None
        self.binding = None
        self.defaultBinding = None
        self.type = None
        self.callback = None
        self.deviceType = None
        self.defaultDeviceType = None
        self.axisDirection = 0
        self.groupID = BitMask32(1)

class AxisData():
    def __init__(self):
        self.axis = ""
        self.keyDescriptionPositive = None
        self.keyDescriptionNegative = None
        self.deadZone = 0
        self.deviceTypePositive = None
        self.deviceTypeNegative = None
        self.devicePositive = None
        self.deviceNegative = None

class KeyMapper():
    """The main KeyMapper class"""
    
    def __init__(self, bindingFile, defaultProfileDirectory, userProfileDirectory,
                 eventObject, saveCallback, loadCallback,
                 acceptKeyCombinations=False, useNegativeValuesForNegativeAxes = False,
                 keyStateCallback = None):
        """Initialise the KeyMapper.
        
        Params: bindingFile -- The name of the file on disk in
                               which the key-bindings are to be saved
                defaultProfileDirectory -- The directory in which the default key-binding
                                           profiles are found
                userProfileDirectory -- The directory into which the user's key-bindings
                                        and additional profiles should be saved
                eventObject -- An object that derives from DirectObject,
                               and which is expected to provide event-handling
                saveCallback -- A method that will handle the file-writing of
                                key-binding data produced by KeyMapper
                loadCallback -- A method that will handle the file-reading of
                                key-binding data to be used by KeyMapper
                acceptKeyCombinations -- A boolean value indicating whether
                                         modifier-based key-combinations are to
                                         be accepted. Defaults to False.
                useNegativeValuesForNegativeAxes -- Whether negative axial inputs should
                                                    produce negative key-values
                keyStateCallback -- An optional method that can be called when a key
                                    -press or -release alters a key-map value"""

        """ Information on the save- and load- callbacks:


        ~SAVE-CALLBACK~

        * The save-callback is expected to take three parameters:
          keySaveData, axisSaveData, fileName

        * keySaveData is the data produced for key-bindings
         - Structure: list of lists of key-binding data.

             The key-binding data-lists have the following structure:

               [keyDescription, currentBinding, deviceType]

               i.e.: [key-description/control-name, currently-bound button/axis, type of device associated with the binding]

        * axisSaveData is the data produced for axes being used
         - Structure:  list of lists of axis-data

            The axis data-lists have the following structure:

              [axisName, deadZoneValue, deviceTypePositive, deviceTypeNegative,
               keyDescriptionPositive, keyDescriptionNegative]

              i.e.: [the axis in question, the dead-zone for this axis,
                     the type of device associated with positive axis-values,
                     the type of device associated with negative axis-values,
                     the key-description/control bound to positive axis-values,
                     the key-description/control bound to negative axis-values]

        * fileName is the Panda Filename-object that indicates the file to be saved to.


        ~LOAD-CALLBACK~

        The load-callback is expected to take three parameters:
          fileName

        * fileName is the Panda Filename-object that indicates the file to be loaded from.

        As to return-value, this callback is expected to return key-mapping data
        in the same format as the save-callback takes in.

        That is, it's expected to return a list/tuple containing
        two lists--the first being a list of key-binding data-lists,
        and the second being a list of axis data-lists.

         Something like this:
         [
           [
             [key-binding data 1], [key-binding data 2], ...
           ],
           [
             [axis-data 1], [axis-data 2], ...
           ]
         ]
        """
        
        # These first three variables are KeyMapper's representation of the relevant key-states
        
        #  The first of these, self.keys, is the dictionary that may
        # be polled by applications enquiring after the states of keys
        # that use the "key-held" binding type.

        #  This dictionary stores values between zero and one.
        # If an application just wants to know whether a key has been pressed or not,
        # this can be queried via the convenience function "keyIsHeld".
        
        #  The second, self.keyBindings, is intended for internal KeyMapper
        # use: it stores the current binding, default binding, binding type and
        # callback, if any, for a given key
        
        #  Finally, the last, self.keyOrder, simply specifies the order in which
        # the keys are to be represented in the binding list; it is simply a list
        # of the key-names, with placement in this list giving the placement in
        # the GUI list.
        
        self.keys = {}        # Arranged like so: {key-name : state}
        self.keyBindings = {} # Arranged like so: {key-name : key-binding object}
        self.keyOrder = []    # Gives the order in which they keys should appear in the GUI list

        self.keyStateCallback = keyStateCallback
        
        self.acceptKeyCombinations = acceptKeyCombinations
        if not acceptKeyCombinations:
            base.mouseWatcherNode.setModifierButtons(ModifierButtons())
            base.buttonThrowers[0].node().setModifierButtons(ModifierButtons())

        self.negativeValuesForNegativeAxes = useNegativeValuesForNegativeAxes
        
        self.bindingFile = Filename(bindingFile)
        self.bindingFileCustom = self.bindingFile
        self.eventObject = eventObject

        self.defaultProfileDirectory = defaultProfileDirectory
        self.userProfileDirectory = userProfileDirectory
        self.profileDict = {}

        vfs = VirtualFileSystem.getGlobalPtr()
        if not vfs.exists(self.defaultProfileDirectory):
            succeeded = vfs.makeDirectoryFull(self.defaultProfileDirectory)
            if not succeeded:
                print ("Warning! Failed to create default profile directory: ", self.defaultProfileDirectory)

        if not vfs.exists(self.userProfileDirectory):
            succeeded = vfs.makeDirectoryFull(self.userProfileDirectory)
            if not succeeded:
                print ("Warning! Failed to create user profile directory: ", self.userProfileDirectory)

        self.getAvailableProfiles()

        self.keyInterceptionEvents = [
            "keyInterception",
            "keyRelease"
        ]
        
        #  Button thrower and the two events registered below allow us to catch
        # arbitrary button events, via which we set new bindings
        self.buttonThrower = base.buttonThrowers[0].node()
        self.eventObject.accept("keyInterception", self.keyInterception, extraArgs = [None])
        self.eventObject.accept("keyRelease", self.keyRelease)

        for deviceType in InputDevice.DeviceClass:
            if deviceType is not InputDevice.DeviceClass.keyboard and \
                deviceType is not InputDevice.DeviceClass.mouse:
                deviceTypeString = self.getDeviceTypeString(deviceType)
                eventString = "keyInterception_" + deviceTypeString
                self.eventObject.accept(eventString,
                                        self.keyInterception,
                                        extraArgs = [deviceTypeString])
                self.keyInterceptionEvents.append(eventString)

        self.deviceButtonThrowers = {}
        self.dataNPList = []
        self.deviceAxisTestValues = {}

        self.eventObject.accept("connect-device", self.connectController)
        self.eventObject.accept("disconnect-device", self.disconnectController)
        
        self.lastKeyInterception = ""
        self.lastKeyInterceptionDeviceType = None
        self.keyBeingBound = None
        
        self.buttonList = []
        
        self.list = None
        self.guiRoot = aspect2d.attachNewNode(PandaNode("KeyMapper"))
        
        self.currentConflict = None
        
        #  Some parameters used in creating the GUI; these may be altered
        # as desired by the user before calling "setup" in order to
        # adjust the appearance of the list.
        self.buttonSize = 0.05
        self.buttonSpacing = self.buttonSize + 0.05
        self.firstButtonTopPadding = self.buttonSize*2.0
        self.listLength = 10

        self.devicesInUse = {}

        self.deadZoneDefaultValue = 0.3
        self.axesInUse = [] # ["AxisData" objects]

        self.updateTask = None

        self.loadMappingCallback = loadCallback
        self.saveMappingCallback = saveCallback

    """""
    METHODS INTENDED FOR DEVELOPER-USE:
    """""

    """
    Setting up KeyMapper:
    """

    def addKey(self, description, defaultKey, defaultKeyDeviceType, keyType,
               callback = None, axisDirection = 0, groupID = None):
        """Add a key to the list of controls managed by the KeyMapper.

        Params: description -- The name of the key (such as 'move forward' or 'shoot');
                               this should uniquely identify the key, as it is used
                               to identify it within KeyMapper.
                defaultKey -- The default mapping for this key.
                keyType -- The type of binding to be used, selected from:
                            KEYMAP_EVENT_RELEASED, KEYMAP_EVENT_PRESSED,
                            KEYMAP_EVENT_PRESSED_AND_RELEASED and KEYMAP_HELD_KEY
                callback -- The callback--if any--to be used for binding types other than
                            KEYMAP_HELD_KEY.
                            In the case of KEYMAP_EVENT_PRESSED_AND_RELEASED, this may be
                            either:
                             * A single callback (in which case the same callback is
                               used for both events, with an additional event-type parameter
                               being provided to it (which should have a value of either
                               KEYMAP_EVENT_PRESSED or KEYMAP_EVENT_RELEASED, as appropriate)),
                            or
                              * A list or tuple holding two callbacks, in which case the first
                                should be called on key-down and the second on key-up."""

        self.keys[description] = 0
        defaultKeyDeviceTypeStr = self.getDeviceTypeString(defaultKeyDeviceType)
        newBinding = KeyBinding()
        newBinding.keyDescription = description
        newBinding.binding = defaultKey
        newBinding.defaultBinding = defaultKey
        newBinding.type = keyType
        newBinding.callback = callback
        newBinding.defaultDeviceType = defaultKeyDeviceTypeStr
        newBinding.deviceType = defaultKeyDeviceTypeStr
        newBinding.axisDirection = axisDirection

        if groupID is not None:
            if not isinstance(groupID, BitMask32):
                groupID = BitMask32(groupID)
            newBinding.groupID = groupID

        self.keyBindings[description] = newBinding

        self.bindKey(description, defaultKey, keyType, callback, defaultKeyDeviceTypeStr, axisDirection)

        self.keyOrder.append(description)

    def setup(self):
        """Set up the KeyMapper after adding the relevant keys,
        initialising the key-maps and constructing the GUI"""

        # Build the error dialogue first, in case
        # something goes wrong...
        self.buildErrorGUI()
        self.errorDialogue.hide()

        self.loadKeyMapping()
        self.saveKeyMapping()

        self.buildMainGUI()
        self.buildBindingGUI()
        self.buildConflictGUI()
        self.buildProfileSaveGUI()

        self.conflictDialogue.hide()
        self.profileSaveDialogue.hide()
        self.bindingDialogue.hide()

        self.bindingDialogueVisible = False

        self.lastKeyInterception = None
        self.lastKeyInterceptionDeviceType = None
        self.lastKeyInterceptionValue = 0

        # This works around the potential issue of
        # the dialogue's modal nature being overridden
        # as a result of other GUI items being created after it.
        if not self.errorDialogue.isHidden():
            self.errorDialogue.show()

        self.updateTask = taskMgr.add(self.update, "update keymapper")

    """
    UI-related methods. Override as called for!
    """

    def getBindingName(self, binding, direction):
        """Get the display-name for a given binding, or lack thereof."""

        result = "<none set>"
        if binding is not None:
            result = binding
            if direction == 1:
                result += " +"
            elif direction == -1:
                result += " -"
        return result

    def getButtonName(self, keyDescription):
        """Get the display-name for a given control"""

        return keyDescription

    def buildErrorGUI(self):
        """Construct the UI that provides error feedback.

        This may be overridden to change said UI."""

        self.errorDialogue = DirectDialog(frameSize = (-0.8, 0.8, -0.4, 0.4),
                                              frameColor = (0.2, 0.3, 0.7, 1),
                                              fadeScreen = 0.4,
                                              image = None,
                                              geom = None,
                                              relief = DGG.FLAT)

        self.errorTitle = DirectLabel(text = "Error!",
                                              scale = 0.09,
                                              text_align = TextNode.ACenter,
                                              text_fg = (1, 1, 1, 1),
                                              parent = self.errorDialogue,
                                              pos = (0, 0, 0.3),
                                              relief = None)
        self.errorLabel = DirectLabel(text = "<Error text here>",
                                              scale = 0.07,
                                              text_align = TextNode.ACenter,
                                              text_fg = (1, 1, 1, 1),
                                              parent = self.errorDialogue,
                                              pos = (0, 0, 0.1),
                                              relief = None)

        self.errorDoneBtn = DirectButton(text = "Close", command = self.hideErrorDialogue,
                                                scale = 0.05,
                                                text_align = TextNode.ACenter,
                                                pos = (0, 0, -0.35),
                                                parent = self.errorDialogue,
                                                text_bg = (0.1, 0.8, 0.2, 1))

    def buildMainGUI(self):
        """Construct the GUI.

        This may be overridden for large-scale
        changes to the user-interface of a
        KeyMapper subclass."""

        self.buildListGUI()
        self.buildProfileGUI()

    def buildProfileGUI(self):
        """Construct the GUI used to select mapping profiles

        This may be overridden to change how that is handled."""

        frameBounds = self.list["frameSize"]

        self.profileMenu = DirectOptionMenu(
            parent = self.guiRoot,
            scale = self.buttonSize,
            pos = (0, 0, frameBounds[2] - self.buttonSize*2.0),
            relief = DGG.RAISED,
            frameSize = (-5, 5, -0.7, 1),
            text_align = TextNode.ACenter,
            command = self.loadProfile,
            items = list(self.profileDict.keys()))
        self.profileMenu["text"] = "Load profile..."
        self.profileMenu["textMayChange"] = 0

        self.profileAddBtn = DirectButton(text = "Add new",
                                   command = self.addNewProfile,
                                   scale = self.buttonSize,
                                   text_align = TextNode.ACenter,
                                   pos = (0.45, 0, frameBounds[2] - self.buttonSize*2.0),
                                   frameSize = (-3, 3, -0.7, 1),
                                   parent = self.guiRoot)

    def fillProfileList(self):
        """
        Set the contents of the profile-list, based on the profiles
        previously detected.

        If "buildProfileGUI" has been overridden, and no longer uses
        a DirectOptionMenu (or sub-class thereof), overriding this
        may be called for.
        """

        self.profileMenu["items"] = list(self.profileDict.keys())

    def buildProfileSaveGUI(self):
        """Construct the GUI used to enter a name for a new profile

        This may be overridden to change how that is handled."""

        self.profileSaveDialogue = DirectDialog(frameSize = (-0.7, 0.7, -0.2, 0.4),
                                              frameColor = (0.2, 0.3, 0.7, 1),
                                              fadeScreen = 0.4,
                                              image = None,
                                              geom = None,
                                              relief = DGG.FLAT)
        self.profileSaveDialogue["frameSize"] = (-0.8, 0.8, -0.1, 0.3)

        self.profileSaveTitle = DirectLabel(text = "Enter a name for this profile:",
                                              scale = 0.09,
                                              text_align = TextNode.ACenter,
                                              text_fg = (1, 1, 1, 1),
                                              parent = self.profileSaveDialogue,
                                              pos = (0, 0, 0.175),
                                              relief = None)

        self.profileSaveEntry = DirectEntry(parent = self.profileSaveDialogue,
                                            pos = (0, 0, 0),
                                            text_align = TextNode.ACenter,
                                            width = 20,
                                            command = self.saveNewProfile,
                                            scale = 0.07)

    def buildBindingGUI(self):
        """Build the interface that asks for a new key-binding.

        This may be overridden to change said interface.

        NB! If you override this, check whether you want to override
        the method 'setBindingDescription'!"""

        self.bindingDialogue = DirectDialog(frameSize = (-0.7, 0.7, -0.2, 0.4),
                                              frameColor = (0.2, 0.3, 0.7, 1),
                                              fadeScreen = 0.4,
                                              image = None,
                                              geom = None,
                                              relief = DGG.FLAT)
        self.bindingDialogue["frameSize"] = (-0.7, 0.7, -0.2, 0.4)

        self.bindingTitle = DirectLabel(text = "Press a key to bind to:",
                                              scale = 0.09,
                                              text_align = TextNode.ACenter,
                                              text_fg = (1, 1, 1, 1),
                                              parent = self.bindingDialogue,
                                              pos = (0, 0, 0.225),
                                              relief = None)
        self.bindingDescriptionKey = DirectLabel(text = "Unused",
                                              scale = 0.07,
                                              text_align = TextNode.ACenter,
                                              text_fg = (1, 1, 1, 1),
                                              parent = self.bindingDialogue,
                                              pos = (0, 0, 0.055),
                                              relief = None)
        self.bindingDescriptionCurrent = DirectLabel(text = "Unused",
                                              scale = 0.05,
                                              text_align = TextNode.ACenter,
                                              text_fg = (1, 1, 1, 1),
                                              parent = self.bindingDialogue,
                                              pos = (0, 0, -0.075),
                                              relief = None)

    def setBindingDescription(self, keyDescription, currentBinding, axisDirection):
        """Update the binding GUI to reflect the binding being handled.

        Params: keyDescription -- The key being bound.
                currentBiding -- The binding being used at the moment."""

        self.bindingDescriptionKey["text"] = keyDescription
        self.bindingDescriptionCurrent["text"] = "(Currently: " + self.getBindingName(currentBinding, axisDirection) + ")"
        self.bindingDescriptionKey.setText()
        self.bindingDescriptionKey.resetFrameSize()
        self.bindingDescriptionCurrent.setText()
        self.bindingDescriptionCurrent.resetFrameSize()

    def buildConflictGUI(self):
        """Build the interface that informs the user of a binding conflict,
        and which asks how to proceed.

        This may be overridden to change said interface.

        NB! If you override this, check whether you want to override
        the method 'setConflictText'!"""

        self.conflictDialogue = DirectDialog(frameSize = (-0.9, 0.9, -0.25, 0.45),
                                              frameColor = (0.2, 0.4, 0.75, 1),
                                              fadeScreen = 0.4,
                                              image = None,
                                              geom = None,
                                              relief = DGG.FLAT)
        self.conflictDialogue["frameSize"] = (-0.9, 0.9, -0.25, 0.45)

        self.conflictTitle = DirectLabel(text = "Warning!",
                                              scale = 0.1,
                                              text_align = TextNode.ACenter,
                                              text_fg = (1, 1, 1, 1),
                                              parent = self.conflictDialogue,
                                              pos = (0, 0, 0.3),
                                              relief = None)
        self.conflictLabel = DirectLabel(text = "Unused",
                                              scale = 0.05,
                                              text_align = TextNode.ACenter,
                                              text_fg = (1, 1, 1, 1),
                                              parent = self.conflictDialogue,
                                              pos = (0, 0, 0.15),
                                              relief = None)

        self.conflictContinueBtn = DirectButton(text = "Continue", command = self.conflictResolutionContinue,
                                                scale = 0.05,
                                                text_align = TextNode.ACenter,
                                                pos = (0.25, 0, -0.2),
                                                parent = self.conflictDialogue,
                                                text_bg = (0.1, 0.8, 0.2, 1))

        self.conflictCancelBtn = DirectButton(text = "Cancel", command = self.conflictResolutionCancel,
                                                scale = 0.05,
                                                text_align = TextNode.ACenter,
                                                pos = (-0.25, 0, -0.2),
                                                parent = self.conflictDialogue,
                                                text_bg = (0.1, 0.8, 0.2, 1))

    def setConflictText(self, lastKeyInterception, conflictingKey):
        """Update the conflict GUI to reflect the conflict being handled.

        Params: lastKeyInterception -- The attempted binding that resulted in a conflict
                conflictingKey -- The control to which that binding is already bound."""

        self.conflictLabel["text"] = "The key \"" + lastKeyInterception + "\" is already bound to \"" + \
                                     conflictingKey + "\"\n\n" + "Would you like to continue anyway\n(rendering \"" + \
                                     conflictingKey + "\" unbound), or \ncancel and choose a new key?"

    def buildListGUI(self):
        """Build the main representation of the current bindings.

        This may be overridden to change how a subclass of KeyMapper
        displays its key-bindings"""

        self.buildList()

        index = 0
        for keyDescription in self.keyOrder:
            bindingEntry = self.keyBindings[keyDescription]

            direction = 0
            if bindingEntry.binding is not None:
                if bindingEntry.binding.lower().startswith("axis."):
                    for axisData in self.axesInUse:
                        if axisData.keyDescriptionPositive == keyDescription:
                            direction = 1
                        elif axisData.keyDescriptionNegative == keyDescription:
                            direction = -1

            btnWrapper = self.buildButton(keyDescription, bindingEntry, direction, self.getNewBinding, [keyDescription])

            z = -(index)*self.buttonSpacing - self.firstButtonTopPadding

            btnWrapper.reparentTo(self.list.getCanvas())
            btnWrapper.setZ(z)

            self.buttonList.append([keyDescription, btnWrapper, z, self.getNewBinding])

            index += 1

    def buildButton(self, keyDescription, bindingEntry, axisDirection, btnCommand, btnExtraArgs = None):
        """Construct a button that displays a key-binding and
        allows the user to change that binding.

        Params: keyDescription -- The key to be bound
                bindingEntry -- The key's entry in self.keyBindings
                axisDirection -- If this is an axis, is it positive or negative?
                                 A value of 0 indicates no direction, or a non-axis.
                btnCommand -- The command executed when the button is pressed
                btnExtraArgs -- Any additional arguments to be sent to the above command

        This may be overridden to change how a KeyMapper subclass
        presents these elements."""

        btn = DirectButton(text = keyDescription, command = btnCommand,
                           scale = self.buttonSize,
                           frameSize = (0.5, 20, -0.7, 1),
                           text_align = TextNode.ALeft,
                           text_pos = (1, 0, 0),
                           extraArgs = btnExtraArgs)

        label = DirectLabel(text = self.getBindingName(bindingEntry.binding, axisDirection), parent = btn,
                            scale = 1,
                            text_align = TextNode.ARight,
                            relief = None,
                            pos = (17, 0, 0))

        btnWrapper = BasicKeyBindingButtonWrapper(btn, label)

        return btnWrapper

    def buildList(self):
        """Construct the list-box in which the binding buttons
        are presented.

        This may be overridden by a KeyMapper subclass
        to change how this element is presented."""

        height = self.buttonSpacing*(self.listLength) + self.firstButtonTopPadding*2.1

        self.list = DirectScrolledFrame(pos = (0, 0, 0),
                                        color = (0.2, 0.2, 0.2, 1),
                                        text_bg = (1, 1, 1, 1),
                                        relief = DGG.SUNKEN,
                                        frameSize = (-0.7, 0.7, -height*0.5, height*0.5),
                                        parent = self.guiRoot)
        self.list["canvasSize"] = (0, 0.5, -(len(self.keyBindings)-1)*self.buttonSpacing - self.firstButtonTopPadding*2.1 + 0.02, 0)

    def showErrorDialogue(self, e):
        """Show a dialogue for a given error

        Params: e -- The error in question"""

        self.errorDialogue.show()
        self.errorLabel["text"] = str(e)

    def showBindingDialogue(self, keyDescription):
        """Display the dialogue that prompts the user for a new
        key-binding.

        Params: keyDecription -- The key to be bound"""

        self.lastKeyInterception = None
        self.lastKeyInterceptionDeviceType = None
        self.lastKeyInterceptionValue = 0

        direction = self.getAxisDirectionForKey(keyDescription)

        self.setBindingDescription(keyDescription, self.keyBindings[keyDescription].binding, direction)
        self.bindingDialogue.show()
        self.bindingDialogueVisible = True

        self.deviceAxisTestValues = {}

        self.setEvents()

    def hideBindingDialogue(self):
        """Hide the binding dialogue."""

        self.bindingDialogue.hide()
        self.bindingDialogueVisible = False

        self.lastKeyInterception = None
        self.lastKeyInterceptionDeviceType = None
        self.lastKeyInterceptionValue = 0

        self.clearEvents()

    def hideProfileSaveDialogue(self):
        """Hide the profile-save dialogue"""

        self.profileSaveDialogue.hide()

    def hideErrorDialogue(self):
        """Hide the error dialogue"""

        self.errorDialogue.hide()

    """
    Tweaks and convenience-functions:
    """

    def setDeadZoneForAllAxes(self, deadZone):
        """Apply the same dead-zone value to all currently-used axes,
        and set the default dead-zone value to this new value.

        Params: deadZone -- The new value to apply"""

        for axisData in self.axesInUse:
            axisData.deadZone = deadZone
        self.deadZoneDefaultValue = deadZone

    def setDeadZoneForAxis(self, axisIndex, deadZone):
        """Apply a new dead-zone value to an axis

        Params: axisIndex -- The index of the axis-entry in the "axesInUse" list
                deadZone -- The new value to apply"""

        self.axesInUse[axisIndex].deadZone = deadZone

    def findAxisAndSetDeadZone(self, axisName, deviceType, deadZone):
        """Apply a new dead-zone value to an axis

        Params: axisName -- The description of the axis in question, as
                            taken from Panda's "InputDevice.Axis" enum and converted to a string
                deviceType -- The type of device expected to be associated with the axis in question
                deadZone -- The new value to apply"""

        for axisData in self.axesInUse:
            if axisData.axis == axisName and \
                    (axisData.deviceTypeNegative == deviceType or axisData.deviceTypePositive == deviceType):
                axisData.deadZone = deadZone

    def keyIsHeld(self, keyID):
        """Convenience function. Determine whether a key is being held"""

        return abs(self.keys[keyID]) > 0.5

    """""
    INTERNAL METHODS:
    """""

    def connectController(self, controller):
        """A callback method that is called when a controller is connected

        Params: controller -- The device that was connected"""

        deviceTypeToAdd = controller.device_class
        deviceTypeToAddString = self.getDeviceTypeString(deviceTypeToAdd)
        for keyBinding in self.keyBindings.values():
            if keyBinding.deviceType == deviceTypeToAddString:
                self.addUsedDevice(deviceTypeToAdd)

        if self.bindingDialogueVisible:
            self.setupEventsForDevice(controller)

    def disconnectController(self, controller):
        """A callback method that is called when a controller is removed

        Params: controller -- The device that was removed"""

        if self.bindingDialogueVisible:
            self.clearEventsForDevice(controller)

        if controller in self.devicesInUse:
            self.removeUsedDevice(controller.device_class)

    def addUsedDevice(self, deviceTypeToAdd):
        """Called when a device is to be added to the list of devices in use

        Params: deviceTypeToAdd -- The type device that was connected"""

        if not isinstance(deviceTypeToAdd, InputDevice.DeviceClass):
            deviceTypeToAdd = eval("InputDevice.DeviceClass." + deviceTypeToAdd)

        devices = base.devices.getDevices(deviceTypeToAdd)
        for device in self.devicesInUse.keys():
            if device.device_class == deviceTypeToAdd:
                return device

        if len(devices) > 0:
            device = devices[0]
            thrower = ButtonThrower(device.name)
            dataNP = None
            for prospectiveDataNP, otherThrower in self.dataNPList:
                if prospectiveDataNP.node().device == device:
                    dataNP = prospectiveDataNP
            if dataNP is None:
                dataNP = base.dataRoot.attachNewNode(InputDeviceNode(device, device.name))
            dataNP.attachNewNode(thrower)
            self.devicesInUse[device] = (dataNP, thrower)

            deviceTypeString = self.getDeviceTypeString(deviceTypeToAdd)

            for axisData in self.axesInUse:
                if axisData.deviceTypePositive == deviceTypeString:
                    axisData.devicePositive = device
                if axisData.deviceTypeNegative == deviceTypeString:
                    axisData.deviceNegative = device

            return device
        return None

    def removeUsedDevice(self, deviceTypeToRemove):
        """Called when a device is to be removed from the list of devices in use

        Params: deviceTypeToRemove -- The type device that was connected"""

        if not isinstance(deviceTypeToRemove, InputDevice.DeviceClass):
            deviceTypeToRemove = eval("InputDevice.DeviceClass." + deviceTypeToRemove)

        if deviceTypeToRemove is InputDevice.DeviceClass.keyboard or \
            deviceTypeToRemove is InputDevice.DeviceClass.mouse:
            return

        deviceRemovalList = [(device, dataNP, thrower) for device, (dataNP, thrower) in self.devicesInUse.items() if device.device_class == deviceTypeToRemove]

        for device, dataNP, thrower in deviceRemovalList:
            for axisData in self.axesInUse:
                if axisData.devicePositive == device or axisData.devicePositive is device:
                    axisData.devicePositive = None
                if axisData.deviceNegative == device or axisData.deviceNegative is device:
                    axisData.deviceNegative = None

            del self.devicesInUse[device]

            self.dataNPList = [(otherDataNP, otherThrower) for (otherDataNP, otherThrower) in self.dataNPList if otherDataNP is not dataNP and otherDataNP != dataNP]
            dataNP.removeNode()

    def getDeviceTypeString(self, deviceTypeInput):
        """Get a string representing a given class of device

        Params: deviceTypeInput -- The device-type in question, either
                                   an "InputDevice.DeviceClass" or a string. """

        if isinstance(deviceTypeInput, InputDevice.DeviceClass):
            deviceTypeInputString = str(deviceTypeInput)
        else:
            deviceTypeInputString = deviceTypeInput

        parts = deviceTypeInputString.split(".")
        numParts = len(parts)
        if numParts == 0:
            return deviceTypeInputString
        elif numParts == 1:
            return deviceTypeInputString
        else:
            return parts[-1]

    def getAxisDirectionForKey(self, keyDescription):
        """Figure out which axis-direction, if any, is associated with
           a given control

        Params: keyDescription -- The control in question"""

        direction = 0

        if keyDescription is not None:
            if keyDescription in self.keyBindings:
                binding = self.keyBindings[keyDescription].binding
                if binding is not None:
                    if binding.lower().startswith("axis."):
                        for axisData in self.axesInUse:
                            if axisData.keyDescriptionPositive == keyDescription:
                                direction = 1
                            elif axisData.keyDescriptionNegative == keyDescription:
                                direction = -1

        return direction

    def loadKeyMapping(self):
        """Load a key-mapping from file."""

        bindingList = []
        try:
            if self.loadMappingCallback is not None:
                keySaveData, axisSaveData = self.loadMappingCallback(self.bindingFile)
            else:
                self.showErrorDialogue(IOError("No file-loading callback found!\n\nThe file\n" + str(self.bindingFile) + "\nwill thus not be loaded."))
                return

            for description, binding, deviceType, axisDirection in list(keySaveData):
                bindingData = self.keyBindings[description]
                bindingList.append((description, binding, bindingData.type, deviceType, bindingData.callback, axisDirection))
            
            self.axesInUse = []
            for axisStr, deadZone in list(axisSaveData):
                axisData = AxisData()
                axisData.axis = axisStr
                axisData.deadZone = deadZone
                self.axesInUse.append(axisData)
        except IOError as e:
            vfs = VirtualFileSystem.getGlobalPtr()
            if vfs.exists(self.bindingFile):
                self.showErrorDialogue(e)

        for keyDescription, binding, controlType, deviceType, callback, axisDirection in bindingList:
            self.bindKey(keyDescription, binding, controlType, callback,
                         deviceType, axisDirection)

    def saveKeyMapping(self):
        """Save a key-mapping to file."""
        
        keySaveData = []
        for keyDescription, keyBinding in list(self.keyBindings.items()):
            dataList = [keyDescription, keyBinding.binding, keyBinding.deviceType, keyBinding.axisDirection]
            keySaveData.append(dataList)

        axisSaveData = []
        for axisData in self.axesInUse:
            dataList = [
                axisData.axis, axisData.deadZone,
                        ]
            axisSaveData.append(dataList)

        if self.saveMappingCallback is not None:
            try:
                self.saveMappingCallback(keySaveData, axisSaveData, self.bindingFile)
            except IOError as e:
                self.showErrorDialogue(e)
        else:
            self.showErrorDialogue(IOError("No file-saving callback found!\n\nThe file\n" + str(self.bindingFile) + "\nwill thus not be saved."))

    def addNewProfile(self):
        """
        Begin the process of adding a new profile containing the current mapping
        """

        self.profileSaveDialogue.show()
        self.profileSaveEntry["focus"] = 1

        self.getAvailableProfiles()
        self.fillProfileList()

    def saveNewProfile(self, name):
        """
        With the user having (hopefully) entered a name for the new profile,
        save it. That done, re-build the profile-list.

        Params: name -- The file-name of the new profile (without directory or extension)
        """

        self.hideProfileSaveDialogue()

        fileName = Filename(self.userProfileDirectory + name + ".btn")
        self.profileSaveEntry.enterText("")

        self.bindingFile = fileName
        self.saveKeyMapping()
        self.bindingFile = self.bindingFileCustom

        self.getAvailableProfiles()
        self.fillProfileList()

    def getAvailableProfiles(self):
        """
        Detect which profiles are available
        """

        vfs = VirtualFileSystem.getGlobalPtr()
        profileFiles = vfs.scanDirectory(self.defaultProfileDirectory) + vfs.scanDirectory(self.userProfileDirectory)
        if profileFiles is not None:
            profileFiles = [f.getFilename() for f in profileFiles]
            profileFiles = [name for name in profileFiles if name.getExtension() == "btn" and name.getBasename() != self.bindingFile.getBasename()]

            for fileName in profileFiles:
                self.profileDict[fileName.getBasenameWoExtension()] = fileName

    def loadProfile(self, profileName):
        """ Load a previously-saved profile

        Params: profileName -- The name of the profile
        """

        self.bindingFile = self.profileDict[profileName]
        self.loadKeyMapping()
        self.bindingFile = self.bindingFileCustom

        # Update our buttons to reflect the new bindings
        for btnItem in self.buttonList:

            keyDescription = btnItem[0]
            bindingEntry = self.keyBindings[keyDescription]

            direction = self.getAxisDirectionForKey(keyDescription)

            btnItem[1].setBindingText(self.getBindingName(bindingEntry.binding, direction))

        self.saveKeyMapping()

    def bindKey(self, keyDescription, binding, type, callback, deviceType, axisDirection = 0):
        """Set a new key-binding.

        This is not intended to be called by the user, but is rather used
        internally by KeyMapper.

        Params: keyDescription -- The name of the key to be bound
                                  (such as 'move forward' or 'shoot').
                binding -- The new binding for the key.
                type -- The type of binding to be used, selected from:
                        KEYMAP_EVENT_RELEASED, KEYMAP_EVENT_PRESSED,
                        KEYMAP_EVENT_PRESSED_AND_RELEASED and KEYMAP_HELD_KEY.
                callback -- The callback--if any--to be used for binding types other than
                            KEYMAP_HELD_KEY.
                            In the case of KEYMAP_EVENT_PRESSED_AND_RELEASED, this may be
                            either:
                             * A single callback (in which case the same callback is
                               used for both events, with an additional event-type parameter
                               being provided to it (which should have a value of either
                               KEYMAP_EVENT_PRESSED or KEYMAP_EVENT_RELEASED, as appropriate)),
                            or
                              * A list or tuple holding two callbacks, in which case the first
                                should be called on key-down and the second on key-up.
                deviceType -- The type of device, as specified in InputDevice.DeviceClass,
                              e.g. InputDevice.DeviceClass.gamepad
                axisDirection -- If this binding is an axis, then this is whether the binding
                                 is for that axis' positive direction (with a value of 1) or
                                 its negative direction (with a value of -1). If it's not an axis,
                                 then this should have a value of 0.
                """

        self.clearKeyEvent(binding, axisDirection)
        self.clearKeyEvent(self.keyBindings[keyDescription].binding, self.keyBindings[keyDescription].axisDirection)
        if type == KEYMAP_HELD_KEY:
            if binding is not None:
                self.eventObject.accept(binding, self.keyPressed, [keyDescription, 1])
                self.eventObject.accept(binding+"-up", self.keyPressed, [keyDescription, 0])
        elif type == KEYMAP_EVENT_PRESSED:
            if callback is not None:
                if binding is not None:
                    self.eventObject.accept(binding, callback, [keyDescription])
            else:
                raise Exception("Callback missing in attempt to bind key using \"pressed\" event.")
        elif type == KEYMAP_EVENT_RELEASED:
            if callback is not None:
                if binding is not None:
                    self.eventObject.accept(binding+"-up", callback, [keyDescription])
            else:
                raise Exception("Callback missing in attempt to bind key using \"pressed\" event.")
        elif type == KEYMAP_EVENT_PRESSED_AND_RELEASED:
            if isinstance(callback, list) or isinstance(callback, tuple):
                if len(callback) < 2:
                    raise Exception("Callback missing in attempt to bind key using both \"pressed\"- and \"released\"- events. There should be 2; number given: "+str(len(callback)))
                elif callback[0] is None:
                    raise Exception("First callback missing in attempt to bind key using \"pressed\"- and \"released\"- events event.")
                elif callback[1] is None:
                    raise Exception("Second callback missing in attempt to bind key using \"pressed\"- and \"released\"- events event.")
                else:
                    if binding is not None:
                        self.eventObject.accept(binding, callback[0], [keyDescription])
                        self.eventObject.accept(binding+"-up", callback[1], [keyDescription])
            else:
                if callback is not None:
                    if binding is not None:
                        self.eventObject.accept(binding, callback, [keyDescription, KEYMAP_EVENT_PRESSED])
                        self.eventObject.accept(binding+"-up", callback, [keyDescription, KEYMAP_EVENT_RELEASED])
                else:
                    raise Exception("Callback missing in attempt to bind key using both \"pressed\"- and \"released\"- events.")
        self.keyBindings[keyDescription].binding = binding
        self.keyBindings[keyDescription].deviceType = deviceType
        self.keyBindings[keyDescription].axisDirection = axisDirection

        if binding is not None and deviceType is not None:
            device = self.addUsedDevice(deviceType)
            if binding.lower().startswith("axis."):
                axisStr = binding[5:]
                foundAxis = False
                for axisData in self.axesInUse:
                    if axisData.axis == axisStr:
                        foundAxis = True
                        if axisDirection > 0:
                            axisData.keyDescriptionPositive = keyDescription
                            axisData.devicePositive = device
                            axisData.deviceTypePositive = deviceType
                        elif axisDirection < 0:
                            axisData.keyDescriptionNegative = keyDescription
                            axisData.deviceNegative = device
                            axisData.deviceTypeNegative = deviceType
                if not foundAxis:
                    axisData = AxisData()
                    axisData.axis = axisStr
                    axisData.deadZone = self.deadZoneDefaultValue
                    if axisDirection > 0:
                        axisData.keyDescriptionPositive = keyDescription
                        axisData.devicePositive = device
                        axisData.deviceTypePositive = deviceType
                    elif axisDirection < 0:
                        axisData.keyDescriptionNegative = keyDescription
                        axisData.deviceNegative = device
                        axisData.deviceTypeNegative = deviceType
                    self.axesInUse.append(axisData)

    def clearKeyEvent(self, binding, direction = 0):
        """Removes a binding from any key that uses it."""

        if not isinstance(binding, str):
            return

        keysToChange = []

        bindingIsAxis = binding.lower().startswith("axis.")
        if bindingIsAxis:
            bindingStr =  binding[5:]
            for axisData in self.axesInUse:
                if axisData.axis == bindingStr:
                    if direction == -1:
                        if axisData.keyDescriptionNegative is not None:
                            keysToChange.append(axisData.keyDescriptionNegative)
                            axisData.keyDescriptionNegative = None
                            axisData.deviceTypeNegative = None
                            axisData.deviceNegative = None
                    elif direction == 1:
                        if axisData.keyDescriptionPositive is not None:
                            keysToChange.append(axisData.keyDescriptionPositive)
                            axisData.keyDescriptionPositive = None
                            axisData.deviceTypePositive = None
                            axisData.devicePositive = None
        else:
            for keyDescription, keyBinding in list(self.keyBindings.items()):
                if binding == keyBinding.binding:
                    keysToChange.append(keyDescription)
        deviceTypesToCheck = []
        for key in keysToChange:
            deviceType = self.keyBindings[key].deviceType
            self.keyBindings[key].binding = None
            self.keyBindings[key].deviceType = None
            deviceTypesToCheck.append(deviceType)
        boundDeviceList = [keyBinding.deviceType for keyBinding in self.keyBindings.values()]
        for deviceType in deviceTypesToCheck:
            if deviceType not in boundDeviceList:
                self.removeUsedDevice(deviceType)
        self.eventObject.ignore(binding)
        self.eventObject.ignore(binding+"-up")

        self.axesInUse = [axisData for axisData in self.axesInUse if axisData.keyDescriptionPositive is not None or axisData.keyDescriptionNegative is not None]

    def keyPressed(self, description, value):
        """The internal method used to manage keys that
        use the KEYMAP_HELD_KEY binding type"""

        if self.keyStateCallback is not None:
            self.keyStateCallback(description, value)

        self.keys[description] = value

    def cancelKeys(self):
        """Set all keys to be 'unpressed'"""
        for description in self.keys:
            self.keys[description] = 0

    def keyInterception(self, deviceType, key, keyValue = 0):
        """The event that handles arbitrary key-presses, used when binding keys."""

        if deviceType is None:
            if key.startswith("mouse"):
                deviceType = self.getDeviceTypeString(InputDevice.DeviceClass.mouse)
            else:
                deviceType = self.getDeviceTypeString(InputDevice.DeviceClass.keyboard)

        if self.acceptKeyCombinations or not "-" in key:
            self.lastKeyInterceptionDeviceType = deviceType
            self.lastKeyInterception = key
            if keyValue > 0:
                keyValue = 1
            elif keyValue < 0:
                keyValue = -1
            self.lastKeyInterceptionValue = keyValue

    def keyRelease(self, key):
        """The event that handles arbitrary key-releases, used when binding keys."""

        if self.bindingDialogueVisible:
            #  NB: The "or" term, checking for the string "mouse" in the "key" parameter, and
            # the assignment of key to lastKeyInterception just below it, are included to get
            # around an issue in which mouse-down events seem to not be sent while the dialogue
            # is visible. Should this issue be dealt with they should probably be removed.
            if self.keyBeingBound is not None and (self.lastKeyInterception is not None or ("mouse" in key and (self.acceptKeyCombinations or not "-" in key))):
                if self.lastKeyInterception is None:
                    self.lastKeyInterception = key
                if self.lastKeyInterceptionDeviceType is None:
                    if self.lastKeyInterception.startswith("mouse"):
                        self.lastKeyInterceptionDeviceType = self.getDeviceTypeString(InputDevice.DeviceClass.mouse)
                    else:
                        self.lastKeyInterceptionDeviceType = self.getDeviceTypeString(InputDevice.DeviceClass.keyboard)
                conflict = None
                keyBeingBoundGroup = self.keyBindings[self.keyBeingBound].groupID
                for keyDescription, keyBinding in list(self.keyBindings.items()):
                    if keyBinding.binding == self.lastKeyInterception and keyDescription != self.keyBeingBound and \
                            keyBinding.groupID.hasBitsInCommon(keyBeingBoundGroup):
                        if keyBinding.binding.lower().startswith("axis."):
                            for axisData in self.axesInUse:
                                if axisData.keyDescriptionPositive == keyDescription:
                                    if self.lastKeyInterceptionValue > 0:
                                        conflict = keyDescription
                                if axisData.keyDescriptionNegative == keyDescription:
                                    if self.lastKeyInterceptionValue < 0:
                                        conflict = keyDescription
                        else:
                            conflict = keyDescription

                if conflict is not None:
                    self.handleBindingConflict(key, conflict)
                else:
                    self.finishKeyRelease(key)

    def handleBindingConflict(self, keyToBeBound, conflictingKey):
        """In the event that the user asks to bind a key using a button
        that has already been assigned elswhere, ask what should be done."""

        self.bindingDialogue.hide()
        self.clearEvents()

        self.currentConflict = conflictingKey
        self.conflictContinueBtn["extraArgs"] = [keyToBeBound]
        self.setConflictText(self.lastKeyInterception, conflictingKey)
        self.conflictDialogue.show()

    def conflictResolutionCancel(self):
        """An event indicating that the user has elected to
        not over-write the prior key-binding in the case of a conflict."""

        self.lastKeyInterception = None
        self.currentConflict = None
        self.conflictDialogue.hide()

        self.setEvents()
        self.bindingDialogue.show()

    def conflictResolutionContinue(self, key):
        """An event indicating that the user has elected,
        in the case of a conflict, to clear the prior
        key-binding and bind that button to the previously-
        indicated key."""

        self.conflictDialogue.hide()
        self.finishKeyRelease(key)
        self.currentConflict = None

    def finishKeyRelease(self, key):
        """Complete the process of binding a key, updating
        the internal binding map and the list-buttons
        and saving the new mapping to file."""

        self.bindKey(self.keyBeingBound, self.lastKeyInterception,
                             self.keyBindings[self.keyBeingBound].type,
                             self.keyBindings[self.keyBeingBound].callback,
                             self.lastKeyInterceptionDeviceType, self.lastKeyInterceptionValue)

        for btnItem in self.buttonList:
            if btnItem[0] == self.keyBeingBound or btnItem[0] == self.currentConflict:

                keyDescription = btnItem[0]
                bindingEntry = self.keyBindings[keyDescription]

                direction = self.getAxisDirectionForKey(keyDescription)

                btnItem[1].setBindingText(self.getBindingName(bindingEntry.binding, direction))

        self.keyBeingBound = None
        self.hideBindingDialogue()

        self.bindingFile = self.bindingFileCustom
        self.saveKeyMapping()

        self.deviceAxisTestValues = {}

    def getNewBinding(self, keyDescription):
        """Request a new binding from the user."""

        self.keyBeingBound = keyDescription
        self.showBindingDialogue(keyDescription)
    
    def setEvents(self):
        """An internal method used to activate KeyMapper's
        listening for arbitrary button events."""
        
        self.buttonThrower.setButtonDownEvent("keyInterception")
        self.buttonThrower.setButtonUpEvent("keyRelease")

        for deviceType in InputDevice.DeviceClass:
            if deviceType is not InputDevice.DeviceClass.keyboard and \
                deviceType is not InputDevice.DeviceClass.mouse:
                thrower = ButtonThrower(str(deviceType))
                deviceTypeString = self.getDeviceTypeString(deviceType)
                thrower.setTag(DEVICE_TYPE_TAG, deviceTypeString)
                thrower.setButtonDownEvent("keyInterception_"+deviceTypeString)
                thrower.setButtonUpEvent("keyRelease")
                self.deviceButtonThrowers[deviceTypeString] = thrower

        devicesAttachedForBinding = base.devices.getDevices()
        for device in devicesAttachedForBinding:
            self.setupEventsForDevice(device)

    def setupEventsForDevice(self, device):
        """An internal method that sets up a ButtonThrower and InputDeviceNode for
           taking bindings from a device

        Params: device -- The device for which to set up events"""

        if device.device_class != InputDevice.DeviceClass.keyboard and \
                        device.device_class != InputDevice.DeviceClass.mouse:
            if device in self.devicesInUse:
                dataNP = self.devicesInUse[device][0]
            else:
                dataNP = base.dataRoot.attachNewNode(InputDeviceNode(device, device.name))

            deviceTypeString = self.getDeviceTypeString(device.device_class)
            thrower = self.deviceButtonThrowers[deviceTypeString]

            dataNP.node().addChild(thrower)
            self.dataNPList.append((dataNP, thrower))

            self.deviceAxisTestValues[device] = {}
            for axis in device.axes:
                self.deviceAxisTestValues[device][axis.axis] = axis.value

    def clearEvents(self):
        """An internal method used to disable KeyMapper's
        listening for arbitrary button events."""
        
        self.buttonThrower.setButtonDownEvent("")
        self.buttonThrower.setButtonUpEvent("")

        for dataNP, thrower in self.dataNPList:
            thrower.clearTag(DEVICE_TYPE_TAG)
            thrower.setButtonDownEvent("")
            thrower.setButtonUpEvent("")
            self.clearBindingDataNPAndThrower(dataNP, thrower)
        self.dataNPList = []
        self.deviceButtonThrowers = {}

    def clearBindingDataNPAndThrower(self, dataNP, thrower):
        """An internal method that clears an InputDeviceNode and ButtonThrower,
           as appropriate

           Params: dataNP -- The InputDeviceNode
                   thrower -- The ButtonThrower"""

        if not dataNP.node().device in self.devicesInUse:
            dataNP.removeNode()
        else:
            dataNP.node().removeChild(thrower)

    def clearEventsForDevice(self, device):
        """An internal method that clears an InputDeviceNode and ButtonThrower,
           as appropriate

           Params: dataNP -- The InputDeviceNode
                   thrower -- The ButtonThrower"""

        tupleList = []
        for dataNP, thrower in self.dataNPList:
            if dataNP.node().device == device:
                self.clearBindingDataNPAndThrower(dataNP, thrower)
                tupleList.append((dataNP, thrower))

        for pair in tupleList:
            self.dataNPList.remove(pair)

    def isShowingDialogue(self):
        """Check whether a dialogue is being shown"""

        return (self.bindingDialogueVisible or not self.conflictDialogue.isHidden())

    def update(self, task):
        """An internal method that polls the relevant device-axes for input,
           and applies that input as appropriate

           Params: task -- A Panda-provided Task object"""

        if self.bindingDialogueVisible:
            for dataNP, thrower in self.dataNPList:
                device = dataNP.node().device
                for axis in device.axes:
                    value = axis.value
                    axisID = axis.axis
                    if axisID != InputDevice.Axis.none:
                        axisIsPresent = axisID in self.deviceAxisTestValues[device]
                        if (not axisIsPresent and abs(value) > 0.5) or \
                                (axisIsPresent and abs(value - self.deviceAxisTestValues[device][axisID]) > 0.3):
                            axisStr = str(axisID)
                            self.keyInterception(self.getDeviceTypeString(device.device_class), axisStr, value)
                            self.keyRelease(axisStr)
                            return Task.cont
        else:
            for axisData in self.axesInUse:
                axisStr = axisData.axis
                devicePositive = axisData.devicePositive
                deviceNegative = axisData.deviceNegative
                if devicePositive is not None:
                    valuePositive = max(0, devicePositive.findAxis(InputDevice.Axis[axisStr]).value)
                else:
                    valuePositive = 0

                if deviceNegative is not None:
                    valueNegative = min(0, deviceNegative.findAxis(InputDevice.Axis[axisStr]).value)
                else:
                    valueNegative = 0

                self.handleAxis(axisData.keyDescriptionPositive,
                                valuePositive, axisData.deadZone)
                self.handleAxis(axisData.keyDescriptionNegative,
                                valueNegative, axisData.deadZone)

        return Task.cont

    def handleAxis(self, keyDescription, value, deadZoneVal):
        """An internal method that interprets the data given by an axis
           and applies it as appropriate, whether setting a key-value
           or running a callback.

           Params: keyDescription -- The axis-control in question
                   value -- The value reported for that axis
                   deadZoneVal -- The threshold below which values are
                                  considered to be invalid"""

        if keyDescription is None:
            return
        absValue = abs(value)
        oldKeyState = abs(self.keys[keyDescription])
        keyBinding = self.keyBindings[keyDescription]
        binaryValue = False
        if keyBinding.type != KEYMAP_HELD_KEY:
            binaryValue = True

        if binaryValue:
            if oldKeyState < 0.5 and absValue > 0.5:
                if self.negativeValuesForNegativeAxes:
                    if value > 0:
                        result = 1
                    else:
                        result = -1
                else:
                    result = 1
                self.keys[keyDescription] = result

                if keyBinding.type == KEYMAP_EVENT_PRESSED:
                    keyBinding.callback(keyDescription)
                elif keyBinding.type == KEYMAP_EVENT_PRESSED_AND_RELEASED:
                    if isinstance(keyBinding.callback, list) or isinstance(keyBinding.callback, tuple):
                        keyBinding.callback[0](keyDescription)
                    else:
                        keyBinding.callback(keyDescription, KEYMAP_EVENT_PRESSED)

            elif oldKeyState > 0.5 and absValue < 0.5:
                result = 0
                self.keys[keyDescription] = result

                if keyBinding.type == KEYMAP_EVENT_RELEASED:
                    keyBinding.callback(keyDescription)
                elif keyBinding.type == KEYMAP_EVENT_PRESSED_AND_RELEASED:
                    if isinstance(keyBinding.callback, list) or isinstance(keyBinding.callback, tuple):
                        keyBinding.callback[1](keyDescription)
                    else:
                        keyBinding.callback(keyDescription, KEYMAP_EVENT_RELEASED)

        else:
            if absValue < deadZoneVal:
                self.keys[keyDescription] = 0
                if keyBinding.type == KEYMAP_HELD_KEY and self.keyStateCallback is not None and oldKeyState != 0:
                    self.keyStateCallback(keyDescription, False)
            elif self.negativeValuesForNegativeAxes:
                self.keys[keyDescription] = value
                if keyBinding.type == KEYMAP_HELD_KEY and self.keyStateCallback is not None and oldKeyState == 0:
                    self.keyStateCallback(keyDescription, True)
            else:
                self.keys[keyDescription] = absValue
                if keyBinding.type == KEYMAP_HELD_KEY and self.keyStateCallback is not None and oldKeyState == 0:
                    self.keyStateCallback(keyDescription, True)

    """""
    DESTROYING AND CLEANING UP
    """""

    def cleanupUI(self):
        """An internal method that cleans up the UI-objects somewhat"""

        for btnItem in self.buttonList:
            btnItem[1].destroy()
        self.buttonList = []

        if not self.list.isEmpty():
            self.list.destroy()
            self.list.removeNode()
        self.list = None
    
    def destroy(self):
        """Clean up the KeyMapper"""

        if self.updateTask is not None:
            taskMgr.remove(self.updateTask)
            self.updateTask = None
        
        self.clearEvents()
        
        # Clean up our events:
        
        #  It may be unwise to alter the key dictionaries while iterating
        # through them, so we create a simple copy of the data and iterate
        # through that.
        copy = []
        for keyDescription, keyBinding in list(self.keyBindings.items()):
            copy.append(keyBinding.binding)
        
        for binding in copy:
            self.clearKeyEvent(binding)

        for eventString in self.keyInterceptionEvents:
            self.eventObject.ignore(eventString)
        
        self.keys = None
        self.keyBindings = None
        self.bindingFile = None
        self.eventObject = None
        self.buttonThrower = None
        
        self.cleanupUI()
    