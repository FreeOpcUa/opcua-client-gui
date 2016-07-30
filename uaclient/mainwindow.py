#! /usr/bin/env python3

import sys
from datetime import datetime
from enum import Enum

from PyQt5.QtCore import pyqtSignal, QTimer, Qt, QObject, QSettings, QModelIndex, QMimeData
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt5.QtWidgets import QMainWindow, QWidget, QApplication, QAbstractItemView, QMenu, QAction

from opcua import ua

from uaclient.uaclient import UaClient
from uaclient.mainwindow_ui import Ui_MainWindow
from uaclient import resources
from uawidgets.attrs_widget import AttrsWidget
from uawidgets.tree_widget import TreeWidget


class DataChangeHandler(QObject):
    data_change_fired = pyqtSignal(object, str, str)

    def datachange_notification(self, node, val, data):
        if data.monitored_item.Value.SourceTimestamp:
            dato = data.monitored_item.Value.SourceTimestamp.isoformat()
        elif data.monitored_item.Value.ServerTimestamp:
            dato = data.monitored_item.Value.ServerTimestamp.isoformat()
        else:
            dato = datetime.now().isoformat()
        self.data_change_fired.emit(node, str(val), dato)


class EventHandler(QObject):
    event_fired = pyqtSignal(object)

    def event_notification(self, event):
        self.event_fired.emit(event)


class EventUI(object):

    def __init__(self, window, uaclient):
        self.window = window
        self.uaclient = uaclient
        self._handler = EventHandler()
        self._subscribed_nodes = []  # FIXME: not really needed
        self.model = QStandardItemModel()
        self.window.ui.evView.setModel(self.model)
        self.window.ui.actionSubscribeEvent.triggered.connect(self._subscribe)
        self.window.ui.actionUnsubscribeEvents.triggered.connect(self._unsubscribe)
        # context menu
        self.window.ui.treeView.addAction(self.window.ui.actionSubscribeEvent)
        self.window.ui.treeView.addAction(self.window.ui.actionUnsubscribeEvents)
        self._handler.event_fired.connect(self._update_event_model, type=Qt.QueuedConnection)

        # accept drops
        self.model.canDropMimeData = self.canDropMimeData
        self.model.dropMimeData = self.dropMimeData

    def canDropMimeData(self, mdata, action, row, column, parent):
        return True

    def dropMimeData(self, mdata, action, row, column, parent):
        node = self.uaclient.client.get_node(mdata.text())
        print("SUB 1", mdata.text(), node)
        self._subscribe(node)
        return True


    def clear(self):
        self._subscribed_nodes = []
        self.model.clear()

    def _subscribe(self, node=None):
        print("SUB", node)
        if not node:
            node = self.window.get_current_node()
            if node is None:
                return
        if node in self._subscribed_nodes:
            print("allready subscribed to event for node: ", node)
            return
        print("Subscribing to events for ", node)
        self.window.ui.evDockWidget.raise_()
        try:
            self.uaclient.subscribe_events(node, self._handler)
        except Exception as ex:
            self.window.show_error(ex)
            raise
        else:
            self._subscribed_nodes.append(node)

    def _unsubscribe(self):
        node = self.window.get_current_node()
        if node is None:
            return
        self._subscribed_nodes.remove(node)
        self.uaclient.unsubscribe_events(node)

    def _update_event_model(self, event):
        self.model.appendRow([QStandardItem(str(event))])


