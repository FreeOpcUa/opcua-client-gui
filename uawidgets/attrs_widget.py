import functools
import logging
from dataclasses import fields
from enum import Enum
from typing import Any, Callable, TypeVar, cast

from PyQt6.QtCore import QAbstractItemModel, QModelIndex, QObject, QPoint, QSettings, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QHeaderView,
    QMenu,
    QStyleOptionViewItem,
    QStyledItemDelegate,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from asyncua import ua
from asyncua.common.ua_utils import data_type_to_string, string_to_val, val_to_string
from asyncua.sync import SyncNode, new_node
from asyncua.ua.uatypes import type_string_from_type

from uawidgets.get_node_dialog import GetNodeButton
from uawidgets.utils import trycatchslot


logger = logging.getLogger(__name__)


F = TypeVar("F", bound=Callable[..., Any])


def robust(func: F) -> F:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception:
            logger.exception("failed to call %s with args: %s %s", func, args, kwargs)
        return None
    return cast(F, wrapper)


class BitEditor(QDialog):
    """
    Edit bits in data
    FIXME: this should be a dialog but a Widget appearing directly in treewidget
    Patch welcome
    """

    def __init__(self, parent: QWidget, attr: ua.AttributeIds, val: int) -> None:
        QDialog.__init__(self, parent)
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.boxes: list[QCheckBox] = []
        self.enum: Any = attr_to_enum(attr)
        for el in self.enum:
            box = QCheckBox(el.name, parent)
            layout.addWidget(box)
            self.boxes.append(box)
            if ua.ua_binary.test_bit(val, el.value):
                box.setChecked(True)
            else:
                box.setChecked(False)

    def get_byte(self) -> int:
        data = 0
        for box in self.boxes:
            if box.isChecked():
                data = ua.ua_binary.set_bit(data, self.enum[box.text()].value)
        return data


class _Data:
    uatype: ua.VariantType

    def is_editable(self) -> bool:
        return self.uatype != ua.VariantType.ExtensionObject


class AttributeData(_Data):
    def __init__(self, attr: ua.AttributeIds, value: Any, uatype: ua.VariantType) -> None:
        self.attr = attr
        self.value = value
        self.uatype = uatype


class MemberData(_Data):
    def __init__(self, obj: Any, name: str, value: Any, uatype: ua.VariantType) -> None:
        self.obj = obj
        self.name = name
        self.value = value
        self.uatype = uatype


class ListData(_Data):
    def __init__(self, mylist: list[Any], idx: int, val: Any, uatype: ua.VariantType) -> None:
        self.mylist = mylist
        self.idx = idx
        self.value = val
        self.uatype = uatype


