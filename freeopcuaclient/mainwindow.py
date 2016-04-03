#! /usr/bin/env python3

import sys
import datetime
from enum import Enum

from PyQt5.QtCore import pyqtSignal, QTimer, Qt, QObject, QSettings, QModelIndex
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt5.QtWidgets import QMainWindow, QWidget, QApplication, QAbstractItemView, QMenu, QAction

from opcua import ua

from freeopcuaclient.uaclient import UaClient
from freeopcuaclient.mainwindow_ui import Ui_MainWindow
from freeopcuaclient import resources


class DataChangeHandler(QObject):
    data_change_fired = pyqtSignal(object, str, str)

    def datachange_notification(self, node, val, data):
        if data.monitored_item.Value.SourceTimestamp:
            dato = data.monitored_item.Value.SourceTimestamp.isoformat()
        elif data.monitored_item.Value.ServerTimestamp:
            dato = data.monitored_item.Value.ServerTimestamp.isoformat()
        else:
            dato = datetime.datetime.now().isoformat()
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

    def clear(self):
        self._subscribed_nodes = []
        self.model.clear()

    def _subscribe(self):
        node = self.window.get_current_node()
        if node is None:
            return
        if node in self._subscribed_nodes:
            print("allready subscribed to event for node: ", node)
            return
        self.window.ui.evDockWidget.raise_()
        try:
            self.uaclient.subscribe_events(node, self._handler)
        except Exception as ex:
            self.window.show_error(ex)
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

    def clear(self):
        self._subscribed_nodes = []
        self.model.clear()

    def _subscribe(self):
        node = self.window.get_current_node()
        if node is None:
            return
        if node in self._subscribed_nodes:
            print("allready subscribed to node: ", node)
            return
        self.model.setHorizontalHeaderLabels(["DisplayName", "Value", "Timestamp"])
        row = [QStandardItem(node.display_name), QStandardItem("No Data yet"), QStandardItem("")]
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


class AttrsUI(object):

    def __init__(self, window, uaclient):
        self.window = window
        self.uaclient = uaclient
        self.model = QStandardItemModel()
        self.window.ui.attrView.setModel(self.model)
        self.window.ui.attrView.header().setSectionResizeMode(1)

        self.window.ui.treeView.activated.connect(self.show_attrs)
        self.window.ui.treeView.clicked.connect(self.show_attrs)
        self.window.ui.attrRefreshButton.clicked.connect(self.show_attrs)

        # Context menu
        self.window.ui.attrView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.window.ui.attrView.customContextMenuRequested.connect(self.showContextMenu)
        copyaction = QAction("&Copy Value", self.model)
        copyaction.triggered.connect(self._copy_value)
        self._contextMenu = QMenu()
        self._contextMenu.addAction(copyaction)

    def showContextMenu(self, position):
        item = self.get_current_item()
        if item:
            self._contextMenu.exec_(self.window.ui.attrView.mapToGlobal(position))

    def get_current_item(self, col_idx=0):
        idx = self.window.ui.attrView.currentIndex()
        return self.model.item(idx.row(), col_idx)

    def _copy_value(self, position):
        it = self.get_current_item(1)
        if it:
            QApplication.clipboard().setText(it.text())

    def clear(self):
        self.model.clear()

    def show_attrs(self, idx):
        if not isinstance(idx, QModelIndex):
            idx = None
        node = self.window.get_current_node(idx)
        self.model.clear()
        if node:
            self._show_attrs(node)

    def _show_attrs(self, node):
        try:
            attrs = self.uaclient.get_all_attrs(node)
        except Exception as ex:
            self.window.show_error(ex)
            raise
        self.model.setHorizontalHeaderLabels(['Attribute', 'Value'])
        for k, v in attrs.items():
            if isinstance(v, (ua.NodeId)):
                v = str(v)
            elif isinstance(v, (ua.QualifiedName, ua.LocalizedText)):
                v = v.to_string()
            elif isinstance(v, Enum):
                v = repr(v)
            elif isinstance(v, ua.DataValue):
                v = repr(v)
            else:
                v = str(v)
            self.model.appendRow([QStandardItem(k), QStandardItem(v)])


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
            self.model.appendRow([QStandardItem(str(ref.ReferenceTypeId)),
                                  QStandardItem(str(ref.NodeId)),
                                  QStandardItem(str(ref.BrowseName)),
                                  QStandardItem(str(ref.TypeDefinition))])


