import logging

from PyQt6.QtCore import (
    pyqtSignal,
    QAbstractItemModel,
    QModelIndex,
    QObject,
    QPoint,
    QSettings,
    Qt,
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QAction
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QMenu,
    QStyleOptionViewItem,
    QStyledItemDelegate,
    QTableView,
    QWidget,
)

from asyncua import ua
from asyncua.sync import SyncNode, new_node

from uawidgets.utils import trycatchslot
from uawidgets.get_node_dialog import GetNodeTextButton


logger = logging.getLogger(__name__)


class RefsWidget(QObject):

    error = pyqtSignal(Exception)
    reference_changed = pyqtSignal(SyncNode)

    def __init__(self, view: QTableView) -> None:
        self.view = view
        QObject.__init__(self, view)
        self.model = QStandardItemModel()

        delegate = MyDelegate(self.view, self)
        delegate.error.connect(self.error.emit)
        delegate.reference_changed.connect(self.reference_changed.emit)
        self.view.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.view.setModel(self.model)
        self.view.setItemDelegate(delegate)
        self.settings = QSettings()
        self.model.setHorizontalHeaderLabels(['ReferenceType', 'NodeId', "BrowseName", "TypeDefinition"])
        header = self.view.horizontalHeader()
        assert header is not None
        state = self.settings.value("WindowState/refs_widget_state_v2", None)
        if state is not None:
            header.restoreState(state)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        self.node: SyncNode | None = None

        self.reloadAction = QAction("Reload", self.model)
        self.reloadAction.triggered.connect(self.reload)
        self.addRefAction = QAction("Add Reference", self.model)
        self.addRefAction.triggered.connect(self.add_ref)
        self.removeRefAction = QAction("Remove Reference", self.model)
        self.removeRefAction.triggered.connect(self.remove_ref)

        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.showContextMenu)
        self._contextMenu = QMenu()
        self._contextMenu.addAction(self.reloadAction)
        self._contextMenu.addSeparator()
        self._contextMenu.addAction(self.addRefAction)
        self._contextMenu.addAction(self.removeRefAction)

    def showContextMenu(self, position: QPoint) -> None:
        if not self.node:
            return
        self.removeRefAction.setEnabled(False)
        idx = self.view.currentIndex()
        if idx.isValid():
            self.removeRefAction.setEnabled(True)
        viewport = self.view.viewport()
        assert viewport is not None
        self._contextMenu.exec(viewport.mapToGlobal(position))

    def clear(self) -> None:
        # remove all rows but not header!!
        self.model.removeRows(0, self.model.rowCount())
        self.node = None

    def _make_default_ref(self) -> ua.ReferenceDescription:
        return ua.ReferenceDescription()

    @trycatchslot
    def add_ref(self) -> None:
        ref = self._make_default_ref()
        logger.info("Adding ref: %s", ref)
        self._add_ref_row(ref)
        idx = self.model.index(self.model.rowCount() - 1, 0)
        self.view.setCurrentIndex(idx)

    @trycatchslot
    def reload(self) -> None:
        node = self.node
        self.clear()
        if node is not None:
            self.show_refs(node)

    @trycatchslot
    def remove_ref(self) -> None:
        idx = self.view.currentIndex()
        if not idx.isValid():
            logger.warning("No valid reference selected to remove")
        idx = idx.sibling(idx.row(), 0)
        item = self.model.itemFromIndex(idx)
        if item is None:
            return
        ref = item.data(Qt.ItemDataRole.UserRole)
        self.do_remove_ref(ref)
        self.reload()

    def do_remove_ref(self, ref: ua.ReferenceDescription, check: bool = True) -> None:
        if self.node is None:
            return
        logger.info("Removing: %s", ref)
        it = ua.DeleteReferencesItem()
        it.SourceNodeId = self.node.nodeid
        it.ReferenceTypeId = ref.ReferenceTypeId
        it.IsForward = ref.IsForward
        it.TargetNodeId = ref.NodeId
        it.DeleteBidirectional = False
        results = self.node.server.delete_references([it])
        logger.info("Remove result: %s", results[0])
        if check:
            results[0].check()

    def save_state(self) -> None:
        header = self.view.horizontalHeader()
        if header is not None:
            self.settings.setValue("WindowState/refs_widget_state_v2", header.saveState())

    def set_read_only(self, read_only: bool) -> None:
        triggers = (
            QAbstractItemView.EditTrigger.NoEditTriggers
            if read_only
            else QAbstractItemView.EditTrigger.DoubleClicked
        )
        self.view.setEditTriggers(triggers)
        self.addRefAction.setEnabled(not read_only)
        self.removeRefAction.setEnabled(not read_only)

    def show_refs(self, node: SyncNode) -> None:
        self.clear()
        self.node = node
        self._show_refs(node)

    def _show_refs(self, node: SyncNode) -> None:
        try:
            refs = node.get_children_descriptions(refs=ua.ObjectIds.References)
        except Exception as ex:
            self.error.emit(ex)
            raise
        for ref in refs:
            self._add_ref_row(ref)

    def _add_ref_row(self, ref: ua.ReferenceDescription) -> None:
        if ref.ReferenceTypeId.Identifier in ua.ObjectIdNames:
            typename = ua.ObjectIdNames[ref.ReferenceTypeId.Identifier]
        else:
            typename = str(ref.ReferenceTypeId)
        nodeid = ref.NodeId.to_string()
        if ref.NodeId.NamespaceIndex == 0 and ref.NodeId.Identifier in ua.ObjectIdNames:
            nodeid += ": " + ua.ObjectIdNames[ref.NodeId.Identifier]
        if ref.TypeDefinition.Identifier in ua.ObjectIdNames:
            typedef = ua.ObjectIdNames[ref.TypeDefinition.Identifier]
        else:
            typedef = ref.TypeDefinition.to_string()
        titem = QStandardItem(typename)
        titem.setData(ref, Qt.ItemDataRole.UserRole)
        self.model.appendRow([
            titem,
            QStandardItem(nodeid),
            QStandardItem(ref.BrowseName.to_string()),
            QStandardItem(typedef)
        ])