class AttrsWidget(QObject):

    error = pyqtSignal(Exception)
    attr_written = pyqtSignal(ua.AttributeIds, ua.DataValue)

    def __init__(self, view: QTreeView, show_timestamps: bool = True) -> None:
        QObject.__init__(self, view)
        self.view = view
        self._timestamps = show_timestamps
        delegate = MyDelegate(self.view, self)
        delegate.error.connect(self.error.emit)
        delegate.attr_written.connect(self.attr_written.emit)
        self.settings = QSettings()
        self.view.setItemDelegate(delegate)
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['Attribute', 'Value', 'DataType'])
        header = self.view.header()
        assert header is not None
        state = self.settings.value("WindowState/attrs_widget_state_v2", None)
        if state is not None:
            header.restoreState(state)
        self.view.setModel(self.model)
        self.current_node: SyncNode | None = None
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        self.view.expanded.connect(self._item_expanded)
        self.view.collapsed.connect(self._item_collapsed)
        self.view.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)

        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.showContextMenu)
        copyaction = QAction("&Copy Value", self.model)
        copyaction.triggered.connect(self._copy_value)
        self._contextMenu = QMenu()
        self._contextMenu.addAction(copyaction)

    def save_state(self) -> None:
        header = self.view.header()
        if header is not None:
            self.settings.setValue("WindowState/attrs_widget_state_v2", header.saveState())

    def set_read_only(self, read_only: bool) -> None:
        triggers = (
            QAbstractItemView.EditTrigger.NoEditTriggers
            if read_only
            else QAbstractItemView.EditTrigger.DoubleClicked
        )
        self.view.setEditTriggers(triggers)

    def _item_expanded(self, idx: QModelIndex) -> None:
        if not idx.parent().isValid():
            return
        it = self.model.itemFromIndex(idx.sibling(0, 1))
        if it is not None:
            it.setText("")

    def _item_collapsed(self, idx: QModelIndex) -> None:
        it = self.model.itemFromIndex(idx.sibling(0, 1))
        if it is None:
            return
        data = it.data(Qt.ItemDataRole.UserRole)
        it.setText(val_to_string(data.value))

    def showContextMenu(self, position: QPoint) -> None:
        item = self.get_current_item()
        if item:
            viewport = self.view.viewport()
            assert viewport is not None
            self._contextMenu.exec(viewport.mapToGlobal(position))

    def get_current_item(self, col_idx: int = 0) -> QStandardItem | None:
        idx = self.view.currentIndex()
        idx = idx.siblingAtColumn(col_idx)
        return self.model.itemFromIndex(idx)

    def _copy_value(self) -> None:
        it = self.get_current_item(1)
        if it:
            clipboard = QApplication.clipboard()
            if clipboard is not None:
                clipboard.setText(it.text())

    def clear(self) -> None:
        self.model.removeRows(0, self.model.rowCount())

    def reload(self) -> None:
        if self.current_node is not None:
            self.show_attrs(self.current_node)

    def show_attrs(self, node: SyncNode) -> None:
        self.current_node = node
        self.clear()
        if self.current_node:
            self._show_attrs()
        self.view.expandToDepth(0)

    def _show_attrs(self) -> None:
        attrs = self.get_all_attrs()
        for attr, dv in attrs:
            try:
                if attr == ua.AttributeIds.Value:
                    self._show_value_attr(attr, dv)
                elif attr == ua.AttributeIds.DataTypeDefinition:
                    self._show_sdef_attr(attr, dv)
                else:
                    self._show_attr(attr, dv)
            except Exception as ex:
                logger.exception("Exception while displaying attribute %s with value %s for node %s", attr, dv, self.current_node)
                self.error.emit(ex)

    def _show_attr(self, attr: ua.AttributeIds, dv: ua.DataValue) -> None:
        if attr == ua.AttributeIds.DataType:
            string = data_type_to_string(dv.Value.Value)
        elif attr in (ua.AttributeIds.AccessLevel,
                      ua.AttributeIds.UserAccessLevel,
                      ua.AttributeIds.WriteMask,
                      ua.AttributeIds.UserWriteMask,
                      ua.AttributeIds.EventNotifier):
            string = enum_to_string(attr, dv.Value.Value)
        else:
            string = val_to_string(dv.Value.Value)
        name_item = QStandardItem(attr.name)
        vitem = QStandardItem(string)
        vitem.setData(AttributeData(attr, dv.Value.Value, dv.Value.VariantType), Qt.ItemDataRole.UserRole)
        self.model.appendRow([name_item, vitem, QStandardItem(dv.Value.VariantType.name)])

    def _show_value_attr(self, attr: ua.AttributeIds, dv: ua.DataValue) -> None:
        name_item = QStandardItem("Value")
        vitem = QStandardItem()
        items = self._show_val(name_item, None, "Value", dv.Value.Value, dv.Value.VariantType)
        items[1].setData(AttributeData(attr, dv.Value.Value, dv.Value.VariantType), Qt.ItemDataRole.UserRole)
        row = [name_item, vitem, QStandardItem(dv.Value.VariantType.name)]
        self.model.appendRow(row)
        self._show_timestamps(name_item, dv)

    def _show_sdef_attr(self, attr: ua.AttributeIds, dv: ua.DataValue) -> None:
        if dv.Value.Value is None:
            return
        items = self._show_val(self.model, None, "DataTypeDefinition", dv.Value.Value, dv.Value.VariantType)
        items[1].setData(AttributeData(attr, dv.Value.Value, dv.Value.VariantType), Qt.ItemDataRole.UserRole)

    @robust
    def _show_val(
        self,
        parent: QStandardItem | QStandardItemModel,
        obj: Any,
        name: str,
        val: Any,
        vtype: ua.VariantType,
    ) -> list[QStandardItem]:
        name_item = QStandardItem(name)
        vitem = QStandardItem()
        vitem.setText(val_to_string(val))
        vitem.setData(MemberData(obj, name, val, vtype), Qt.ItemDataRole.UserRole)
        row = [name_item, vitem, QStandardItem(str(vtype))]
        if isinstance(val, list):
            row[2].setText("List of " + str(vtype))
            self._show_list(name_item, val, vtype)
        elif vtype == ua.VariantType.ExtensionObject:
            self._show_ext_obj(name_item, val)
        parent.appendRow(row)
        return row

    @robust
    def _show_list(self, parent: QStandardItem, mylist: list[Any], vtype: ua.VariantType) -> None:
        for idx, val in enumerate(mylist):
            name_item = QStandardItem(str(idx))
            vitem = QStandardItem()
            vitem.setText(val_to_string(val))
            vitem.setData(ListData(mylist, idx, val, vtype), Qt.ItemDataRole.UserRole)
            vtypename = vtype.name if isinstance(vtype, Enum) else str(vtype)
            row = [name_item, vitem, QStandardItem(vtypename)]
            parent.appendRow(row)
            if vtype == ua.VariantType.ExtensionObject or not isinstance(vtype, ua.VariantType):
                self._show_ext_obj(name_item, val)

    def refresh_list(self, parent: QStandardItem, mylist: list[Any], vtype: ua.VariantType) -> None:
        while parent.hasChildren():
            self.model.removeRow(0, parent.index())
        self._show_list(parent, mylist, vtype)

    @robust
    def _show_ext_obj(self, item: QStandardItem, val: Any) -> None:
        item.setText(item.text() + ": " + val.__class__.__name__)
        if val is None:
            self._show_val(item, val, "Value", None, ua.VariantType.Null)
            return
        for field in fields(val):
            member_val = getattr(val, field.name)
            att_type = type_string_from_type(field.type)
            if hasattr(ua.VariantType, att_type):
                attr = getattr(ua.VariantType, att_type)
            elif hasattr(ua, att_type):
                attr = getattr(ua, att_type)
            else:
                return
            self._show_val(item, val, field.name, member_val, attr)

    def _show_timestamps(self, item: QStandardItem, dv: ua.DataValue) -> None:
        string = val_to_string(dv.ServerTimestamp)
        item.appendRow([QStandardItem("Server Timestamp"), QStandardItem(string), QStandardItem(ua.VariantType.DateTime.name)])
        string = val_to_string(dv.SourceTimestamp)
        item.appendRow([QStandardItem("Source Timestamp"), QStandardItem(string), QStandardItem(ua.VariantType.DateTime.name)])

    def get_all_attrs(self) -> list[tuple[ua.AttributeIds, ua.DataValue]]:
        assert self.current_node is not None
        attrs = list(ua.AttributeIds)
        dvs = self.current_node.read_attributes(attrs)
        res: list[tuple[ua.AttributeIds, ua.DataValue]] = []
        for idx, dv in enumerate(dvs):
            if dv.StatusCode.is_good():
                res.append((attrs[idx], dv))
        res.sort(key=lambda x: x[0].name)
        return res