class TreeUI(object):

    def __init__(self, window, uaclient):
        self.window = window
        self.uaclient = uaclient
        self.model = TreeViewModel(self.uaclient)
        self.model.clear()  # FIXME: do we need this?
        self.model.error.connect(self.window.show_error)
        self.window.ui.treeView.setModel(self.model)
        self.window.ui.treeView.setUniformRowHeights(True)
        self.window.ui.treeView.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.window.ui.treeView.header().setSectionResizeMode(1)
        self.window.ui.actionCopyPath.triggered.connect(self._copy_path)
        self.window.ui.actionCopyNodeId.triggered.connect(self._copy_nodeid)
        # add items to context menu
        self.window.ui.treeView.addAction(self.window.ui.actionCopyPath)
        self.window.ui.treeView.addAction(self.window.ui.actionCopyNodeId)

    def clear(self):
        self.model.clear()

    def start(self):
        self.model.clear()
        self.model.add_item(*self.uaclient.get_root_node_and_desc())

    def _copy_path(self):
        path = self.get_current_path()
        path = ",".join(path)
        QApplication.clipboard().setText(path)

    def _copy_nodeid(self):
        node = self.get_current_node()
        if node:
            text = node.nodeid.to_string()
        else:
            text = ""
        QApplication.clipboard().setText(text)

    def get_current_path(self):
        idx = self.window.ui.treeView.currentIndex()
        idx = idx.sibling(idx.row(), 0)
        it = self.model.itemFromIndex(idx)
        path = []
        while it and it.data():
            node = it.data()
            name = node.get_browse_name().to_string()
            path.insert(0, name)
            it = it.parent()
        return path

    def get_current_node(self, idx=None):
        if idx is None:
            idx = self.window.ui.treeView.currentIndex()
        idx = idx.sibling(idx.row(), 0)
        it = self.model.itemFromIndex(idx)
        if not it:
            return None
        node = it.data()
        if not node:
            print("No node for item:", it, it.text())
            return None
        node.display_name = it.text()  # FIXME: hack
        return node


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

        self.tree_ui = TreeUI(self, self.uaclient)
        self.refs_ui = RefsUI(self, self.uaclient)
        self.attrs_ui = AttrsUI(self, self.uaclient)
        self.datachange_ui = DataChangeUI(self, self.uaclient)
        self.event_ui = EventUI(self, self.uaclient)

        self.resize(int(self.settings.value("main_window_width", 800)), int(self.settings.value("main_window_height", 600)))
        self.restoreState(self.settings.value("main_window_state", b""))

        self.ui.connectButton.clicked.connect(self._connect)
        self.ui.disconnectButton.clicked.connect(self._disconnect)
        # self.ui.treeView.expanded.connect(self._fit)

        self.ui.actionConnect.triggered.connect(self._connect)
        self.ui.actionDisconnect.triggered.connect(self._disconnect)

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
        self.tree_ui.start()

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


class TreeViewModel(QStandardItemModel):

    error = pyqtSignal(str)

    def __init__(self, uaclient):
        super(TreeViewModel, self).__init__()
        self.uaclient = uaclient
        self._fetched = []

    def clear(self):
        QStandardItemModel.clear(self)
        self._fetched = []
        self.setHorizontalHeaderLabels(['DisplayName', "BrowseName", 'NodeId'])

    def add_item(self, node, desc, parent=None):
        item = [QStandardItem(desc.DisplayName.to_string()), QStandardItem(desc.BrowseName.to_string()), QStandardItem(desc.NodeId.to_string())]
        if desc.NodeClass == ua.NodeClass.Object:
            if desc.TypeDefinition == ua.TwoByteNodeId(ua.ObjectIds.FolderType):
                item[0].setIcon(QIcon(":/folder.svg"))
            else:
                item[0].setIcon(QIcon(":/object.svg"))
        elif desc.NodeClass == ua.NodeClass.Variable:
            if desc.TypeDefinition == ua.TwoByteNodeId(ua.ObjectIds.PropertyType):
                item[0].setIcon(QIcon(":/property.svg"))
            else:
                item[0].setIcon(QIcon(":/variable.svg"))
        elif desc.NodeClass == ua.NodeClass.Method:
                item[0].setIcon(QIcon(":/method.svg"))

        item[0].setData(node)
        if parent:
            return parent.appendRow(item)
        else:
            return self.appendRow(item)

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
            for node, attrs in self.uaclient.get_children(parent.data()):
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
