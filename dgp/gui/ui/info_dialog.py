# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'dgp/gui/ui\info_dialog.ui'
#
# Created by: PyQt5 UI code generator 5.9
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_InfoDialog(object):
    def setupUi(self, InfoDialog):
        InfoDialog.setObjectName("InfoDialog")
        InfoDialog.resize(213, 331)
        self.verticalLayout = QtWidgets.QVBoxLayout(InfoDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.table_info = QtWidgets.QTableView(InfoDialog)
        self.table_info.setObjectName("table_info")
        self.verticalLayout.addWidget(self.table_info)
        self.buttonBox = QtWidgets.QDialogButtonBox(InfoDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(InfoDialog)
        self.buttonBox.accepted.connect(InfoDialog.accept)
        self.buttonBox.rejected.connect(InfoDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(InfoDialog)

    def retranslateUi(self, InfoDialog):
        _translate = QtCore.QCoreApplication.translate
        InfoDialog.setWindowTitle(_translate("InfoDialog", "Info"))

