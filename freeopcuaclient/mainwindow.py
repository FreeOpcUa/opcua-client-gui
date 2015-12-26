#! /usr/bin/env python3

import sys 

from PyQt5.QtCore import pyqtSignal, QTimer, Qt, QObject, QSettings
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt5.QtWidgets import QMainWindow, QWidget, QApplication, QAbstractItemView, QHeaderView


from freeopcuaclient.uaclient import UaClient
from freeopcuaclient.mainwindow_ui import Ui_MainWindow
from freeopcuaclient import resources
from opcua import ua



class SubHandler(QObject):
    """
    Subscription Handler. To receive events from server for a subscription
    """

    data_change_fired = pyqtSignal(object, str, str)

    def datachange_notification(self, node, val, data):
        self.data_change_fired.emit(node, str(val), data.monitored_item.Value.SourceTimestamp.isoformat())

    def event(self, handle, event):
        print("Event handling not implemented yet", handle, event)




class Window(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowIcon(QIcon(":/network.svg"))

        #fix stuff imposible to do in qtdesigner
        #remove dock titlebar for addressbar
        w = QWidget()
        self.ui.addrDockWidget.setTitleBarWidget(w)
        #tabify some docks
        self.tabifyDockWidget(self.ui.evDockWidget, self.ui.subDockWidget)
        self.tabifyDockWidget(self.ui.subDockWidget, self.ui.refDockWidget)

        # we only show statusbar in case of errors
        self.ui.statusBar.hide()  

        # load settings, seconds arg is default
        self.settings = QSettings("FreeOpcUa", "FreeOpcUaClient")
        self._address_list = self.settings.value("address_list", ["opc.tcp://localhost:4841", "opc.tcp://localhost:53530/OPCUA/SimulationServer/"])
        self._address_list_max_count = int(self.settings.value("address_list_max_count", 10)) 


        # init widgets
        for addr in self._address_list:
            self.ui.addrComboBox.insertItem(-1, addr)

        self.attr_model = QStandardItemModel()
        self.refs_model = QStandardItemModel()
        self.sub_model = QStandardItemModel()
        self.ui.attrView.setModel(self.attr_model)
        self.ui.attrView.header().setSectionResizeMode(1)
        self.ui.refView.setModel(self.refs_model)
        self.ui.refView.horizontalHeader().setSectionResizeMode(1)
        self.ui.subView.setModel(self.sub_model)
        self.ui.subView.horizontalHeader().setSectionResizeMode(1)

        self.model = MyModel(self)
        self.model.clear()
        self.model.error.connect(self.show_error)
        self.ui.treeView.setModel(self.model)
        self.ui.treeView.setUniformRowHeights(True)
        self.ui.treeView.setSelectionBehavior(QAbstractItemView.SelectRows)
        #self.ui.treeView.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ui.treeView.header().setSectionResizeMode(1)

        self.resize(int(self.settings.value("main_window_width", 800)), int(self.settings.value("main_window_height", 600)))
        self.restoreState(self.settings.value("main_window_state", b""))

        self._subscribed_nodes = [] # FIXME: not really needed

        self.uaclient = UaClient() 
        self.ui.connectButton.clicked.connect(self._connect)
        self.ui.disconnectButton.clicked.connect(self._disconnect)
        self.ui.treeView.activated.connect(self._show_attrs_and_refs)
        self.ui.treeView.clicked.connect(self._show_attrs_and_refs)
        #self.ui.treeView.expanded.connect(self._fit)

        self.ui.actionSubscribeDataChange.triggered.connect(self._subscribe)
        self.ui.actionSubscribeEvent.triggered.connect(self._subscribeEvent)
        self.ui.actionUnsubscribe.triggered.connect(self._unsubscribe)
        self.ui.actionConnect.triggered.connect(self._connect)
        self.ui.actionDisconnect.triggered.connect(self._disconnect)

        self.ui.attrRefreshButton.clicked.connect(self.show_attrs)

        # context menu
        self.ui.treeView.addAction(self.ui.actionSubscribeDataChange)
        self.ui.treeView.addAction(self.ui.actionSubscribeEvent)
        self.ui.treeView.addAction(self.ui.actionUnsubscribe)

        # handle subscriptions
        self._subhandler = SubHandler()
        self._subhandler.data_change_fired.connect(self._update_subscription_model, type=Qt.QueuedConnection)

    def show_error(self, msg, level=1):
        print("showing error: ", msg, level)
        self.ui.statusBar.show()
        self.ui.statusBar.setStyleSheet("QStatusBar { background-color : red; color : black; }")
        #self.ui.statusBar.clear()
        self.ui.statusBar.showMessage(str(msg))
        QTimer.singleShot(1500, self.ui.statusBar.hide)

    def _subscribeEvent(self):
        self.show_error("Not Implemented")

    def _subscribe(self):
        idx = self.ui.treeView.currentIndex()
        it = self.model.itemFromIndex(idx)
        if not id:
            self.show_error("No item currently selected")
        node = it.data()
        if node in self._subscribed_nodes:
            print("allready subscribed to node: ", node)
            return
        self.sub_model.setHorizontalHeaderLabels(["DisplayName", "Value", "SourceTimestamp"])
        row = [QStandardItem(it.text()), QStandardItem("No Data yet"), QStandardItem("")]
        row[0].setData(node)
        self.sub_model.appendRow(row)
        self._subscribed_nodes.append(node)
        self.ui.subDockWidget.raise_()
        try:
            self.uaclient.subscribe(node, self._subhandler)
        except Exception as ex:
            self.show_error(ex)
            idx = self.sub_model.indexFromItem(row[0])
            self.sub_model.takeRow(idx.row())

    def _unsubscribe(self):
        idx = self.ui.treeView.currentIndex()
        it = self.model.itemFromIndex(idx)
        if not id:
            print("No item currently selected")
        node = it.data()
        #FIXME: remove node from view
        self.uaclient.unsubscribe(node)
        self._subscribed_nodes.remove(node)
        i = 0
        while self.sub_model.item(i):
            item = self.sub_model.item(i)
            if item.data() == node:
                self.sub_model.removeRow(i)
            i += 1

    def _update_subscription_model(self, node, value, timestamp):
        i = 0
        while self.sub_model.item(i):
            item = self.sub_model.item(i)
            if item.data() == node:
                it = self.sub_model.item(i, 1)
                it.setText(value)
                it_ts = self.sub_model.item(i, 2)
                it_ts.setText(timestamp)
            i += 1

    def _show_attrs_and_refs(self, idx):
        node = self.get_current_node(idx)
        if node:
            self._show_attrs(node)
            self._show_refs(node)

    def get_current_node(self, idx=None):
        if idx is None:
            idx = self.ui.treeView.currentIndex()
        it = self.model.itemFromIndex(idx)
        if not it:
            return None
        node = it.data()
        if not node:
            print("No node for item:", it, it.text()) 
            return None
        return node

    def show_attrs(self):
        node = self.get_current_node()
        if node:
            self._show_attrs(node)
        else:
            self.attr_model.clear()

    def _show_refs(self, node):
        self.refs_model.clear()
        self.refs_model.setHorizontalHeaderLabels(['ReferenceType', 'NodeId', "BrowseName", "TypeDefinition"])
        try:
            refs = self.uaclient.get_all_refs(node) 
        except Exception as ex:
            self.show_error(ex)
            raise
        for ref in refs:
            self.refs_model.appendRow([QStandardItem(str(ref.ReferenceTypeId)),
                    QStandardItem(str(ref.NodeId)),
                    QStandardItem(str(ref.BrowseName)),
                    QStandardItem(str(ref.TypeDefinition))])

    def _show_attrs(self, node):
        try:
            attrs = self.uaclient.get_all_attrs(node) 
        except Exception as ex:
            self.show_error(ex)
            raise
        self.attr_model.clear()
        self.attr_model.setHorizontalHeaderLabels(['Attribute', 'Value'])
        for k, v in attrs.items():
            self.attr_model.appendRow([QStandardItem(k), QStandardItem(str(v))])

    def _connect(self):
        uri = self.ui.addrComboBox.currentText()
        try:
            self.uaclient.connect(uri)
        except Exception as ex:
            self.show_error(ex)
            raise

        self._update_address_list(uri)
        self.model.client = self.uaclient
        self.model.clear()
        self.model.add_item(*self.uaclient.get_root_node_and_desc())

    def _update_address_list(self, uri):
        if uri == self._address_list[0]:
            return
        if uri in self._address_list:
            self._address_list.remove(uri)
        self._address_list.insert(0, uri)
        if len(self._address_list) > self._address_list_max_count:
            self._address_list.pop(-1)

    def _disconnect(self):
        try:
            self.uaclient.disconnect()
        except Exception as ex:
            self.show_error(ex)
            raise
        finally:
            self.model.clear()
            self.sub_model.clear()
            self.model.client = None

    def closeEvent(self, event):
        self.settings.setValue("main_window_width", self.size().width())
        self.settings.setValue("main_window_height", self.size().height())
        self.settings.setValue("main_window_state", self.saveState())  
        self.settings.setValue("address_list", self._address_list)  
        self._disconnect()
        event.accept()


class MyModel(QStandardItemModel):

    error = pyqtSignal(str)

    def __init__(self, parent):
        super(MyModel, self).__init__(parent)
        self.client = None
        self._fetched = [] 

    def clear(self):
        QStandardItemModel.clear(self)
        self._fetched = []
        self.setHorizontalHeaderLabels(['DisplayName', "BrowseName", 'NodeId'])

    def add_item(self, node, desc, parent=None):
        data = [QStandardItem(desc.DisplayName.to_string()), QStandardItem(desc.BrowseName.to_string()), QStandardItem(desc.NodeId.to_string())]
        if desc.NodeClass == ua.NodeClass.Object:
            if desc.TypeDefinition == ua.TwoByteNodeId(ua.ObjectIds.FolderType):
                data[0].setIcon(QIcon(":/folder.svg"))
            else:
                data[0].setIcon(QIcon(":/object.svg"))
        elif desc.NodeClass == ua.NodeClass.Variable:
            if desc.TypeDefinition == ua.TwoByteNodeId(ua.ObjectIds.PropertyType):
                data[0].setIcon(QIcon(":/property.svg"))
            else:
                data[0].setIcon(QIcon(":/variable.svg"))

        data[0].setData(node)
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
            return QStandardItemModel.hasChildren(self, idx)
        return True

    def fetchMore(self, idx):
        parent = self.itemFromIndex(idx)
        if parent:
            self._fetchMore(parent)

    def _fetchMore(self, parent):
        try:
            for node, attrs in self.client.get_children(parent.data()):
                self.add_item(node, attrs, parent)
        except Exception as ex:
            self.error.emit(ex)
            raise


def main():
    app = QApplication(sys.argv)
    client = Window()
    client.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

