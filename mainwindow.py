#! /usr/bin/env python3

import sys 
sys.path.insert(0, "..") #FIXME remove

from PySide import QtCore
from PySide import QtGui 


from uaclient import UaClient
from mainwindow_ui import Ui_MainWindow

from IPython import embed


class Window(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # init widgets
        self.ui.addrLineEdit.setText("opc.tcp://localhost:4841/")
        self.ui.treeView.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.attr_model = QtGui.QStandardItemModel()
        self.model = MyModel(self)
        self.ui.attrView.setModel(self.attr_model)
        self.model.setHorizontalHeaderLabels(['Name', 'NodeId', 'NodeClass'])
        self.ui.treeView.setModel(self.model)
        self.ui.treeView.setUniformRowHeights(True)

        self.uaclient = UaClient() 
        self.ui.connectButton.clicked.connect(self._connect)
        self.ui.disconnectButton.clicked.connect(self._disconnect)
        self.ui.treeView.activated.connect(self._show_attrs_and_refs)
        self.ui.treeView.clicked.connect(self._show_attrs_and_refs)

    def _show_attrs_and_refs(self, idx):
        print("Activated", idx)
        it = self.model.itemFromIndex(idx)
        if not it:
            return
        node = it.data()
        if not node:
            print("No node for item:", it, it.text()) 
            return
        attrs = self.uaclient.get_all_node_attrs(node) 
        print("attrs : ", attrs)
        self.attr_model.clear()
        for k, v in attrs.items():
            self.attr_model.appendRow([QtGui.QStandardItem(k), QtGui.QStandardItem(str(v))])

    def _connect(self):
        self._disconnect()
        uri = self.ui.addrLineEdit.text()
        self.uaclient.connect(uri)
        self.model.client = self.uaclient
        self.model.add_item(self.uaclient.get_root_attrs())

    def _disconnect(self):
        self.uaclient.disconnect()
        self.model.clear()
        self.model.client = None

    def closeEvent(self, event):
        self._disconnect()
        event.accept()


class MyModel(QtGui.QStandardItemModel):
    def __init__(self, parent):
        super(MyModel, self).__init__(parent)
        self.client = None
        self._fetched = [] 

    def add_item(self, attrs, parent=None):
        data = [QtGui.QStandardItem(str(attr)) for attr in attrs[1:]]
        data[0].setData(attrs[0])
        if parent:
            return parent.appendRow(data)
        else:
            return self.appendRow(data)

    def canFetchMore(self, idx):
        item = self.itemFromIndex(idx)
        if not item:
            return True
        node = item.data()
        if node not in self._fetched:
            self._fetched.append(node)
            return True
        return False

    def hasChildren(self, idx):
        item = self.itemFromIndex(idx)
        if not item:
            return True
        node = item.data()
        if node in self._fetched:
            return QtGui.QStandardItemModel.hasChildren(self, idx)
        return True

    def fetchMore(self, idx):
        parent = self.itemFromIndex(idx)
        if not parent:
            print("No item for ids: ", idx)
        else:
            for attrs in self.client.get_children(parent.data()):
                self.add_item(attrs, parent)


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    client = Window()
    client.show()
    sys.exit(app.exec_())
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

