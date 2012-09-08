#!/usr/bin/python3
from isan.common.command_line import *
from isan.common.perceptrons import Base_Model as Model
#from isan.common.searcher import DFA as Searcher
from isan.tagging.cws import CWSSearcher as Searcher
from isan.tagging.default_segger import Segger as Segger


if __name__=="__main__":
    command_line('分词',Model,Segger,Searcher)
