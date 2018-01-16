# coding: utf-8

import sys

from PyQt5.uic import compileUiDir

"""Simple Qt build utility to compile all .ui files into Python modules."""


if __name__ == '__main__':
    compileUiDir(sys.argv[1], indent=4, from_imports=True, import_from='dgp')
