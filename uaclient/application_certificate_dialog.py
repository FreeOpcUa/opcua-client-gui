from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QDialog, QFileDialog

from uaclient.applicationcertificate_ui import Ui_ApplicationCertificateDialog

if TYPE_CHECKING:
    from uaclient.mainwindow import Window


class ApplicationCertificateDialog(QDialog):
    def __init__(self, parent: "Window") -> None:
        QDialog.__init__(self)
        self.ui = Ui_ApplicationCertificateDialog()
        self.ui.setupUi(self)

        self.uaclient = parent.uaclient
        self._parent = parent

        self.ui.certificateLabel.setText(self.uaclient.application_certificate_path or "")
        self.ui.privateKeyLabel.setText(self.uaclient.application_private_key_path or "")

        self.ui.certificateButton.clicked.connect(self.get_certificate)
        self.ui.privateKeyButton.clicked.connect(self.get_private_key)

    @property
    def certificate_path(self) -> str | None:
        text = self.ui.certificateLabel.text()
        if text == "None":
            return None
        return text

    @certificate_path.setter
    def certificate_path(self, value: str | None) -> None:
        self.ui.certificateLabel.setText(value or "")

    @property
    def private_key_path(self) -> str | None:
        text = self.ui.privateKeyLabel.text()
        if text == "None":
            return None
        return text

    @private_key_path.setter
    def private_key_path(self, value: str | None) -> None:
        self.ui.privateKeyLabel.setText(value or "")

    def get_certificate(self) -> None:
        path, ok = QFileDialog.getOpenFileName(
            self,
            "Select application certificate",
            self.uaclient.application_certificate_path or "",
            "Certificate (*.der)",
        )
        if ok:
            self.ui.certificateLabel.setText(path)

    def get_private_key(self) -> None:
        path, ok = QFileDialog.getOpenFileName(
            self,
            "Select application private key",
            self.uaclient.application_private_key_path or "",
            "Private key (*.pem)",
        )
        if ok:
            self.ui.privateKeyLabel.setText(path)
