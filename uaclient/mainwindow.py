import logging
import sys
from datetime import datetime
from typing import Any

from PyQt6.QtCore import (
    QCoreApplication,
    QFile,
    QItemSelection,
    QMimeData,
    QModelIndex,
    QObject,
    QPoint,
    QSettings,
    QTextStream,
    QTimer,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import QAction, QCloseEvent, QIcon, QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QHeaderView,
    QMainWindow,
    QMenu,
    QMessageBox,
    QWidget,
)

from uaclient.theme import breeze_resources  # noqa: F401

from asyncua import ua
from asyncua.sync import SyncNode

from uaclient.application_certificate_dialog import ApplicationCertificateDialog
from uaclient.connection_dialog import ConnectionDialog
from uaclient.graphwidget import GraphUI
from uaclient.mainwindow_ui import Ui_MainWindow
from uaclient.uaclient import UaClient

from uawidgets import resources  # noqa: F401  # must be here for ressources even if not used
from uawidgets.attrs_widget import AttrsWidget
from uawidgets.call_method_dialog import CallMethodDialog
from uawidgets.logger import QtHandler
from uawidgets.refs_widget import RefsWidget
from uawidgets.tree_widget import TreeWidget
from uawidgets.utils import trycatchslot


logger = logging.getLogger(__name__)


class DataChangeHandler(QObject):
    data_change_fired = pyqtSignal(object, str, str)

    def datachange_notification(self, node: SyncNode, val: Any, data: Any) -> None:
        if data.monitored_item.Value.SourceTimestamp:
            dato = data.monitored_item.Value.SourceTimestamp.isoformat()
        elif data.monitored_item.Value.ServerTimestamp:
            dato = data.monitored_item.Value.ServerTimestamp.isoformat()
        else:
            dato = datetime.now().isoformat()
        self.data_change_fired.emit(node, str(val), dato)


class EventHandler(QObject):
    event_fired = pyqtSignal(object)

    def event_notification(self, event: Any) -> None:
        self.event_fired.emit(event)


class EventUI:

    def __init__(self, window: "Window", uaclient: UaClient) -> None:
        self.window = window
        self.uaclient = uaclient
        self._handler = EventHandler()
        self._subscribed_nodes: list[SyncNode] = []
        self.model = QStandardItemModel()
        self.window.ui.evView.setModel(self.model)
        self.window.ui.actionSubscribeEvent.triggered.connect(self._subscribe)
        self.window.ui.actionUnsubscribeEvents.triggered.connect(self._unsubscribe)
        self.window.addAction(self.window.ui.actionSubscribeEvent)
        self.window.addAction(self.window.ui.actionUnsubscribeEvents)
        self.window.addAction(self.window.ui.actionAddToGraph)
        self._handler.event_fired.connect(self._update_event_model, type=Qt.ConnectionType.QueuedConnection)  # type: ignore[call-arg]

        self.model.canDropMimeData = self.canDropMimeData  # type: ignore[method-assign,assignment]
        self.model.dropMimeData = self.dropMimeData  # type: ignore[method-assign,assignment]

    def canDropMimeData(
        self,
        mdata: QMimeData | None,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex,
    ) -> bool:
        return True

    def show_error(self, *args: Any) -> None:
        self.window.show_error(*args)

    def dropMimeData(
        self,
        mdata: QMimeData | None,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex,
    ) -> bool:
        if mdata is None or self.uaclient.client is None:
            return False
        node = self.uaclient.client.get_node(mdata.text())
        self._subscribe(node)
        return True

    def clear(self) -> None:
        self._subscribed_nodes = []
        self.model.clear()

    @trycatchslot
    def _subscribe(self, node: SyncNode | None = None) -> None:
        logger.info("Subscribing to %s", node)
        if not node:
            node = self.window.get_current_node()
            if node is None:
                return
        if node in self._subscribed_nodes:
            logger.info("already subscribed to event for node: %s", node)
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
    def _unsubscribe(self) -> None:
        node = self.window.get_current_node()
        if node is None or node not in self._subscribed_nodes:
            return
        self.uaclient.unsubscribe_events(node)
        self._subscribed_nodes.remove(node)

    @trycatchslot
    def _update_event_model(self, event: Any) -> None:
        self.model.appendRow([QStandardItem(str(event))])


