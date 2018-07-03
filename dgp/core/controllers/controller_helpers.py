# -*- coding: utf-8 -*-
from typing import Optional, Union

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QWidget, QMessageBox, QInputDialog

__all__ = ['confirm_action', 'get_input']


def confirm_action(title: str, message: str,
                   parent: Optional[Union[QWidget, QObject]]=None):  # pragma: no cover
    dlg = QMessageBox(QMessageBox.Question, title, message,
                      QMessageBox.Yes | QMessageBox.No, parent=parent)
    dlg.setDefaultButton(QMessageBox.No)
    dlg.exec_()
    return dlg.result() == QMessageBox.Yes


def get_input(title: str, label: str, text: str, parent: QWidget=None):  # pragma: no cover
    new_text, result = QInputDialog.getText(parent, title, label, text=text)
    if result:
        return new_text
    return False


