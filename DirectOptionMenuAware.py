#######################################################################
##                                                                   ##
## DirectOptionMenuAware--A version of Panda3D's DirectOptionMenu    ##
## that implements some tweaks and changes.                          ##
##                                                                   ##
#######################################################################
##                                                                   ##
## Original version written by                                       ##
## Ian Eborn (Thaumaturge), copyright 2019                           ##
##                                                                   ##
#######################################################################
##                                                                   ##
## This code is licensed under the MIT license. See the              ##
## license file (LICENSE.md) for details.                            ##
## Link, if available:                                               ##
##  https://github.com/ArsThaumaturgis/KeyMapper/blob/master/LICENSE ##
##                                                                   ##
#######################################################################

from direct.gui.DirectGui import DirectOptionMenu
from panda3d.core import PGScrollFrame

class DirectOptionMenuAware(DirectOptionMenu):
    def __init__(self, parent = None, **kw):
        if "popupMarker_pos" in kw:
            self.popupMarkerPos = kw["popupMarker_pos"]
        else:
            self.popupMarkerPos = None

        optiondefs = (
            ('itemTextFont',       None,             None),
        )
        self.defineoptions(kw, optiondefs)
        DirectOptionMenu.__init__(self, parent)

        self.initialiseoptions(DirectOptionMenuAware)

    def showPopupMenu(self, event = None):
        DirectOptionMenu.showPopupMenu(self, event)

        parent = None
        np = self.getParent()
        while np is not None and np != render2d and not np.isEmpty() and parent is None:
            if isinstance(np.node(), PGScrollFrame):
                parent = np
            else:
                np = np.getParent()

        if parent is not None:
            parentBounds = [x for x in parent.node().getFrame()]
            parentPos = parent.getPos(render2d)
            parentScale = parent.getScale(render2d)

            bounds = [x for x in self.popupMenu.node().getFrame()]
            pos = self.popupMenu.getPos(render2d)
            scale = self.popupMenu.getScale(render2d)

            bottomZ = pos[2] + bounds[2]*scale[2]
            topZ = pos[2] + bounds[3]*scale[2]

            minZ = parentBounds[2]*parentScale[2] + parentPos[2]
            maxZ = parentBounds[3]*parentScale[2] + parentPos[2]

            if topZ > maxZ:
                self.popupMenu.setZ(render2d, pos[2] - topZ + maxZ)

    def set(self, index, fCommand = 1):
        textMayChange = self["textMayChange"]

        lastIndex = self.selectedIndex
        if lastIndex != -1 and lastIndex is not None:
            self.component("item%d" %lastIndex).setColorScale((1, 1, 1, 1))

        if not textMayChange:
            text = self["text"]

        DirectOptionMenu.set(self, index, fCommand)

        if not textMayChange:
            self["text"] = text

        newIndex = self.selectedIndex
        if newIndex != -1 and newIndex is not None:
            self.component("item%d" %newIndex).setColorScale((0.7, 0.7, 0.7, 1))

    def setItems(self):
        DirectOptionMenu.setItems(self)
        if self.popupMarkerPos:
            self.popupMarker.setPos(self.popupMarkerPos)

        if self["itemTextFont"] is not None:
            for i in range(len(self["items"])):
                btn = self.component('item%d' %i)
                btn["text_font"] = self["itemTextFont"]