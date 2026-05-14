import sys
import time
import unittest
from typing import Any

from asyncua.sync import Server

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from uaclient.mainwindow import Window


class TestClient(unittest.TestCase):
    def setUp(self) -> None:
        self.server = Server()
        url = "opc.tcp://localhost:48400/freeopcua/server/"
        self.server.set_endpoint(url)
        self.server.start()
        self.client = Window()
        self.client.ui.addrComboBox.setCurrentText(url)
        self.client.connect()

    def tearDown(self) -> None:
        self.client.disconnect()
        self.server.stop()

    def get_attr_value(self, text: str) -> Any:
        idxlist = self.client.attrs_ui.model.match(
            self.client.attrs_ui.model.index(0, 0),
            Qt.ItemDataRole.DisplayRole, text, 1,
            Qt.MatchFlag.MatchExactly | Qt.MatchFlag.MatchRecursive)
        idx = idxlist[0]
        idx = idx.sibling(idx.row(), 1)
        item = self.client.attrs_ui.model.itemFromIndex(idx)
        assert item is not None
        return item.data(Qt.ItemDataRole.UserRole).value

    def test_select_objects(self) -> None:
        objects = self.server.nodes.objects
        self.client.tree_ui.expand_to_node(objects)
        self.assertEqual(objects, self.client.tree_ui.get_current_node())
        self.assertGreater(self.client.attrs_ui.model.rowCount(), 6)
        self.assertGreater(self.client.refs_ui.model.rowCount(), 1)

        data = self.get_attr_value("NodeId")
        self.assertEqual(data, objects.nodeid)

    def test_select_server_node(self) -> None:
        server_node = self.server.nodes.server
        self.client.tree_ui.expand_to_node(server_node)
        self.assertEqual(server_node, self.client.tree_ui.get_current_node())
        self.assertGreater(self.client.attrs_ui.model.rowCount(), 6)
        self.assertGreater(self.client.refs_ui.model.rowCount(), 10)

        data = self.get_attr_value("NodeId")
        self.assertEqual(data, server_node.nodeid)


class TestAutoReconnect(unittest.TestCase):
    def setUp(self) -> None:
        self.url = "opc.tcp://localhost:48401/freeopcua/server/"
        self.server = Server()
        self.server.set_endpoint(self.url)
        self.server.start()
        self.client = Window()
        self.client.ui.addrComboBox.setCurrentText(self.url)
        self.client.connect()

    def tearDown(self) -> None:
        self.client.disconnect()
        try:
            self.server.stop()
        except Exception:
            pass

    def _pump(self, seconds: float) -> None:
        app = QApplication.instance()
        assert app is not None
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            time.sleep(0.05)

    def test_widgets_grey_out_when_server_dies(self) -> None:
        self.assertTrue(self.client.ui.treeView.isEnabled())
        self.assertTrue(self.client.ui.disconnectButton.isEnabled())
        self.assertFalse(self.client.ui.connectButton.isEnabled())

        self.server.stop()
        self._pump(5)

        self.assertFalse(self.client.ui.treeView.isEnabled())
        self.assertFalse(self.client.ui.attrView.isEnabled())
        self.assertFalse(self.client.ui.refView.isEnabled())
        # The user can still abort an in-progress reconnect.
        self.assertTrue(self.client.ui.disconnectButton.isEnabled())
        self.assertFalse(self.client.ui.connectButton.isEnabled())
        self.assertIn("auto-reconnect", self.client.ui.statusBar.currentMessage())

        # Re-bind the same port and verify the supervisor reconnects.
        self.server = Server()
        self.server.set_endpoint(self.url)
        self.server.start()
        self._pump(15)

        self.assertTrue(self.client.ui.treeView.isEnabled())
        self.assertTrue(self.client.ui.attrView.isEnabled())
        self.assertTrue(self.client.ui.refView.isEnabled())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    unittest.main()
