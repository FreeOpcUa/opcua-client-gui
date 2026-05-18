import uuid
from typing import Any

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from asyncua import ua
from asyncua.common.ua_utils import string_to_variant
from asyncua.sync import SyncNode, data_type_to_variant_type

from uawidgets.get_node_dialog import GetDataTypeNodeButton, GetNodeButton


class NewNodeBaseDialog(QDialog):
    def __init__(self, parent: QWidget | None, title: str, server: SyncNode) -> None:
        QDialog.__init__(self, parent)
        self.setWindowTitle(title)
        self.settings = QSettings()
        self.server = server

        self.vlayout = QVBoxLayout(self)
        self._layout = QHBoxLayout()
        self.vlayout.addLayout(self._layout)

        self._layout.addWidget(QLabel("ns:", self))

        self.nsComboBox = QComboBox(self)
        uries = server.get_namespace_array()
        for uri in uries:
            self.nsComboBox.addItem(uri)
        nsidx = int(self.settings.value("last_namespace", len(uries) - 1))
        if nsidx > len(uries) - 1:
            nsidx = len(uries) - 1
        self.nsComboBox.setCurrentIndex(nsidx)
        self._layout.addWidget(self.nsComboBox)

        self._layout.addWidget(QLabel("Name:", self))
        self.nameLabel = QLineEdit(self)
        self.nameLabel.setMinimumWidth(120)
        self.nameLabel.setText("NoName")
        self._layout.addWidget(self.nameLabel)
        self.nodeidCheckBox = QCheckBox("Auto NodeId", self)
        self.nodeidCheckBox.stateChanged.connect(self._show_nodeid)
        self._layout.addWidget(self.nodeidCheckBox)
        self.nodeidLineEdit = QLineEdit(self)
        self.nodeidLineEdit.setMinimumWidth(80)
        self.nodeidLineEdit.setText(self.settings.value("last_nodeid_prefix", f"ns={nsidx};i=20000"))
        self._layout.addWidget(self.nodeidLineEdit)

        if self.settings.value("last_node_widget_vis", False) == "true":
            self.nodeidCheckBox.setChecked(False)
            self.nodeidLineEdit.show()
        else:
            self.nodeidCheckBox.setChecked(True)
            self.nodeidLineEdit.hide()

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal,
            self,
        )
        self.vlayout.addWidget(self.buttons)

        self.buttons.accepted.connect(self.accept)
        self.buttons.accepted.connect(self._store_state)
        self.buttons.rejected.connect(self.reject)

    def _store_state(self) -> None:
        self.settings.setValue("last_namespace", self.nsComboBox.currentIndex())
        self.settings.setValue("last_node_widget_vis", not self.nodeidCheckBox.isChecked())
        ns_nt = self.nodeidLineEdit.text().split(';')
        self.settings.setValue("last_nodeid_prefix", ns_nt[0] + ';' + ns_nt[1][0:2])

    def _show_nodeid(self, val: int) -> None:
        if val:
            self.nodeidLineEdit.hide()
        else:
            self.nodeidLineEdit.show()
        self.adjustSize()

    def get_nodeid_and_bname(self) -> tuple[ua.NodeId, ua.QualifiedName]:
        ns = self.nsComboBox.currentIndex()
        name = self.nameLabel.text()
        bname = ua.QualifiedName(name, ns)
        if self.nodeidCheckBox.isChecked():
            nodeid = ua.NodeId(NamespaceIndex=ns)
        else:
            nodeid = ua.NodeId.from_string(self.nodeidLineEdit.text())
        return nodeid, bname

    def get_args(self) -> tuple[Any, ...]:
        nodeid, bname = self.get_nodeid_and_bname()
        return nodeid, bname

    @classmethod
    def getArgs(
        cls,
        parent: QWidget | None,
        title: str,
        server: SyncNode,
        *args: Any,
        **kwargs: Any,
    ) -> tuple[tuple[Any, ...] | list[Any], bool]:
        dialog = cls(parent, title, server, *args, **kwargs)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            return dialog.get_args(), True
        else:
            return [], False


class NewUaObjectDialog(NewNodeBaseDialog):
    def __init__(
        self,
        parent: QWidget | None,
        title: str,
        server: SyncNode,
        base_node_type: SyncNode,
        current_node_type: SyncNode | None = None,
    ) -> None:
        NewNodeBaseDialog.__init__(self, parent, title, server)

        if current_node_type is None:
            current_node_type = base_node_type

        self.objectTypeButton = GetNodeButton(self, current_node_type, base_node_type)
        self._layout.addWidget(self.objectTypeButton)

    def get_args(self) -> tuple[Any, ...]:
        nodeid, bname = self.get_nodeid_and_bname()
        otype = self.objectTypeButton.get_node()
        return nodeid, bname, otype