class MyDelegate(QStyledItemDelegate):

    error = pyqtSignal(Exception)
    attr_written = pyqtSignal(ua.AttributeIds, ua.DataValue)

    def __init__(self, parent: QObject | None, attrs_widget: AttrsWidget) -> None:
        QStyledItemDelegate.__init__(self, parent)
        self.attrs_widget = attrs_widget

    @trycatchslot
    def createEditor(
        self,
        parent: QWidget | None,
        option: QStyleOptionViewItem,
        idx: QModelIndex,
    ) -> QWidget | None:
        if idx.column() != 1 or parent is None:
            return None
        item = self.attrs_widget.model.itemFromIndex(idx)
        if item is None:
            return None
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data.is_editable():
            return None
        text = item.text()
        if isinstance(data, (ListData, MemberData)):
            return QStyledItemDelegate.createEditor(self, parent, option, idx)
        elif data.attr == ua.AttributeIds.NodeId:
            return None
        elif data.uatype == ua.VariantType.Boolean:
            combo = QComboBox(parent)
            combo.addItem("True")
            combo.addItem("False")
            combo.setCurrentText(text)
            return combo
        elif data.attr == ua.AttributeIds.NodeClass:
            combo = QComboBox(parent)
            for nclass in ua.NodeClass:
                combo.addItem(nclass.name)
            combo.setCurrentText(text)
            return combo
        elif data.attr == ua.AttributeIds.ValueRank:
            combo = QComboBox(parent)
            for rank in ua.ValueRank:
                combo.addItem(rank.name)
            combo.setCurrentText(text)
            return combo
        elif data.attr == ua.AttributeIds.DataType:
            nodeid = data.value
            assert self.attrs_widget.current_node is not None
            node = new_node(self.attrs_widget.current_node, nodeid)
            startnode = new_node(self.attrs_widget.current_node, ua.ObjectIds.BaseDataType)
            return GetNodeButton(parent, node, startnode)
        elif data.attr in (ua.AttributeIds.AccessLevel,
                           ua.AttributeIds.UserAccessLevel,
                           ua.AttributeIds.WriteMask,
                           ua.AttributeIds.UserWriteMask,
                           ua.AttributeIds.EventNotifier):
            return BitEditor(parent, data.attr, data.value)
        else:
            return QStyledItemDelegate.createEditor(self, parent, option, idx)

    @trycatchslot
    def setModelData(
        self,
        editor: QWidget | None,
        model: QAbstractItemModel | None,
        idx: QModelIndex,
    ) -> None:
        if editor is None or model is None:
            return
        data = model.data(idx, Qt.ItemDataRole.UserRole)

        if isinstance(data, AttributeData):
            self._write_attribute_data(data, editor, model, idx)
        elif isinstance(data, MemberData):
            self._set_member_data(data, editor, model, idx)
        elif isinstance(data, ListData):
            self._set_list_data(data, editor, model, idx)
        else:
            logger.info("Error while setting model data, data is %s", data)

    def _set_list_data(
        self,
        data: ListData,
        editor: QWidget,
        model: QAbstractItemModel,
        idx: QModelIndex,
    ) -> None:
        text = editor.text()  # type: ignore[attr-defined]
        data.mylist[data.idx] = string_to_val(text, data.uatype)
        model.setItemData(idx, {Qt.ItemDataRole.DisplayRole: text, Qt.ItemDataRole.UserRole: data})
        attr_data = self._get_attr_data(idx, model)
        self._write_attr(attr_data)

    def _set_member_data(
        self,
        data: MemberData,
        editor: QWidget,
        model: QAbstractItemModel,
        idx: QModelIndex,
    ) -> None:
        text = editor.text()  # type: ignore[attr-defined]
        val = string_to_val(text, data.uatype)
        data.value = val
        model.setItemData(idx, {Qt.ItemDataRole.DisplayRole: text, Qt.ItemDataRole.UserRole: data})
        setattr(data.obj, data.name, val)
        attr_data = self._get_attr_data(idx, model)
        self._write_attr(attr_data)

    def _get_attr_data(self, idx: QModelIndex, model: QAbstractItemModel) -> AttributeData:
        while True:
            idx = idx.parent()
            it = self.attrs_widget.model.itemFromIndex(idx.sibling(0, 1))
            if it is None:
                continue
            data = it.data(Qt.ItemDataRole.UserRole)
            if isinstance(data, AttributeData):
                return data

    def _get_parent_data(self, idx: QModelIndex, model: QAbstractItemModel) -> tuple[QModelIndex, Any]:
        parent_idx = idx.parent()
        it = self.attrs_widget.model.itemFromIndex(parent_idx.sibling(0, 1))
        return parent_idx, it.data(Qt.ItemDataRole.UserRole) if it is not None else None

    def _write_attribute_data(
        self,
        data: AttributeData,
        editor: QWidget,
        model: QAbstractItemModel,
        idx: QModelIndex,
    ) -> None:
        if data.attr is ua.AttributeIds.Value:
            try:
                assert self.attrs_widget.current_node is not None
                data.uatype = self.attrs_widget.current_node.read_data_type_as_variant_type()
            except Exception as ex:
                logger.exception("Could get primitive type of variable %s", self.attrs_widget.current_node)
                self.error.emit(ex)
                raise

        text: str
        if data.attr == ua.AttributeIds.NodeClass:
            data.value = ua.NodeClass[editor.currentText()]  # type: ignore[attr-defined]
            text = editor.currentText()  # type: ignore[attr-defined]
        elif data.attr == ua.AttributeIds.ValueRank:
            data.value = ua.ValueRank[editor.currentText()]  # type: ignore[attr-defined]
            text = editor.currentText()  # type: ignore[attr-defined]
        elif data.attr == ua.AttributeIds.DataType:
            data.value = editor.get_node().nodeid  # type: ignore[attr-defined]
            text = data_type_to_string(data.value)
        elif data.attr in (ua.AttributeIds.AccessLevel,
                           ua.AttributeIds.UserAccessLevel,
                           ua.AttributeIds.WriteMask,
                           ua.AttributeIds.UserWriteMask,
                           ua.AttributeIds.EventNotifier):
            data.value = editor.get_byte()  # type: ignore[attr-defined]
            text = enum_to_string(data.attr, data.value)
        else:
            if isinstance(editor, QComboBox):
                text = editor.currentText()
            else:
                text = editor.text()  # type: ignore[attr-defined]
            data.value = string_to_val(text, data.uatype)
        model.setItemData(idx, {Qt.ItemDataRole.DisplayRole: text, Qt.ItemDataRole.UserRole: data})
        self._write_attr(data)
        if isinstance(data.value, list):
            item = self.attrs_widget.model.itemFromIndex(idx.sibling(0, 0))
            if item is not None:
                self.attrs_widget.refresh_list(item, data.value, data.uatype)

    def _write_attr(self, data: AttributeData) -> None:
        dv = ua.DataValue(ua.Variant(data.value, VariantType=data.uatype))
        try:
            logger.info("Writing attribute %s of node %s with value: %s", data.attr, self.attrs_widget.current_node, dv)
            assert self.attrs_widget.current_node is not None
            self.attrs_widget.current_node.write_attribute(data.attr, dv)
        except Exception as ex:
            logger.exception("Exception while writing %s to %s", dv, data.attr)
            self.error.emit(ex)
        else:
            self.attr_written.emit(data.attr, dv)


def attr_to_enum(attr: ua.AttributeIds) -> Any:
    attr_name = attr.name
    if attr_name.startswith("User"):
        attr_name = attr_name[4:]
    return getattr(ua, attr_name)


def enum_to_string(attr: ua.AttributeIds, val: int) -> str:
    attr_enum = attr_to_enum(attr)
    return ", ".join([e.name for e in attr_enum.parse_bitfield(val)])
