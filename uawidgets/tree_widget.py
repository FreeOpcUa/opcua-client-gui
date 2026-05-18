import logging
from typing import Iterable

from PyQt6.QtCore import pyqtSignal, QMimeData, QModelIndex, QObject, QSize, Qt, QSettings
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QIcon, QAction
from PyQt6.QtWidgets import QApplication, QAbstractItemView, QHeaderView, QTreeView

from asyncua import ua
from asyncua.sync import SyncNode, new_node


logger = logging.getLogger(__name__)

# Bumped to invalidate any pre-PyQt6 header state that may have left
# columns at zero width / hidden after the Qt 5 -> 6 migration.
_HEADER_STATE_KEY = "tree_widget_state_v2"


class TreeWidget(QObject):

    error = pyqtSignal(Exception)

    def __init__(self, view: QTreeView) -> None:
        QObject.__init__(self, view)
        self.view = view
        self.model = TreeViewModel()
        self.model.error.connect(self.error)
        self.view.setModel(self.model)

        self.model.setHorizontalHeaderLabels(['DisplayName', "BrowseName", 'NodeId'])
        # Clamp icon rendering size; the bundled SVGs lack viewBox attributes
        # and Qt6's SVG painter logs "buffer size too big" when asked to
        # render them at unbounded sizes.
        self.view.setIconSize(QSize(16, 16))
        header = self.view.header()
        assert header is not None
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        self.view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.settings = QSettings()
        state = self.settings.value(_HEADER_STATE_KEY, None)
        if state is not None:
            header.restoreState(state)

        self.actionReload = QAction("Reload", self)
        self.actionReload.triggered.connect(self.reload_current)

    def save_state(self) -> None:
        header = self.view.header()
        if header is not None:
            self.settings.setValue(_HEADER_STATE_KEY, header.saveState())

    def clear(self) -> None:
        self.model.clear()

    def set_root_node(self, node: SyncNode) -> None:
        self.model.clear()
        self.model.set_root_node(node)
        self.view.expandToDepth(0)

    def copy_path(self) -> None:
        path = self.get_current_path()
        path_str = ",".join(path)
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(path_str)

    def expand_current_node(self, expand: bool = True) -> None:
        idx = self.view.currentIndex()
        self.view.setExpanded(idx, expand)

    def expand_to_node(self, node: SyncNode | str) -> None:
        """
        Expand tree until given node and select it
        """
        if isinstance(node, str):
            idxlist = self.model.match(self.model.index(0, 0), Qt.ItemDataRole.DisplayRole, node, 1, Qt.MatchFlag.MatchExactly | Qt.MatchFlag.MatchRecursive)
            if not idxlist:
                raise ValueError(f"Node {node} not found in tree")
            node = self.model.data(idxlist[0], Qt.ItemDataRole.UserRole)
        path = node.get_path()
        for path_node in path:
            try:
                text = path_node.read_display_name().Text
            except ua.UaError:
                return
            idxlist = self.model.match(self.model.index(0, 0), Qt.ItemDataRole.DisplayRole, text, 1, Qt.MatchFlag.MatchExactly | Qt.MatchFlag.MatchRecursive)
            if idxlist:
                idx = idxlist[0]
                self.view.setExpanded(idx, True)
                self.view.setCurrentIndex(idx)
                self.view.activated.emit(idx)
            else:
                logger.warning("While expanding tree, could not find node %s in tree view, this might be OK", path_node)

    def copy_nodeid(self) -> None:
        node = self.get_current_node()
        if node is None:
            return
        text = node.nodeid.to_string()
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(text)

    def get_current_path(self) -> list[str]:
        idx = self.view.currentIndex()
        idx = idx.sibling(idx.row(), 0)
        it: QStandardItem | None = self.model.itemFromIndex(idx)
        path: list[str] = []
        while it and it.data(Qt.ItemDataRole.UserRole):
            node = it.data(Qt.ItemDataRole.UserRole)
            name = node.read_browse_name().to_string()
            path.insert(0, name)
            it = it.parent()
        return path

    def update_browse_name_current_item(self, bname: ua.QualifiedName) -> None:
        idx = self.view.currentIndex()
        idx = idx.sibling(idx.row(), 1)
        it = self.model.itemFromIndex(idx)
        if it is not None:
            it.setText(bname.to_string())

    def update_display_name_current_item(self, dname: ua.LocalizedText) -> None:
        idx = self.view.currentIndex()
        idx = idx.sibling(idx.row(), 0)
        it = self.model.itemFromIndex(idx)
        if it is not None:
            it.setText(dname.Text)

    def reload_current(self) -> None:
        idx = self.view.currentIndex()
        idx = idx.sibling(idx.row(), 0)
        it = self.model.itemFromIndex(idx)
        if not it:
            return
        self.reload(it)

    def reload(self, item: QStandardItem | None = None) -> None:
        if item is None:
            item = self.model.item(0, 0)
        if item is None:
            return
        for _ in range(item.rowCount()):
            child_it = item.child(0, 0)
            if child_it is None:
                continue
            node = child_it.data(Qt.ItemDataRole.UserRole)
            if node:
                self.model.reset_cache(node)
            item.takeRow(0)
        node = item.data(Qt.ItemDataRole.UserRole)
        if node:
            self.model.reset_cache(node)
            self.model.indexFromItem(item)

    def remove_current_item(self) -> None:
        idx = self.view.currentIndex()
        self.model.removeRow(idx.row(), idx.parent())

    def get_current_node(self, idx: QModelIndex | None = None) -> SyncNode | None:
        if idx is None:
            idx = self.view.currentIndex()
        idx = idx.sibling(idx.row(), 0)
        it = self.model.itemFromIndex(idx)
        if not it:
            return None
        node = it.data(Qt.ItemDataRole.UserRole)
        if not node:
            ex = RuntimeError("Item does not contain node data, report!")
            self.error.emit(ex)
            raise ex
        return node


