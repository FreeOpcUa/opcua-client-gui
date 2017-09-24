
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

    def get_attr_value(self, text):
        idxlist = self.client.attrs_ui.model.match(self.client.attrs_ui.model.index(0, 0), Qt.DisplayRole, text,  1, Qt.MatchExactly | Qt.MatchRecursive)
        idx = idxlist[0]
        idx = idx.sibling(idx.row(), 1)
        item = self.client.attrs_ui.model.itemFromIndex(idx)
        return item.data(Qt.UserRole).value

    def test_select_objects(self):
        objects = self.server.nodes.objects
        self.client.tree_ui.expand_to_node(objects)
        self.assertEqual(objects, self.client.tree_ui.get_current_node())
        self.assertGreater(self.client.attrs_ui.model.rowCount(), 6)
        self.assertGreater(self.client.refs_ui.model.rowCount(), 1)

        data = self.get_attr_value("NodeId")
        self.assertEqual(data, objects.nodeid)

    def test_select_server_node(self):
        server_node = self.server.nodes.server
        self.client.tree_ui.expand_to_node(server_node)
        self.assertEqual(server_node, self.client.tree_ui.get_current_node())
        self.assertGreater(self.client.attrs_ui.model.rowCount(), 6)
        self.assertGreater(self.client.refs_ui.model.rowCount(), 10)

        data = self.get_attr_value("NodeId")
        self.assertEqual(data, server_node.nodeid)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    unittest.main()


