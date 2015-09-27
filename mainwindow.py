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
        self.model = QtGui.QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['col1', 'col2', 'col3'])
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

    def _add_modelitem(self, attrs, idx=None):
        #parent = self.model.itemFromIndex(idx)
        print(attrs)
        data = [QtGui.QStandardItem(str(attr)) for attr in attrs]
        return self.model.appendRow(data)
        #return parent.insertRow(data)

    def _expanded(self, idx):
        print("expanded ", idx)

    def _connect(self):
        uri = self.ui.addrLineEdit.text()
        self.uaclient.connect(uri)
        self._add_modelitem(self.uaclient.get_root_attrs())

    def _disconnect(self):
        self.uaclient.disconnect()




if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    client = Window()
    client.show()
    sys.exit(app.exec_())
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

