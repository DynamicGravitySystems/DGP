# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'dgp/gui/ui\channel_select_dialog.ui'
#
# Created by: PyQt5 UI code generator 5.9
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_ChannelSelection(object):
    def setupUi(self, ChannelSelection):
        ChannelSelection.setObjectName("ChannelSelection")
        ChannelSelection.resize(304, 300)
        self.verticalLayout = QtWidgets.QVBoxLayout(ChannelSelection)
        self.verticalLayout.setObjectName("verticalLayout")
        self.channel_treeview = QtWidgets.QTreeView(ChannelSelection)
        self.channel_treeview.setDragEnabled(True)
        self.channel_treeview.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.channel_treeview.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.channel_treeview.setUniformRowHeights(True)
        self.channel_treeview.setObjectName("channel_treeview")
        self.channel_treeview.header().setVisible(False)
        self.verticalLayout.addWidget(self.channel_treeview)
        self.dialog_buttons = QtWidgets.QDialogButtonBox(ChannelSelection)
        self.dialog_buttons.setOrientation(QtCore.Qt.Horizontal)
        self.dialog_buttons.setStandardButtons(QtWidgets.QDialogButtonBox.Close|QtWidgets.QDialogButtonBox.Reset)
        self.dialog_buttons.setObjectName("dialog_buttons")
        self.verticalLayout.addWidget(self.dialog_buttons)

        self.retranslateUi(ChannelSelection)
        self.dialog_buttons.accepted.connect(ChannelSelection.accept)
        self.dialog_buttons.rejected.connect(ChannelSelection.reject)
        QtCore.QMetaObject.connectSlotsByName(ChannelSelection)

    def retranslateUi(self, ChannelSelection):
        _translate = QtCore.QCoreApplication.translate
        ChannelSelection.setWindowTitle(_translate("ChannelSelection", "Select Data Channels"))