class DataChangeUI:

    def __init__(self, window: "Window", uaclient: UaClient) -> None:
        self.window = window
        self.uaclient = uaclient
        self._subhandler = DataChangeHandler()
        self._subscribed_nodes: list[SyncNode] = []
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["DisplayName", "Value", "Timestamp"])
        self.window.ui.subView.setModel(self.model)
        header = self.window.ui.subView.horizontalHeader()
        assert header is not None
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.window.ui.actionSubscribeDataChange.triggered.connect(self._subscribe)
        self.window.ui.actionUnsubscribeDataChange.triggered.connect(self._unsubscribe)

        self.window.addAction(self.window.ui.actionSubscribeDataChange)
        self.window.addAction(self.window.ui.actionUnsubscribeDataChange)

        self._subhandler.data_change_fired.connect(self._update_subscription_model, type=Qt.ConnectionType.QueuedConnection)  # type: ignore[call-arg]

        self.model.canDropMimeData = self.canDropMimeData  # type: ignore[method-assign,assignment]
        self.model.dropMimeData = self.dropMimeData  # type: ignore[method-assign,assignment]

    def canDropMimeData(
        self,
        mdata: QMimeData | None,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex,
    ) -> bool:
        return True

    def dropMimeData(
        self,
        mdata: QMimeData | None,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex,
    ) -> bool:
        if mdata is None or self.uaclient.client is None:
            return False
        node = self.uaclient.client.get_node(mdata.text())
        self._subscribe(node)
        return True

    def clear(self) -> None:
        self._subscribed_nodes = []
        self.model.clear()

    def show_error(self, *args: Any) -> None:
        self.window.show_error(*args)

    @trycatchslot
    def _subscribe(self, node: SyncNode | None = None) -> None:
        if not isinstance(node, SyncNode):
            node = self.window.get_current_node()
            if node is None:
                return
        if node in self._subscribed_nodes:
            logger.warning("already subscribed to node: %s ", node)
            return
        text = str(node.read_display_name().Text)
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
    def _unsubscribe(self) -> None:
        node = self.window.get_current_node()
        if node is None or node not in self._subscribed_nodes:
            return
        self.uaclient.unsubscribe_datachange(node)
        self._subscribed_nodes.remove(node)
        i = 0
        while True:
            item = self.model.item(i)
            if item is None:
                break
            if item.data() == node:
                self.model.removeRow(i)
            else:
                i += 1

    def _update_subscription_model(self, node: SyncNode, value: str, timestamp: str) -> None:
        i = 0
        while True:
            item = self.model.item(i)
            if item is None:
                break
            if item.data() == node:
                it = self.model.item(i, 1)
                it_ts = self.model.item(i, 2)
                if it is not None:
                    it.setText(value)
                if it_ts is not None:
                    it_ts.setText(timestamp)
            i += 1


