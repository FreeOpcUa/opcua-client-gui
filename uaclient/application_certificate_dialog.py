from PyQt5.QtWidgets import QDialog, QFileDialog

from uaclient.applicationcertificate_ui import Ui_ApplicationCertificateDialog


class ApplicationCertificateDialog(QDialog):
    def __init__(self, parent):
        QDialog.__init__(self)
        self.ui = Ui_ApplicationCertificateDialog()
        self.ui.setupUi(self)

        self.uaclient = parent.uaclient
        self.parent = parent

        self.ui.certificateLabel.setText(self.uaclient.application_certificate_path)
        self.ui.privateKeyLabel.setText(self.uaclient.application_private_key_path)

        self.ui.certificateButton.clicked.connect(self.get_certificate)
        self.ui.privateKeyButton.clicked.connect(self.get_private_key)

    @property
    def certificate_path(self):
        text = self.ui.certificateLabel.text()
        if text == "None":
            return None
        return text

    @certificate_path.setter
    def certificate_path(self, value):
        self.ui.certificateLabel.setText(value)

    @property
    def private_key_path(self):
        text = self.ui.privateKeyLabel.text()
        if text == "None":
            return None
        return text

    @private_key_path.setter
    def private_key_path(self, value):
        self.ui.privateKeyLabel.setText(value)

    def get_certificate(self):
        path, ok = QFileDialog.getOpenFileName(self,
                                               "Select application certificate",
                                               self.uaclient.application_certificate_path,
                                               "Certificate (*.der)")
        if ok:
            self.ui.certificateLabel.setText(path)

    def get_private_key(self):
        path, ok = QFileDialog.getOpenFileName(self,
                                               "Select application private key",
                                               self.uaclient.application_private_key_path,
                                               "Private key (*.pem)")
        if ok:
            self.ui.privateKeyLabel.setText(path)
