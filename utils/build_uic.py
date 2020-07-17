# -*- coding: utf-8 -*-
from pathlib import Path

from PyQt5.uic import compileUiDir
from PyQt5.pyrcc_main import processResourceFile


"""
Utility script to build python compiled UI and resource files from Qt .ui and
.qrc files.

See Also
--------

`Qt 5 Resource System <http://doc.qt.io/qt-5/resources.html>`__

`Qt 5 Resource Compiler (RCC) <http://doc.qt.io/qt-5/rcc.html>`__

`PyQt5 Resource System <http://pyqt.sourceforge.net/Docs/PyQt5/resources.html>`__


"""
BASE_DIR = Path(Path(__file__).parent).joinpath('../dgp').absolute()
RES_FILES = [
    str(BASE_DIR.joinpath('gui/ui/resources/resources.qrc'))
]
RES_DEST = str(BASE_DIR.joinpath('resources_rc.py'))
UI_DIR = str(BASE_DIR.joinpath('gui/ui'))


def compile_ui(ui_directory, resource_files, resource_dest, base_module='dgp',
               resource_suffix='_rc') -> None:
    """Compile Qt .ui and .qrc files into .py files for direct import.

    Parameters
    ----------
    ui_directory : str
        String path to directory containing .ui files to compile
    resource_files : List of str
        List of string paths to Qt resource .qrc files to compile
    resource_dest : str
        Destination path/name for the compiled resource file
    base_module : str, optional
        Module name which .ui files will import the compiled resources_rc.py
        file from. Default is to import from the root 'dgp' module
    resource_suffix : str, optional
        Optional suffix used by ui files to load resources. Default is '_rc'

    Notes
    -----
    Compiled .ui files are output to the same directory as their source

    """
    processResourceFile(resource_files, resource_dest, None)
    compileUiDir(ui_directory, from_imports=True, import_from=base_module,
                 resource_suffix=resource_suffix)


if __name__ == '__main__':
    compile_ui(UI_DIR, RES_FILES, RES_DEST)
