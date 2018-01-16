# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'dgp/gui/ui\data_import_dialog.ui'
#
# Created by: PyQt5 UI code generator 5.9
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.setWindowModality(QtCore.Qt.ApplicationModal)
        Dialog.resize(418, 500)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Dialog.sizePolicy().hasHeightForWidth())
        Dialog.setSizePolicy(sizePolicy)
        Dialog.setMinimumSize(QtCore.QSize(300, 500))
        Dialog.setMaximumSize(QtCore.QSize(600, 1200))
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/images/assets/geoid_icon.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        Dialog.setWindowIcon(icon)
        self.gridLayout = QtWidgets.QGridLayout(Dialog)
        self.gridLayout.setObjectName("gridLayout")
        self.group_datatype = QtWidgets.QGroupBox(Dialog)
        self.group_datatype.setObjectName("group_datatype")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.group_datatype)
        self.verticalLayout.setObjectName("verticalLayout")
        self.type_gravity = QtWidgets.QRadioButton(self.group_datatype)
        self.type_gravity.setChecked(True)
        self.type_gravity.setObjectName("type_gravity")
        self.group_radiotype = QtWidgets.QButtonGroup(Dialog)
        self.group_radiotype.setObjectName("group_radiotype")
        self.group_radiotype.addButton(self.type_gravity)
        self.verticalLayout.addWidget(self.type_gravity)
        self.type_gps = QtWidgets.QRadioButton(self.group_datatype)
        self.type_gps.setObjectName("type_gps")
        self.group_radiotype.addButton(self.type_gps)
        self.verticalLayout.addWidget(self.type_gps)
        self.gridLayout.addWidget(self.group_datatype, 5, 0, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 8, 0, 1, 3)
        self.combo_flights = QtWidgets.QComboBox(Dialog)
        self.combo_flights.setObjectName("combo_flights")
        self.gridLayout.addWidget(self.combo_flights, 3, 0, 1, 1)
        self.combo_meters = QtWidgets.QComboBox(Dialog)
        self.combo_meters.setObjectName("combo_meters")
        self.gridLayout.addWidget(self.combo_meters, 4, 0, 1, 1)
        self.field_path = QtWidgets.QLineEdit(Dialog)
        self.field_path.setReadOnly(True)
        self.field_path.setObjectName("field_path")
        self.gridLayout.addWidget(self.field_path, 1, 0, 1, 1)
        self.tree_directory = QtWidgets.QTreeView(Dialog)
        self.tree_directory.setObjectName("tree_directory")
        self.gridLayout.addWidget(self.tree_directory, 7, 0, 1, 3)
        self.button_browse = QtWidgets.QPushButton(Dialog)
        self.button_browse.setObjectName("button_browse")
        self.gridLayout.addWidget(self.button_browse, 1, 2, 1, 1)
        self.label_3 = QtWidgets.QLabel(Dialog)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 3, 2, 1, 1)
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 4, 2, 1, 1)

        self.retranslateUi(Dialog)
        self.buttonBox.rejected.connect(Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Import Data"))
        self.group_datatype.setTitle(_translate("Dialog", "Data Type"))
        self.type_gravity.setText(_translate("Dialog", "&Gravity Data"))
        self.type_gps.setText(_translate("Dialog", "G&PS Data"))
        self.button_browse.setText(_translate("Dialog", "&Browse"))
        self.label_3.setText(_translate("Dialog", "<html><head/><body><p align=\"center\"><span style=\" font-size:12pt;\">Flight</span></p></body></html>"))
        self.label.setText(_translate("Dialog", "<html><head/><body><p align=\"center\"><span style=\" font-size:12pt;\">Meter</span></p></body></html>"))