class NewUaVariableDialog(NewNodeBaseDialog):
    def __init__(
        self,
        parent: QWidget | None,
        title: str,
        server: SyncNode,
        dtype: str | None = None,
    ) -> None:
        NewNodeBaseDialog.__init__(self, parent, title, server)

        self.valLineEdit = QLineEdit(self)
        self.valLineEdit.setMinimumWidth(100)
        self._layout.addWidget(self.valLineEdit)

        self.dataTypeButton = GetDataTypeNodeButton(self, self.server, self.settings, dtype)
        self.dataTypeButton.value_changed.connect(self._data_type_changed)
        self._layout.addWidget(self.dataTypeButton)
        self._data_type_changed(self.dataTypeButton.get_node())

    def _data_type_changed(self, node: SyncNode) -> None:
        if node.nodeid in (
                ua.NodeId(ua.ObjectIds.Decimal),
                ua.NodeId(ua.ObjectIds.Float),
                ua.NodeId(ua.ObjectIds.Double)):
            self.valLineEdit.setText(str(0.0))
            self.valLineEdit.setEnabled(True)
        elif node.nodeid in (
                ua.NodeId(ua.ObjectIds.UInt16),
                ua.NodeId(ua.ObjectIds.UInt32),
                ua.NodeId(ua.ObjectIds.UInt64),
                ua.NodeId(ua.ObjectIds.Int16),
                ua.NodeId(ua.ObjectIds.Int32),
                ua.NodeId(ua.ObjectIds.Int64)):
            self.valLineEdit.setText(str(0))
            self.valLineEdit.setEnabled(True)
        elif node.nodeid in (
                ua.NodeId(ua.ObjectIds.Structure),
                ua.NodeId(ua.ObjectIds.Enumeration),
                ua.NodeId(ua.ObjectIds.DiagnosticInfo)):
            self.valLineEdit.setText("Null")
            self.valLineEdit.setEnabled(False)
        elif node.nodeid == ua.NodeId(ua.ObjectIds.Guid):
            self.valLineEdit.setText(str(uuid.uuid4()))
            self.valLineEdit.setEnabled(True)
        elif node.nodeid == ua.NodeId(ua.ObjectIds.Boolean):
            self.valLineEdit.setText("true")
            self.valLineEdit.setEnabled(True)
        elif node.nodeid in (ua.NodeId(ua.ObjectIds.NodeId), ua.NodeId(ua.ObjectIds.ExpandedNodeId)):
            self.valLineEdit.setText("ns=1;i=1000")
            self.valLineEdit.setEnabled(True)
        elif node.nodeid == ua.NodeId(ua.ObjectIds.DateTime):
            self.valLineEdit.setText("2020-01-31T12:00:00")
            self.valLineEdit.setEnabled(True)
        else:
            self.valLineEdit.setText("Null")
            self.valLineEdit.setEnabled(True)

    def get_args(self) -> tuple[Any, ...]:
        nodeid, bname = self.get_nodeid_and_bname()
        dtype = self.dataTypeButton.get_node()
        vtype = data_type_to_variant_type(dtype)
        if vtype == ua.VariantType.ExtensionObject:
            var = ua.Variant()
        else:
            var = string_to_variant(self.valLineEdit.text(), vtype)
        return nodeid, bname, var, vtype, dtype.nodeid


class NewUaMethodDialog(NewNodeBaseDialog):
    def __init__(self, parent: QWidget | None, title: str, server: SyncNode) -> None:
        NewNodeBaseDialog.__init__(self, parent, title, server)

        self.widgets: list[list[Any]] = []

        self.inplayout = QVBoxLayout(self)
        self.vlayout.addLayout(self.inplayout)
        self.inplayout.addLayout(self.add_input_header())

        self.ouplayout = QVBoxLayout(self)
        self.vlayout.addLayout(self.ouplayout)
        self.ouplayout.addLayout(self.add_output_header())

    def get_args(self) -> tuple[Any, ...]:
        nodeid, bname = self.get_nodeid_and_bname()

        input_args: list[ua.Argument] = []
        output_args: list[ua.Argument] = []

        for row in self.widgets:
            dtype = row[3].get_node()
            name = row[1].text()
            description = row[2].text()

            method_arg = ua.Argument()
            method_arg.Name = name
            method_arg.DataType = dtype.nodeid
            method_arg.ValueRank = -1
            method_arg.ArrayDimensions = []
            method_arg.Description = ua.LocalizedText(description)

            if row[0] == 'input':
                input_args.append(method_arg)
            else:
                output_args.append(method_arg)

        return nodeid, bname, None, input_args, output_args

    def add_row(self, mode: str) -> QHBoxLayout:
        rowlayout = QHBoxLayout(self)

        rowlayout.addWidget(QLabel("Arg Name:", self))
        argNameLabel = QLineEdit(self)
        argNameLabel.setText("")
        rowlayout.addWidget(argNameLabel)

        rowlayout.addWidget(QLabel("Description:", self))
        argDescLabel = QLineEdit(self)
        argDescLabel.setText("")
        rowlayout.addWidget(argDescLabel)

        dataTypeButton = GetDataTypeNodeButton(self, self.server, self.settings)
        rowlayout.addWidget(dataTypeButton)

        self.widgets.append([mode, argNameLabel, argDescLabel, dataTypeButton])
        return rowlayout

    def _add_input_row(self) -> None:
        self.inplayout.addLayout(self.add_row("input"))

    def _add_output_row(self) -> None:
        self.ouplayout.addLayout(self.add_row("output"))

    def add_input_header(self) -> QHBoxLayout:
        header_row = QHBoxLayout(self)
        header_row.addWidget(QLabel("Input", self))
        button = QPushButton("Add input argument")
        button.clicked.connect(self._add_input_row)
        header_row.addWidget(button)
        return header_row

    def add_output_header(self) -> QHBoxLayout:
        header_row = QHBoxLayout(self)
        header_row.addWidget(QLabel("Output", self))
        button = QPushButton("Add output argument")
        header_row.addWidget(button)
        button.clicked.connect(self._add_output_row)
        return header_row

    def add_h_line(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        return line
