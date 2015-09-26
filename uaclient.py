#! /usr/bin/env python3

import sys, os, pprint, time
from PySide.QtCore import *
from PySide.QtGui import *


from uaclient_ui import Ui_MainWindow


class UaClient(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # init widgets
        self.ui.treeView.setSelectionBehavior(QAbstractItemView.SelectRows)
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(['col1', 'col2', 'col3'])
        self.ui.treeView.setModel(model)
        self.ui.treeView.setUniformRowHeights(True)
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # populate data
        for i in range(3):
            parent1 = QStandardItem('Family {}. Some long status text for sp'.format(i))
            for j in range(3):
                child1 = QStandardItem('Child {}'.format(i*3+j))
                child2 = QStandardItem('row: {}, col: {}'.format(i, j+1))
                child3 = QStandardItem('row: {}, col: {}'.format(i, j+2))
                parent1.appendRow([child1, child2, child3])
            model.appendRow(parent1)
            # span container columns
            self.ui.treeView.setFirstColumnSpanned(i, self.ui.treeView.rootIndex(), True)
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # expand third container
        index = model.indexFromItem(parent1)
        self.ui.treeView.expand(index)
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # select last row
        selmod = self.ui.treeView.selectionModel()
        index2 = model.indexFromItem(child3)
        selmod.select(index2, QItemSelectionModel.Select|QItemSelectionModel.Rows)
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


if __name__ == "__main__":
    app = QApplication(sys.argv)
    client = UaClient()
    client.show()
    sys.exit(app.exec_())
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

