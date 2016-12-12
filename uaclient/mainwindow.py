#! /usr/bin/env python3

import sys
from datetime import datetime
import inspect
from enum import Enum
import logging

from PyQt5.QtCore import pyqtSignal, QTimer, Qt, QObject, QSettings, QModelIndex, QMimeData, QCoreApplication
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt5.QtWidgets import QMainWindow, QWidget, QApplication, QAbstractItemView, QMenu, QAction

from opcua import ua
from opcua import Node

from uaclient.uaclient import UaClient
from uaclient.mainwindow_ui import Ui_MainWindow
from uaclient.connection_dialog import ConnectionDialog
from uawidgets import resources
from uawidgets.attrs_widget import AttrsWidget
from uawidgets.tree_widget import TreeWidget
from uawidgets.refs_widget import RefsWidget
from uawidgets.utils import trycatchslot
from uawidgets.logger import QtHandler


logger = logging.getLogger(__name__)


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

    def show_error(self, *args):
        self.window.show_error(*args)

    def dropMimeData(self, mdata, action, row, column, parent):
        node = self.uaclient.client.get_node(mdata.text())
        self._subscribe(node)
        return True

    def clear(self):
        self._subscribed_nodes = []
        self.model.clear()

    @trycatchslot
    def _subscribe(self, node=None):
        logger.info("Subscribing to %s", node)
        if not node:
            node = self.window.get_current_node()
            if node is None:
                return
        if node in self._subscribed_nodes:
            logger.info("allready subscribed to event for node: %s", node)
            return
        logger.info("Subscribing to events for %s", node)
        self.window.ui.evDockWidget.raise_()
        try:
            self.uaclient.subscribe_events(node, self._handler)
        except Exception as ex:
            self.window.show_error(ex)
            raise
        else:
            self._subscribed_nodes.append(node)

    @trycatchslot
    def _unsubscribe(self):
        node = self.window.get_current_node()
        if node is None:
            return
        self._subscribed_nodes.remove(node)
        self.uaclient.unsubscribe_events(node)

    @trycatchslot
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

    def show_error(self, *args):
        self.window.show_error(*args)

    @trycatchslot
    def _subscribe(self, node=None):
        if not isinstance(node, Node):
            node = self.window.get_current_node()
            if node is None:
                return
        if node in self._subscribed_nodes:
            logger.warning("allready subscribed to node: %s ", node)
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

    @trycatchslot
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

        # setup QSettings for application and get a settings object
        QCoreApplication.setOrganizationName("FreeOpcUa")
        QCoreApplication.setApplicationName("OpcUaClient")
        self.settings = QSettings()

        self._address_list = self.settings.value("address_list", ["opc.tcp://localhost:4840", "opc.tcp://localhost:53530/OPCUA/SimulationServer/"])
        self._address_list_max_count = int(self.settings.value("address_list_max_count", 10))

        # init widgets
        for addr in self._address_list:
            self.ui.addrComboBox.insertItem(-1, addr)

        self.uaclient = UaClient()

        self.tree_ui = TreeWidget(self.ui.treeView)
        self.tree_ui.error.connect(self.show_error)
        self.refs_ui = RefsWidget(self.ui.refView)
        self.refs_ui.error.connect(self.show_error)
        self.attrs_ui = AttrsWidget(self.ui.attrView)
        self.attrs_ui.error.connect(self.show_error)
        self.datachange_ui = DataChangeUI(self, self.uaclient)
        self.event_ui = EventUI(self, self.uaclient)

        self.ui.addrComboBox.currentTextChanged.connect(self._uri_changed)
        self._uri_changed(self.ui.addrComboBox.currentText())  # force update for current value at startup

        self.ui.treeView.activated.connect(self.show_refs)
        self.ui.treeView.clicked.connect(self.show_refs)
        self.ui.actionCopyPath.triggered.connect(self.tree_ui.copy_path)
        self.ui.actionCopyNodeId.triggered.connect(self.tree_ui.copy_nodeid)
        # add items to context menu
        self.ui.treeView.addAction(self.ui.actionCopyPath)
        self.ui.treeView.addAction(self.ui.actionCopyNodeId)

        self.ui.treeView.activated.connect(self.show_attrs)
        self.ui.treeView.clicked.connect(self.show_attrs)
        self.ui.attrRefreshButton.clicked.connect(self.show_attrs)

        self.resize(int(self.settings.value("main_window_width", 800)), int(self.settings.value("main_window_height", 600)))
        data = self.settings.value("main_window_state", None)
        if data:
            self.restoreState(data)

        self.ui.connectButton.clicked.connect(self.connect)
        self.ui.disconnectButton.clicked.connect(self.disconnect)
        # self.ui.treeView.expanded.connect(self._fit)

        self.ui.actionConnect.triggered.connect(self.connect)
        self.ui.actionDisconnect.triggered.connect(self.disconnect)

        self.ui.connectOptionButton.clicked.connect(self.show_connection_dialog)

    def _uri_changed(self, uri):
        self.uaclient.load_security_settings(uri)

    def show_connection_dialog(self):
        dia = ConnectionDialog(self, self.ui.addrComboBox.currentText())
        dia.security_mode = self.uaclient.security_mode
        dia.security_policy = self.uaclient.security_policy
        dia.certificate_path = self.uaclient.certificate_path
        dia.private_key_path = self.uaclient.private_key_path
        ret = dia.exec_()
        if ret:
            self.uaclient.security_mode = dia.security_mode
            self.uaclient.security_policy = dia.security_policy
            self.uaclient.certificate_path = dia.certificate_path
            self.uaclient.private_key_path = dia.private_key_path

    @trycatchslot
    def show_refs(self, idx):
        node = self.get_current_node(idx)
        if node:
            self.refs_ui.show_refs(node)
    
    @trycatchslot
    def show_attrs(self, idx):
        if not isinstance(idx, QModelIndex):
            idx = None
        node = self.get_current_node(idx)
        if node:
            self.attrs_ui.show_attrs(node)

    def show_error(self, msg):
        logger.warning("showing error: %s")
        self.ui.statusBar.show()
        self.ui.statusBar.setStyleSheet("QStatusBar { background-color : red; color : black; }")
        self.ui.statusBar.showMessage(str(msg))
        QTimer.singleShot(1500, self.ui.statusBar.hide)

    def get_current_node(self, idx=None):
        return self.tree_ui.get_current_node(idx)

    def get_uaclient(self):
        return self.uaclient

    @trycatchslot
    def connect(self):
        uri = self.ui.addrComboBox.currentText()
        try:
            self.uaclient.connect(uri)
        except Exception as ex:
            self.show_error(ex)
            raise

        self._update_address_list(uri)
        self.tree_ui.set_root_node(self.uaclient.client.get_root_node())

    def _update_address_list(self, uri):
        if uri == self._address_list[0]:
            return
        if uri in self._address_list:
            self._address_list.remove(uri)
        self._address_list.insert(0, uri)
        if len(self._address_list) > self._address_list_max_count:
            self._address_list.pop(-1)

    def disconnect(self):
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
        self.attrs_ui.save_state()
        self.refs_ui.save_state()
        self.settings.setValue("main_window_width", self.size().width())
        self.settings.setValue("main_window_height", self.size().height())
        self.settings.setValue("main_window_state", self.saveState())
        self.settings.setValue("address_list", self._address_list)
        self.disconnect()
        event.accept()


def main():
    app = QApplication(sys.argv)
    client = Window()
    handler = QtHandler(client.ui.logTextEdit)
    logging.getLogger().addHandler(handler)
    logging.getLogger("uaclient").setLevel(logging.INFO)
    logging.getLogger("uawidgets").setLevel(logging.INFO)
    #logging.getLogger("opcua").setLevel(logging.INFO)  # to enable logging of ua server
   
    client.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
