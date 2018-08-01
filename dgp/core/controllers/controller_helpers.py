# -*- coding: utf-8 -*-
import shlex
import sys
from pathlib import Path
from typing import Optional, Union

from PyQt5.QtCore import QObject, QProcess
from PyQt5.QtWidgets import QWidget, QMessageBox, QInputDialog

__all__ = ['confirm_action', 'get_input', 'show_in_explorer']


def confirm_action(title: str, message: str,
                   parent: Optional[Union[QWidget, QObject]]=None):  # pragma: no cover
    """
    Prompt the user for a yes/no confirmation, useful when performing
    destructive actions e.g. deleting a project member.

    Parameters
    ----------
    title : str
    message : str
    parent : QWidget, optional
        The parent widget for this dialog, if not specified the dialog
        may not be destroyed when the main UI application quits.

    Returns
    -------
    bool
        True if user confirms the dialog (selects 'Yes')
        False if the user cancels or otherwise aborts the dialog

    """
    dlg = QMessageBox(QMessageBox.Question, title, message,
                      QMessageBox.Yes | QMessageBox.No, parent=parent)
    dlg.setDefaultButton(QMessageBox.No)
    dlg.exec_()
    return dlg.result() == QMessageBox.Yes


def get_input(title: str, label: str, text: str = "", parent: QWidget=None):  # pragma: no cover
    """
    Get text input from the user using a simple Qt Dialog Box

    Parameters
    ----------
    title : str
    label : str
    text : str, optional
        Existing string to display in the input dialog

    parent : QWidget, optional
        The parent widget for this dialog, if not specified the dialog
        may not be destroyed when the main UI application quits.

    Returns
    -------

    """
    new_text, result = QInputDialog.getText(parent, title, label, text=text)
    if result:
        return new_text
    return False


def show_in_explorer(path: Path):  # pragma: no cover
    """Reveal the specified path in the OS's explorer/file-browser/finder

    Parameters
    ----------
    path : :class:`pathlib.Path`

    ToDo: Linux file explorer handling
    """
    dest = path.absolute().resolve()
    if sys.platform == 'darwin':
        target = 'oascript'
        args = f'-e tell application "Finder" -e activate -e select POSIX file ' \
               f'"{dest!s}" -e end tell'
    elif sys.platform == 'win32':
        target = 'explorer'
        args = shlex.quote(f'{dest!s}')
    else:
        return

    QProcess.startDetached(target, shlex.split(args))