class DataChangeUI(object):

    def __init__(self, window, uaclient):
        self.window = window
        self.uaclient = uaclient
        self._subhandler = DataChangeHandler()
        self._subscribed_nodes = []
        self.model = QStandardItemModel()
        self.window.ui.subView.setModel(self.model)
        self.window.ui.subView.horizontalHeader().setSectionResizeMode(1)

        self.window.ui.actionSubscribeDataChange.triggered.connect(self._subscribe)
        self.window.ui.actionUnsubscribeDataChange.triggered.connect(self._unsubscribe)

        # populate contextual menu
        self.window.ui.treeView.addAction(self.window.ui.actionSubscribeDataChange)
        self.window.ui.treeView.addAction(self.window.ui.actionUnsubscribeDataChange)

        # handle subscriptions
        self._subhandler.data_change_fired.connect(self._update_subscription_model, type=Qt.QueuedConnection)
        
        # accept drops
        self.model.canDropMimeData = self.canDropMimeData
        self.model.dropMimeData = self.dropMimeData

    def canDropMimeData(self, mdata, action, row, column, parent):
        return True

    def dropMimeData(self, mdata, action, row, column, parent):
        node = self.uaclient.client.get_node(mdata.text())
        self._subscribe(node)
        return True

    def clear(self):
        self._subscribed_nodes = []
        self.model.clear()

    def _subscribe(self, node=None):
        if node is None:
            node = self.window.get_current_node()
            if node is None:
                return
        if node in self._subscribed_nodes:
            print("allready subscribed to node: ", node)
            return
        self.model.setHorizontalHeaderLabels(["DisplayName", "Value", "Timestamp"])
        text = str(node.get_display_name().Text)
        row = [QStandardItem(text), QStandardItem("No Data yet"), QStandardItem("")]
        row[0].setData(node)
        self.model.appendRow(row)
        self._subscribed_nodes.append(node)
        self.window.ui.subDockWidget.raise_()
        try:
            self.uaclient.subscribe_datachange(node, self._subhandler)
        except Exception as ex:
            self.window.show_error(ex)
            idx = self.model.indexFromItem(row[0])
            self.model.takeRow(idx.row())
            raise

    def _unsubscribe(self):
        node = self.window.get_current_node()
        if node is None:
            return
        self.uaclient.unsubscribe_datachange(node)
        self._subscribed_nodes.remove(node)
        i = 0
        while self.model.item(i):
            item = self.model.item(i)
            if item.data() == node:
                self.model.removeRow(i)
            i += 1

    def _update_subscription_model(self, node, value, timestamp):
        i = 0
        while self.model.item(i):
            item = self.model.item(i)
            if item.data() == node:
                it = self.model.item(i, 1)
                it.setText(value)
                it_ts = self.model.item(i, 2)
                it_ts.setText(timestamp)
            i += 1



class RefsUI(object):

    def __init__(self, window, uaclient):
        self.window = window
        self.uaclient = uaclient
        self.model = QStandardItemModel()
        self.window.ui.refView.setModel(self.model)
        self.window.ui.refView.horizontalHeader().setSectionResizeMode(1)

        self.window.ui.treeView.activated.connect(self.show_refs)
        self.window.ui.treeView.clicked.connect(self.show_refs)

    def clear(self):
        self.model.clear()

    def show_refs(self, idx):
        node = self.window.get_current_node(idx)
        self.model.clear()
        if node:
            self._show_refs(node)

    def _show_refs(self, node):
        self.model.setHorizontalHeaderLabels(['ReferenceType', 'NodeId', "BrowseName", "TypeDefinition"])
        try:
            refs = self.uaclient.get_all_refs(node)
        except Exception as ex:
            self.window.show_error(ex)
            raise
        for ref in refs:
            typename = ua.ObjectIdNames[ref.ReferenceTypeId.Identifier]
            if ref.NodeId.NamespaceIndex == 0 and ref.NodeId.Identifier in ua.ObjectIdNames:
                nodeid = ua.ObjectIdNames[ref.NodeId.Identifier]
            else:
                nodeid = ref.NodeId.to_string()
            if ref.TypeDefinition.Identifier in ua.ObjectIdNames:
                typedef = ua.ObjectIdNames[ref.TypeDefinition.Identifier]
            else:
                typedef = ref.TypeDefinition.to_string()
            self.model.appendRow([QStandardItem(typename),
                                  QStandardItem(nodeid),
                                  QStandardItem(ref.BrowseName.to_string()),
                                  QStandardItem(typedef)
                                  ])