class Window(QMainWindow):

    def __init__(self) -> None:
        QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowIcon(QIcon(":/network.svg"))

        w = QWidget()
        self.ui.addrDockWidget.setTitleBarWidget(w)
        self.tabifyDockWidget(self.ui.evDockWidget, self.ui.subDockWidget)
        self.tabifyDockWidget(self.ui.subDockWidget, self.ui.refDockWidget)
        self.tabifyDockWidget(self.ui.refDockWidget, self.ui.graphDockWidget)

        self.ui.statusBar.hide()

        QCoreApplication.setOrganizationName("FreeOpcUa")
        QCoreApplication.setApplicationName("OpcUaClient")
        self.settings = QSettings()

        self._address_list: list[str] = self.settings.value("address_list", ["opc.tcp://localhost:4840", "opc.tcp://localhost:53530/OPCUA/SimulationServer/"])
        self._address_list_max_count = int(self.settings.value("address_list_max_count", 10))

        for addr in self._address_list:
            self.ui.addrComboBox.insertItem(100, addr)

        self.uaclient = UaClient()

        self.tree_ui = TreeWidget(self.ui.treeView)
        self.tree_ui.error.connect(self.show_error)
        self.setup_context_menu_tree()
        selection_model = self.ui.treeView.selectionModel()
        assert selection_model is not None
        selection_model.currentChanged.connect(self._update_actions_state)

        self.refs_ui = RefsWidget(self.ui.refView)
        self.refs_ui.error.connect(self.show_error)
        self.attrs_ui = AttrsWidget(self.ui.attrView)
        self.attrs_ui.error.connect(self.show_error)
        self.datachange_ui = DataChangeUI(self, self.uaclient)
        self.event_ui = EventUI(self, self.uaclient)
        self.graph_ui = GraphUI(self, self.uaclient)

        self.ui.addrComboBox.currentTextChanged.connect(self._uri_changed)
        self._uri_changed(self.ui.addrComboBox.currentText())

        selection_model.selectionChanged.connect(self.show_refs)
        self.ui.actionCopyPath.triggered.connect(self.tree_ui.copy_path)
        self.ui.actionCopyNodeId.triggered.connect(self.tree_ui.copy_nodeid)
        self.ui.actionCall.triggered.connect(self.call_method)

        selection_model.selectionChanged.connect(self.show_attrs)
        self.ui.attrRefreshButton.clicked.connect(self.show_attrs)

        self.resize(int(self.settings.value("main_window_width", 800)), int(self.settings.value("main_window_height", 600)))
        data = self.settings.value("main_window_state", None)
        if data:
            self.restoreState(data)

        self.ui.connectButton.clicked.connect(self.connect)
        self.ui.disconnectButton.clicked.connect(self.disconnect)

        self.ui.actionConnect.triggered.connect(self.connect)
        self.ui.actionDisconnect.triggered.connect(self.disconnect)

        self.ui.connectOptionButton.clicked.connect(self.show_connection_dialog)
        self.ui.actionClient_Application_Certificate.triggered.connect(self.show_application_certificate_dialog)
        self.ui.actionDark_Mode.triggered.connect(self.dark_mode)

    def _uri_changed(self, uri: str) -> None:
        self.uaclient.load_security_settings(uri)

    def show_connection_dialog(self) -> None:
        dia = ConnectionDialog(self, self.ui.addrComboBox.currentText())
        dia.security_mode = self.uaclient.security_mode
        dia.security_policy = self.uaclient.security_policy
        dia.certificate_path = self.uaclient.user_certificate_path
        dia.private_key_path = self.uaclient.user_private_key_path
        ret = dia.exec()
        if ret:
            self.uaclient.security_mode = dia.security_mode
            self.uaclient.security_policy = dia.security_policy
            self.uaclient.user_certificate_path = dia.certificate_path
            self.uaclient.user_private_key_path = dia.private_key_path

    def show_application_certificate_dialog(self) -> None:
        dia = ApplicationCertificateDialog(self)
        dia.certificate_path = self.uaclient.application_certificate_path
        dia.private_key_path = self.uaclient.application_private_key_path
        ret = dia.exec()
        if ret == QDialog.DialogCode.Accepted:
            self.uaclient.application_certificate_path = dia.certificate_path
            self.uaclient.application_private_key_path = dia.private_key_path
        self.uaclient.save_application_certificate_settings()

    @trycatchslot
    def show_refs(self, selection: QItemSelection) -> None:
        if isinstance(selection, QItemSelection):
            if not selection.indexes():
                return

        node = self.get_current_node()
        if node:
            self.refs_ui.show_refs(node)

    @trycatchslot
    def show_attrs(self, selection: QItemSelection) -> None:
        if isinstance(selection, QItemSelection):
            if not selection.indexes():
                return

        node = self.get_current_node()
        if node:
            self.attrs_ui.show_attrs(node)

    def show_error(self, msg: Any) -> None:
        logger.warning("showing error: %s", msg)
        self.ui.statusBar.show()
        self.ui.statusBar.setStyleSheet("QStatusBar { background-color : red; color : black; }")
        self.ui.statusBar.showMessage(str(msg))
        QTimer.singleShot(1500, self.ui.statusBar.hide)

    def get_current_node(self, idx: QModelIndex | None = None) -> SyncNode | None:
        return self.tree_ui.get_current_node(idx)

    def get_uaclient(self) -> UaClient:
        return self.uaclient

    @trycatchslot
    def connect(self) -> None:
        uri = self.ui.addrComboBox.currentText().strip()
        try:
            self.uaclient.connect(uri)
        except Exception as ex:
            self.show_error(ex)
            raise

        self._update_address_list(uri)
        assert self.uaclient.client is not None
        self.tree_ui.set_root_node(self.uaclient.client.nodes.root)
        self.ui.treeView.setFocus()
        self.load_current_node()

    def _update_address_list(self, uri: str) -> None:
        if uri == self._address_list[0]:
            return
        if uri in self._address_list:
            self._address_list.remove(uri)
        self._address_list.insert(0, uri)
        if len(self._address_list) > self._address_list_max_count:
            self._address_list.pop(-1)

    def disconnect(self) -> None:
        try:
            self.uaclient.disconnect()
        except Exception as ex:
            self.show_error(ex)
            raise
        finally:
            self.save_current_node()
            self.tree_ui.clear()
            self.refs_ui.clear()
            self.attrs_ui.clear()
            self.datachange_ui.clear()
            self.event_ui.clear()

    def closeEvent(self, event: QCloseEvent | None) -> None:
        assert event is not None
        self.tree_ui.save_state()
        self.attrs_ui.save_state()
        self.refs_ui.save_state()
        self.settings.setValue("main_window_width", self.size().width())
        self.settings.setValue("main_window_height", self.size().height())
        self.settings.setValue("main_window_state", self.saveState())
        self.settings.setValue("address_list", self._address_list)
        self.disconnect()
        event.accept()

    def save_current_node(self) -> None:
        current_node = self.tree_ui.get_current_node()
        if current_node:
            mysettings = self.settings.value("current_node", None)
            if mysettings is None:
                mysettings = {}
            uri = self.ui.addrComboBox.currentText()
            mysettings[uri] = current_node.nodeid.to_string()
            self.settings.setValue("current_node", mysettings)

    def load_current_node(self) -> None:
        mysettings = self.settings.value("current_node", None)
        if mysettings is None:
            return
        uri = self.ui.addrComboBox.currentText()
        if uri in mysettings:
            nodeid = ua.NodeId.from_string(mysettings[uri])
            assert self.uaclient.client is not None
            node = self.uaclient.client.get_node(nodeid)
            self.tree_ui.expand_to_node(node)

    def setup_context_menu_tree(self) -> None:
        self.ui.treeView.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ui.treeView.customContextMenuRequested.connect(self._show_context_menu_tree)
        self._contextMenu = QMenu()
        self.addAction(self.ui.actionCopyPath)
        self.addAction(self.ui.actionCopyNodeId)
        self._contextMenu.addSeparator()
        self._contextMenu.addAction(self.ui.actionCall)
        self._contextMenu.addSeparator()

    def addAction(self, action: QAction) -> None:  # type: ignore[override]
        self._contextMenu.addAction(action)

    @trycatchslot
    def _update_actions_state(self, current: QModelIndex, previous: QModelIndex) -> None:
        node = self.get_current_node(current)
        self.ui.actionCall.setEnabled(False)
        if node:
            if node.read_node_class() == ua.NodeClass.Method:
                self.ui.actionCall.setEnabled(True)

    def _show_context_menu_tree(self, position: QPoint) -> None:
        node = self.tree_ui.get_current_node()
        if node:
            viewport = self.ui.treeView.viewport()
            assert viewport is not None
            self._contextMenu.exec(viewport.mapToGlobal(position))

    def call_method(self) -> None:
        node = self.get_current_node()
        if node is None:
            return
        assert self.uaclient.client is not None
        dia = CallMethodDialog(self, self.uaclient.client, node)
        dia.show()

    def dark_mode(self) -> None:
        self.settings.setValue("dark_mode", self.ui.actionDark_Mode.isChecked())

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText("Restart for changes to take effect")
        msg.exec()


def main() -> None:
    app = QApplication(sys.argv)
    client = Window()
    handler = QtHandler(client.ui.logTextEdit)
    logging.getLogger().addHandler(handler)
    logging.getLogger("uaclient").setLevel(logging.INFO)
    logging.getLogger("uawidgets").setLevel(logging.INFO)

    if QSettings().value("dark_mode", "false") == "true":
        file = QFile(":/dark.qss")
        file.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text)
        stream = QTextStream(file)
        app.setStyleSheet(stream.readAll())

    client.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