class TreeViewModel(QStandardItemModel):

    error = pyqtSignal(Exception)

    def __init__(self) -> None:
        super().__init__()
        self._fetched: list[SyncNode] = []

    def clear(self) -> None:
        # remove all rows but not header!!
        self.removeRows(0, self.rowCount())
        self._fetched = []

    def set_root_node(self, node: SyncNode) -> None:
        desc = self._get_node_desc(node)
        self.add_item(desc, node=node)

    def _get_node_desc(self, node: SyncNode) -> ua.ReferenceDescription:
        attrs = node.read_attributes([ua.AttributeIds.DisplayName, ua.AttributeIds.BrowseName, ua.AttributeIds.NodeId, ua.AttributeIds.NodeClass])
        desc = ua.ReferenceDescription()
        desc.DisplayName = attrs[0].Value.Value
        desc.BrowseName = attrs[1].Value.Value
        desc.NodeId = attrs[2].Value.Value
        desc.NodeClass = attrs[3].Value.Value
        desc.TypeDefinition = ua.TwoByteNodeId(ua.ObjectIds.FolderType)
        return desc

    def add_item(
        self,
        desc: ua.ReferenceDescription,
        parent: QStandardItem | None = None,
        node: SyncNode | None = None,
    ) -> None:
        dname = bname = nodeid = "No Value"
        if desc.DisplayName:
            dname = desc.DisplayName.Text
        if desc.BrowseName:
            bname = desc.BrowseName.to_string()
        nodeid = desc.NodeId.to_string()
        item = [QStandardItem(dname), QStandardItem(bname), QStandardItem(nodeid)]
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
        elif desc.NodeClass == ua.NodeClass.ObjectType:
            item[0].setIcon(QIcon(":/object_type.svg"))
        elif desc.NodeClass == ua.NodeClass.VariableType:
            item[0].setIcon(QIcon(":/variable_type.svg"))
        elif desc.NodeClass == ua.NodeClass.DataType:
            item[0].setIcon(QIcon(":/data_type.svg"))
        elif desc.NodeClass == ua.NodeClass.ReferenceType:
            item[0].setIcon(QIcon(":/reference_type.svg"))
        if node:
            item[0].setData(node, Qt.ItemDataRole.UserRole)
        else:
            assert parent is not None
            parent_node = parent.data(Qt.ItemDataRole.UserRole)
            item[0].setData(new_node(parent_node, desc.NodeId), Qt.ItemDataRole.UserRole)
        if parent:
            parent.appendRow(item)
        else:
            self.appendRow(item)

    def reset_cache(self, node: SyncNode) -> None:
        if node in self._fetched:
            self._fetched.remove(node)

    def canFetchMore(self, idx: QModelIndex) -> bool:
        item = self.itemFromIndex(idx)
        if not item:
            return False
        node = item.data(Qt.ItemDataRole.UserRole)
        if node not in self._fetched:
            self._fetched.append(node)
            return True
        return False

    def hasChildren(self, parent: QModelIndex = QModelIndex()) -> bool:
        item = self.itemFromIndex(parent)
        if not item:
            return True
        node = item.data(Qt.ItemDataRole.UserRole)
        if node in self._fetched:
            return QStandardItemModel.hasChildren(self, parent)
        return True

    def fetchMore(self, idx: QModelIndex) -> None:
        parent = self.itemFromIndex(idx)
        if parent:
            self._fetchMore(parent)

    def _fetchMore(self, parent: QStandardItem) -> None:
        try:
            node = parent.data(Qt.ItemDataRole.UserRole)
            descs = node.get_children_descriptions()
            descs.sort(key=lambda x: x.BrowseName)
            added: list[ua.NodeId] = []
            for desc in descs:
                if desc.NodeId not in added:
                    self.add_item(desc, parent)
                    added.append(desc.NodeId)
        except Exception as ex:
            self.error.emit(ex)
            raise

    def mimeData(self, idxs: Iterable[QModelIndex]) -> QMimeData:
        mdata = QMimeData()
        nodes: list[str] = []
        for idx in idxs:
            item = self.itemFromIndex(idx)
            if item:
                node = item.data(Qt.ItemDataRole.UserRole)
                if node:
                    nodes.append(node.nodeid.to_string())
        mdata.setText(", ".join(nodes))
        return mdata
