
import unittest
import sys
print("SYS:PATH", sys.path)
sys.path.insert(0, "python-opcua")
sys.path.insert(0, "opcua-widgets")
import os
print("PWD", os.getcwd())

from opcua import ua
from opcua import Server

from PyQt5.QtCore import QTimer, QSettings, QModelIndex, Qt, QCoreApplication
from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest

from uaclient.mainwindow import Window


class TestClient(unittest.TestCase):
    def setUp(self):
        self.server = Server()
        url = "opc.tcp://localhost:48400/freeopcua/server/"
        self.server.set_endpoint(url)
        self.server.start()
        self.client = Window()
        self.client.ui.addrComboBox.setCurrentText(url)
        self.client.connect()

    def tearDown(self):
        self.client.disconnect()
        self.server.stop()

    def test_select_objects(self):
        objects = self.server.nodes.objects
        self.client.tree_ui.set_current_node("Objects")
        self.assertEqual(objects, self.client.tree_ui.get_current_node())



if __name__ == "__main__":
    app = QApplication(sys.argv)
    unittest.main()


