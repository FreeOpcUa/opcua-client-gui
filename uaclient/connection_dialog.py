from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QDialog, QFileDialog

from uaclient.connection_ui import Ui_ConnectionDialog
from uawidgets.utils import trycatchslot

if TYPE_CHECKING:
    from uaclient.mainwindow import Window


class ConnectionDialog(QDialog):
    def __init__(self, parent: "Window", uri: str) -> None:
        QDialog.__init__(self)
        self.ui = Ui_ConnectionDialog()
        self.ui.setupUi(self)

        self.uaclient = parent.uaclient
        self.uri = uri
        self._parent = parent

        self.ui.modeComboBox.addItem("None")
        self.ui.modeComboBox.addItem("Sign")
        self.ui.modeComboBox.addItem("SignAndEncrypt")

        self.ui.policyComboBox.addItem("None")
        self.ui.policyComboBox.addItem("Basic128Rsa15")
        self.ui.policyComboBox.addItem("Basic256")

        self.ui.closeButton.clicked.connect(self.accept)
        self.ui.certificateButton.clicked.connect(self.get_certificate)
        self.ui.privateKeyButton.clicked.connect(self.get_private_key)
        self.ui.queryButton.clicked.connect(self.query)

    @trycatchslot
    def query(self) -> None:
        self.ui.modeComboBox.clear()
        self.ui.policyComboBox.clear()
        endpoints = self._parent.uaclient.get_endpoints(self.uri)
        modes: list[str] = []
        policies: list[str] = []
        for edp in endpoints:
            mode = edp.SecurityMode.name
            if mode not in modes:
                self.ui.modeComboBox.addItem(mode)
                modes.append(mode)
            policy = edp.SecurityPolicyUri.split("#")[1]
            if policy not in policies:
                self.ui.policyComboBox.addItem(policy)
                policies.append(policy)

    @property
    def security_mode(self) -> str | None:
        text = self.ui.modeComboBox.currentText()
        if text == "None":
            return None
        return text

    @security_mode.setter
    def security_mode(self, value: str | None) -> None:
        text = value or "None"
        if self.ui.modeComboBox.findText(text) == -1:
            self.ui.modeComboBox.addItem(text)
        self.ui.modeComboBox.setCurrentText(text)

    @property
    def security_policy(self) -> str | None:
        text = self.ui.policyComboBox.currentText()
        if text == "None":
            return None
        return text

    @security_policy.setter
    def security_policy(self, value: str | None) -> None:
        text = value or "None"
        if self.ui.policyComboBox.findText(text) == -1:
            self.ui.policyComboBox.addItem(text)
        self.ui.policyComboBox.setCurrentText(text)

    @property
    def certificate_path(self) -> str:
        return self.ui.certificateLabel.text()

    @certificate_path.setter
    def certificate_path(self, value: str | None) -> None:
        self.ui.certificateLabel.setText(value or "")

    @property
    def private_key_path(self) -> str:
        return self.ui.privateKeyLabel.text()

    @private_key_path.setter
    def private_key_path(self, value: str | None) -> None:
        self.ui.privateKeyLabel.setText(value or "")

    def get_certificate(self) -> None:
        path, ok = QFileDialog.getOpenFileName(self, "Select certificate", self.certificate_path, "Certificate (*.der)")
        if ok:
            self.ui.certificateLabel.setText(path)

    def get_private_key(self) -> None:
        path, ok = QFileDialog.getOpenFileName(self, "Select private key", self.private_key_path, "Private key (*.pem)")
        if ok:
            self.ui.privateKeyLabel.setText(path)
