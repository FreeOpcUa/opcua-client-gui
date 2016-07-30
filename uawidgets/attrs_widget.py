from PyQt5.QtCore import pyqtSignal, Qt, QObject
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QApplication, QMenu, QAction

from opcua import ua
from opcua.common.ua_utils import string_to_variant, variant_to_string, val_to_string


class AttrsWidget(QObject):

    error = pyqtSignal(str)

    def __init__(self, view):
        QObject.__init__(self, view)
        self.view = view
        self.model = QStandardItemModel()
        self.view.setModel(self.model)
        self.current_node = None
        self.view.doubleClicked.connect(self.edit_attr)
        self.model.itemChanged.connect(self.edit_attr_finished)
        self.view.header().setSectionResizeMode(1)

        # Context menu
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.showContextMenu)
        copyaction = QAction("&Copy Value", self.model)
        copyaction.triggered.connect(self._copy_value)
        self._contextMenu = QMenu()
        self._contextMenu.addAction(copyaction)

    def _check_edit(self, item):
        """
        filter only element we want to edit.
        take either idx eller item as argument
        """
        if item.column() != 1:
            return False
        name_item = self.model.item(item.row(), 0)
        if name_item.text() != "Value":
            return False
        return True

    def edit_attr(self, idx):
        if not self._check_edit(idx):
            return
        attritem = self.model.item(idx.row(), 0)
        if attritem.text() == "Value":
            self.view.edit(idx)

    def edit_attr_finished(self, item):
        if not self._check_edit(item):
            return
        try:
            var = item.data()
            val = item.text()
            var = string_to_variant(val, var.VariantType)
            self.current_node.set_value(var)
        except Exception as ex:
            self.error.emit(ex)
            raise
        finally:
            dv = self.current_node.get_data_value()
            item.setText(variant_to_string(dv.Value))
            name_item = self.model.item(item.row(), 0)
            name_item.child(0, 1).setText(val_to_string(dv.ServerTimestamp))
            name_item.child(1, 1).setText(val_to_string(dv.SourceTimestamp))

    def showContextMenu(self, position):
        item = self.get_current_item()
        if item:
            self._contextMenu.exec_(self.view.mapToGlobal(position))

    def get_current_item(self, col_idx=0):
        idx = self.view.currentIndex()
        return self.model.item(idx.row(), col_idx)

    def _copy_value(self, position):
        it = self.get_current_item(1)
        if it:
            QApplication.clipboard().setText(it.text())

    def clear(self):
        self.model.clear()

    def show_attrs(self, node):
        self.current_node = node
        self.model.clear()
        if self.current_node:
            self._show_attrs()
        self.view.expandAll()

    def _show_attrs(self):
        attrs = self.get_all_attrs()
        self.model.setHorizontalHeaderLabels(['Attribute', 'Value', 'DataType'])
        for name, dv in attrs:
            if name == "DataType":
                if isinstance(dv.Value.Value.Identifier, int) and dv.Value.Value.Identifier < 63:
                    string = ua.DataType_to_VariantType(dv.Value.Value).name
                elif dv.Value.Value.Identifier in ua.ObjectIdNames:
                    string = ua.ObjectIdNames[dv.Value.Value.Identifier]
                else:
                    string = dv.Value.Value.to_string()
            elif name in ("AccessLevel", "UserAccessLevel"):
                string = ",".join([e.name for e in ua.int_to_AccessLevel(dv.Value.Value)])
            elif name in ("WriteMask", "UserWriteMask"):
                string = ",".join([e.name for e in ua.int_to_WriteMask(dv.Value.Value)])
            elif name in ("EventNotifier"):
                string = ",".join([e.name for e in ua.int_to_EventNotifier(dv.Value.Value)])
            else:
                string = variant_to_string(dv.Value)
            name_item = QStandardItem(name)
            vitem = QStandardItem(string)
            vitem.setData(dv.Value)
            self.model.appendRow([name_item, vitem, QStandardItem(dv.Value.VariantType.name)])
            if name == "Value":
                string = val_to_string(dv.ServerTimestamp)
                name_item.appendRow([QStandardItem("Server Timestamp"), QStandardItem(string), QStandardItem(ua.VariantType.DateTime.name)])
                string = val_to_string(dv.SourceTimestamp)
                name_item.appendRow([QStandardItem("Source Timestamp"), QStandardItem(string), QStandardItem(ua.VariantType.DateTime.name)])

    def get_all_attrs(self):
        names = []
        vals = []
        for name, val in ua.AttributeIds.__dict__.items():
            if not name.startswith("_"):
                names.append(name)
                vals.append(val)
        try:
            attrs = self.current_node.get_attributes(vals)
        except Exception as ex:
            self.error.emit(ex)
            raise
        res = []
        for idx, name in enumerate(names):
            if attrs[idx].StatusCode.is_good():
                res.append((name, attrs[idx]))
        res.sort()
        return res