class Window(QMainWindow):

    def __init__(self):
        QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowIcon(QIcon(":/network.svg"))

        # fix stuff imposible to do in qtdesigner
        # remove dock titlebar for addressbar
        w = QWidget()
        self.ui.addrDockWidget.setTitleBarWidget(w)
        # tabify some docks
        self.tabifyDockWidget(self.ui.evDockWidget, self.ui.subDockWidget)
        self.tabifyDockWidget(self.ui.subDockWidget, self.ui.refDockWidget)

        # we only show statusbar in case of errors
        self.ui.statusBar.hide()

        # load settings, seconds arg is default
        self.settings = QSettings("FreeOpcUa", "FreeOpcUaClient")
        self._address_list = self.settings.value("address_list", ["opc.tcp://localhost:4840", "opc.tcp://localhost:53530/OPCUA/SimulationServer/"])
        self._address_list_max_count = int(self.settings.value("address_list_max_count", 10))

        # init widgets
        for addr in self._address_list:
            self.ui.addrComboBox.insertItem(-1, addr)

        self.uaclient = UaClient()

        self.tree_ui = TreeWidget(self.ui.treeView)
        self.refs_ui = RefsUI(self, self.uaclient)
        self.attrs_ui = AttrsWidget(self.ui.attrView)
        self.datachange_ui = DataChangeUI(self, self.uaclient)
        self.event_ui = EventUI(self, self.uaclient)


        self.ui.actionCopyPath.triggered.connect(self.tree_ui.copy_path)
        self.ui.actionCopyNodeId.triggered.connect(self.tree_ui.copy_nodeid)
        # add items to context menu
        self.ui.treeView.addAction(self.ui.actionCopyPath)
        self.ui.treeView.addAction(self.ui.actionCopyNodeId)


        self.ui.treeView.activated.connect(self.show_attrs)
        self.ui.treeView.clicked.connect(self.show_attrs)
        self.ui.attrRefreshButton.clicked.connect(self.show_attrs)


        self.resize(int(self.settings.value("main_window_width", 800)), int(self.settings.value("main_window_height", 600)))
        self.restoreState(self.settings.value("main_window_state", b"", type="QByteArray"))

        self.ui.connectButton.clicked.connect(self._connect)
        self.ui.disconnectButton.clicked.connect(self._disconnect)
        # self.ui.treeView.expanded.connect(self._fit)

        self.ui.actionConnect.triggered.connect(self._connect)
        self.ui.actionDisconnect.triggered.connect(self._disconnect)

        self.ui.modeComboBox.addItem("None")
        self.ui.modeComboBox.addItem("Sign")
        self.ui.modeComboBox.addItem("SignAndEncrypt")

        self.ui.policyComboBox.addItem("None")
        self.ui.policyComboBox.addItem("Basic128RSA15")
        self.ui.policyComboBox.addItem("Basic256")
        self.ui.policyComboBox.addItem("Basic256SHA256")
    
    def show_attrs(self, idx):
        if not isinstance(idx, QModelIndex):
            idx = None
        node = self.get_current_node(idx)
        self.attrs_ui.show_attrs(node)

    def show_error(self, msg, level=1):
        print("showing error: ", msg, level)
        self.ui.statusBar.show()
        self.ui.statusBar.setStyleSheet("QStatusBar { background-color : red; color : black; }")
        self.ui.statusBar.showMessage(str(msg))
        QTimer.singleShot(1500, self.ui.statusBar.hide)

    def get_current_node(self, idx=None):
        return self.tree_ui.get_current_node(idx)

    def get_uaclient(self):
        return self.uaclient

    def _connect(self):
        uri = self.ui.addrComboBox.currentText()
        try:
            self.uaclient.connect(uri)
        except Exception as ex:
            self.show_error(ex)
            raise

        self._update_address_list(uri)
        self.tree_ui.start(self.uaclient.client)

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
            self.tree_ui.clear()
            self.refs_ui.clear()
            self.attrs_ui.clear()
            self.datachange_ui.clear()
            self.event_ui.clear()

    def closeEvent(self, event):
        self.settings.setValue("main_window_width", self.size().width())
        self.settings.setValue("main_window_height", self.size().height())
        self.settings.setValue("main_window_state", self.saveState())
        self.settings.setValue("address_list", self._address_list)
        self._disconnect()
        event.accept()


def main():
    app = QApplication(sys.argv)
    client = Window()
    client.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
