##################################################################
##                                                              ##
## A pair of convenience functions to allow KeyMapper to be     ##
## used without frequent error-dialogues                        ##
##                                                              ##
##################################################################
##                                                              ##
## Original version written by                                  ##
## Ian Eborn (Thaumaturge) in 2019                              ##
##                                                              ##
##################################################################
##                                                              ##
## This code is free for both commercial and private use.       ##
## Please leave the above credits in any subsequent versions    ##
## This module and related files are offered as-is, without any ##
## warranty, with any and all defects or errors.                ##
##                                                              ##
##################################################################

from GameSaver.GameSaver import  GameSaver, SaveableWrapper

class SaveLoadDummy():
    firstCallback = True

    @staticmethod
    def saveKeyMapping(keySaveData, axisSaveData, bindingFilename):
        if SaveLoadDummy.firstCallback:
            SaveLoadDummy.firstCallback = False
            raise(IOError("Warning:\n\nUsing dummy save- and load- callbacks.\n\nBindings and profiles will not be saved or loaded!"))

    @staticmethod
    def loadKeyMapping(bindingFilename):
        raise(IOError("Warning:\n\nUsing dummy save- and load- callbacks.\n\nBindings and profiles will not be saved or loaded!"))