class MyDelegate(QStyledItemDelegate):

    error = pyqtSignal(Exception)
    reference_changed = pyqtSignal(SyncNode)

    def __init__(self, parent: QObject | None, widget: RefsWidget) -> None:
        QStyledItemDelegate.__init__(self, parent)
        self._widget = widget

    @trycatchslot
    def createEditor(
        self,
        parent: QWidget | None,
        option: QStyleOptionViewItem,
        idx: QModelIndex,
    ) -> QWidget | None:
        if idx.column() > 1 or self._widget.node is None or parent is None:
            return None
        data_idx = idx.sibling(idx.row(), 0)
        item = self._widget.model.itemFromIndex(data_idx)
        if item is None:
            return None
        ref = item.data(Qt.ItemDataRole.UserRole)
        if idx.column() == 1:
            node = new_node(self._widget.node, ref.NodeId)
            startnode = new_node(self._widget.node, ua.ObjectIds.RootFolder)
            return GetNodeTextButton(parent, node, startnode)
        else:  # idx.column() == 0
            node = new_node(self._widget.node, ref.ReferenceTypeId)
            startnode = new_node(self._widget.node, ua.ObjectIds.ReferenceTypesFolder)
            return GetNodeTextButton(parent, node, startnode)

    @trycatchslot
    def setModelData(
        self,
        editor: QWidget | None,
        model: QAbstractItemModel | None,
        idx: QModelIndex,
    ) -> None:
        if editor is None or model is None:
            return
        data_idx = idx.sibling(idx.row(), 0)
        ref = model.data(data_idx, Qt.ItemDataRole.UserRole)
        self._widget.do_remove_ref(ref, check=False)
        if idx.column() == 0:
            ref.ReferenceTypeId = editor.get_node().nodeid  # type: ignore[attr-defined]
            model.setData(idx, ref.ReferenceTypeId.to_string(), Qt.ItemDataRole.DisplayRole)
        elif idx.column() == 1:
            ref.NodeId = editor.get_node().nodeid  # type: ignore[attr-defined]
            ref.NodeClass = editor.get_node().get_node_class()  # type: ignore[attr-defined]
            model.setData(idx, ref.NodeId.to_string(), Qt.ItemDataRole.DisplayRole)
        model.setData(data_idx, ref, Qt.ItemDataRole.UserRole)
        if ref.NodeId.is_null() or ref.ReferenceTypeId.is_null():
            logger.info("Do not save yet. Need NodeId and ReferenceTypeId to be set")
            return
        self._write_ref(ref)

    def _write_ref(self, ref: ua.ReferenceDescription) -> None:
        if self._widget.node is None:
            return
        logger.info("Writing ref %s", ref)
        it = ua.AddReferencesItem()
        it.SourceNodeId = self._widget.node.nodeid
        it.ReferenceTypeId = ref.ReferenceTypeId
        it.IsForward = ref.IsForward
        it.TargetNodeId = ref.NodeId
        it.TargetNodeClass = ref.NodeClass

        results = self._widget.node.server.add_references([it])
        results[0].check()

        self.reference_changed.emit(self._widget.node)
        self._widget.reload()
