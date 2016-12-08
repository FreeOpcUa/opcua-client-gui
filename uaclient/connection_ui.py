# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'uaclient/connection_ui.ui'
#
# Created by: PyQt5 UI code generator 5.7
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_ConnectionDialog(object):
    def setupUi(self, ConnectionDialog):
        ConnectionDialog.setObjectName("ConnectionDialog")
        ConnectionDialog.resize(400, 300)
        self.gridLayout = QtWidgets.QGridLayout(ConnectionDialog)
        self.gridLayout.setContentsMargins(11, 11, 11, 11)
        self.gridLayout.setSpacing(6)
        self.gridLayout.setObjectName("gridLayout")
        self.queryButton = QtWidgets.QPushButton(ConnectionDialog)
        self.queryButton.setObjectName("queryButton")
        self.gridLayout.addWidget(self.queryButton, 0, 0, 1, 2)
        self.label = QtWidgets.QLabel(ConnectionDialog)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 1, 0, 1, 1)
        self.policyComboBox = QtWidgets.QComboBox(ConnectionDialog)
        self.policyComboBox.setObjectName("policyComboBox")
        self.gridLayout.addWidget(self.policyComboBox, 1, 1, 1, 2)
        self.label_2 = QtWidgets.QLabel(ConnectionDialog)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 2, 0, 1, 1)
        self.modeComboBox = QtWidgets.QComboBox(ConnectionDialog)
        self.modeComboBox.setObjectName("modeComboBox")
        self.gridLayout.addWidget(self.modeComboBox, 2, 1, 1, 2)
        self.certificateLabel = QtWidgets.QLabel(ConnectionDialog)
        self.certificateLabel.setObjectName("certificateLabel")
        self.gridLayout.addWidget(self.certificateLabel, 3, 0, 1, 1)
        self.certificateButton = QtWidgets.QPushButton(ConnectionDialog)
        self.certificateButton.setObjectName("certificateButton")
        self.gridLayout.addWidget(self.certificateButton, 3, 1, 1, 2)
        self.privateKeyLabel = QtWidgets.QLabel(ConnectionDialog)
        self.privateKeyLabel.setObjectName("privateKeyLabel")
        self.gridLayout.addWidget(self.privateKeyLabel, 4, 0, 1, 1)
        self.privateKeyButton = QtWidgets.QPushButton(ConnectionDialog)
        self.privateKeyButton.setObjectName("privateKeyButton")
        self.gridLayout.addWidget(self.privateKeyButton, 4, 1, 1, 2)
        self.closeButton = QtWidgets.QPushButton(ConnectionDialog)
        self.closeButton.setObjectName("closeButton")
        self.gridLayout.addWidget(self.closeButton, 5, 2, 1, 1)

        self.retranslateUi(ConnectionDialog)
        QtCore.QMetaObject.connectSlotsByName(ConnectionDialog)

    def retranslateUi(self, ConnectionDialog):
        _translate = QtCore.QCoreApplication.translate
        ConnectionDialog.setWindowTitle(_translate("ConnectionDialog", "ConnectionDialog"))
        self.queryButton.setText(_translate("ConnectionDialog", "Query server capability"))
        self.label.setText(_translate("ConnectionDialog", "Security Policy"))
        self.label_2.setText(_translate("ConnectionDialog", "Message Security Mode"))
        self.certificateLabel.setText(_translate("ConnectionDialog", "None"))
        self.certificateButton.setText(_translate("ConnectionDialog", "Select certificate"))
        self.privateKeyLabel.setText(_translate("ConnectionDialog", "None"))
        self.privateKeyButton.setText(_translate("ConnectionDialog", "Select private key"))
        self.closeButton.setText(_translate("ConnectionDialog", "Close"))

