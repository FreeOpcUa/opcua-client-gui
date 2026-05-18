from PyQt6.QtCore import pyqtSignal, QSettings, Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from asyncua import ua
from asyncua.sync import SyncNode, new_node

from uawidgets.tree_widget import TreeWidget


class GetNodeTextButton(QWidget):
    """
    Create a text field with a button which will query a node
    """

    def __init__(self, parent: QWidget, currentnode: SyncNode, startnode: SyncNode) -> None:
        QWidget.__init__(self, parent)
        if currentnode.nodeid.is_null():
            text = "Null"
        else:
            text = currentnode.nodeid.to_string()
        self.lineEdit = QLineEdit(parent)
        self.lineEdit.setText(text)
        self.button = QPushButton(parent)
        self.button.setText("...")
        self.button.setMinimumWidth(5)
        self._layout = QHBoxLayout(parent)
        self._layout.setSpacing(0)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.addWidget(self.lineEdit)
        self._layout.addWidget(self.button)
        self.setLayout(self._layout)
        self.start_node = startnode
        self.button.clicked.connect(self.get_new_node)

    def get_new_node(self) -> tuple[SyncNode | None, bool]:
        node = self.get_node()
        node, ok = GetNodeDialog.getNode(self, self.start_node, currentnode=node)
        if ok and node is not None:
            self.lineEdit.setText(node.nodeid.to_string())
        return node, ok

    def get_node(self) -> SyncNode:
        text = self.lineEdit.text()
        if text and text not in ("None", "Null"):
            current = ua.NodeId.from_string(text)
        else:
            current = ua.NodeId()
        return new_node(self.start_node, current)


class GetNodeButton(QPushButton):
    """
    Create Button which will query a node
    """

    value_changed = pyqtSignal(SyncNode)

    def __init__(self, parent: QWidget, currentnode: SyncNode, startnode: SyncNode) -> None:
        text = "Null"
        try:
            text = currentnode.read_browse_name().to_string()
        except ua.UaError:
            pass
        QPushButton.__init__(self, text, parent)
        self._current_node = currentnode
        self.start_node = startnode
        self.clicked.connect(self.get_new_node)

    def get_new_node(self) -> tuple[SyncNode | None, bool]:
        node, ok = GetNodeDialog.getNode(self, self.start_node, currentnode=self._current_node)
        if ok and node is not None:
            self._current_node = node
            self.setText(self._current_node.read_browse_name().to_string())
            self.value_changed.emit(self._current_node)
        return node, ok

    def get_node(self) -> SyncNode:
        return self._current_node


class GetNodeDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None,
        startnode: SyncNode,
        currentnode: SyncNode | None = None,
    ) -> None:
        QDialog.__init__(self, parent)

        layout = QVBoxLayout(self)

        self.treeview = QTreeView(self)
        self.treeview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree = TreeWidget(self.treeview)
        self.tree.set_root_node(startnode)
        layout.addWidget(self.treeview)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal, self)
        layout.addWidget(self.buttons)
        self.resize(800, 600)

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.treeview.activated.connect(self.accept)

        if currentnode:
            self.tree.expand_to_node(currentnode)

    def get_node(self) -> SyncNode | None:
        return self.tree.get_current_node()

    @staticmethod
    def getNode(
        parent: QWidget | None,
        startnode: SyncNode,
        currentnode: SyncNode | None = None,
    ) -> tuple[SyncNode | None, bool]:
        dialog = GetNodeDialog(parent, startnode, currentnode)
        result = dialog.exec()
        node = dialog.get_node()
        return node, result == QDialog.DialogCode.Accepted


class GetDataTypeNodeButton(GetNodeButton):
    """
    Specialized GetNodeButton for getting a data type
    Create Button which will query a node
    """

    def __init__(
        self,
        parent: QWidget,
        server: SyncNode,
        settings: QSettings,
        dtype: str | None = None,
    ) -> None:
        # We pass settings because we cannot create QSettings before __init__ of super()
        self.settings = settings
        base_data_type = server.get_node(ua.ObjectIds.BaseDataType)
        if dtype is None:
            dtype = self.settings.value("last_datatype", None)
        if dtype is None:
            current_type = server.get_node(ua.ObjectIds.Float)
        else:
            current_type = server.get_node(dtype)
        GetNodeButton.__init__(self, parent, current_type, base_data_type)

    def get_new_node(self) -> tuple[SyncNode | None, bool]:
        node, ok = GetNodeButton.get_new_node(self)
        if ok and node is not None:
            self.settings.setValue("last_datatype", node.nodeid.to_string())
        return node, ok
