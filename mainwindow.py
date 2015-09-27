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
        #self.model = QtGui.QStandardItemModel()
        self.model = MyModel(self)
        self.model.setHorizontalHeaderLabels(['Name', 'NodeId', 'NodeClass'])
        self.ui.treeView.setModel(self.model)
        self.ui.treeView.setUniformRowHeights(True)
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # populate data

        #for i in range(3):
            #parent1 =             for j in range(3):
                #child1 = QtGui.QStandardItem('Child {}'.format(i*3+j))
                #child2 = QtGui.QStandardItem('row: {}, col: {}'.format(i, j+1))
                #child3 = QtGui.QStandardItem('row: {}, col: {}'.format(i, j+2))
                #parent1.appendRow([child1, child2, child3])
            #model.appendRow(parent1)
            # span container columns
            #self.ui.treeView.setFirstColumnSpanned(i, , True)
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # expand third container
        #index = model.indexFromItem(parent1)
        #self.ui.treeView.expand(index)
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # select last row
        #selmod = self.ui.treeView.selectionModel()
        #index2 = model.indexFromItem(child3)
        #selmod.select(index2, QtGui.QItemSelectionModel.Select|QtGui.QItemSelectionModel.Rows)
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        self.uaclient = UaClient() 
        self.ui.connectButton.clicked.connect(self._connect)
        self.ui.disconnectButton.clicked.connect(self._disconnect)
        self.ui.treeView.expanded.connect(self._expanded)


    def _expanded(self, idx):
        print("expanded ", idx)

    def _connect(self):
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
        print("add item ", attrs, " to ", parent)
        data = [QtGui.QStandardItem(str(attr)) for attr in attrs[1:]]
        data[0].setData(attrs[0])
        if parent:
            return parent.appendRow(data)
        else:
            print("adding: ", data)
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
        print("Fetch more", idx)

        parent = self.itemFromIndex(idx)
        print(parent)
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

