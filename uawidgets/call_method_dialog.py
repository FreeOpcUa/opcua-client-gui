import logging
from typing import Any

from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from asyncua import ua
from asyncua.common.ua_utils import data_type_to_string, string_to_variant, val_to_string
from asyncua.sync import SyncNode, call_method_full, data_type_to_variant_type


logger = logging.getLogger(__name__)


class CallMethodDialog(QDialog):
    def __init__(self, parent: QWidget | None, server: Any, parent_node, method_node: SyncNode) -> None:
        QDialog.__init__(self, parent)
        self.setWindowTitle("UA Method Call")
        self.server = server
        self.parent_node = parent_node
        self.method_node = method_node

        self.vlayout = QVBoxLayout(self)
        self._top_layout = QHBoxLayout()
        self.vlayout.addLayout(self._top_layout)
        self.inputs: list[QLineEdit] = []
        self.outputs: list[QLabel] = []

        self.vlayout.addWidget(QLabel("Input Arguments:", self))
        try:
            inputs = method_node.get_child("0:InputArguments")
            for arg in inputs.read_value():
                self._add_input(arg)
        except ua.UaError:
            logger.exception("Error reading input arguments")

        layout = QHBoxLayout()
        self.vlayout.addLayout(layout)
        layout.addWidget(QLabel("Result:", self))
        self.result_label = QLabel("None")
        layout.addWidget(self.result_label)

        self.vlayout.addWidget(QLabel("Output Arguments:", self))
        try:
            outputs = method_node.get_child("0:OutputArguments")
            for arg in outputs.read_value():
                self._add_output(arg)
        except ua.UaError:
            logger.exception("Error reading output arguments")

        layout = QHBoxLayout()
        self.vlayout.addLayout(layout)
        layout.addStretch()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)
        call_button = QPushButton("Call Method")
        call_button.clicked.connect(self.call)
        layout.addWidget(call_button)

    def call(self) -> None:
        try:
            self._call()
        except Exception as ex:
            logger.exception("Error calling method")
            self.result_label.setText(str(ex))

    def _call(self) -> None:
        args = []
        for inp in self.inputs:
            data_type: SyncNode = inp.data_type  # type: ignore[attr-defined]
            val = string_to_variant(inp.text(), data_type_to_variant_type(data_type))
            args.append(val)

        result = call_method_full(self.parent_node, self.method_node, *args)
        self.result_label.setText(str(result.StatusCode))

        for idx, res in enumerate(result.OutputArguments):
            self.outputs[idx].setText(val_to_string(res))

    def _add_input(self, arg: ua.Argument) -> None:
        layout = QHBoxLayout()
        self.vlayout.addLayout(layout)
        layout.addWidget(QLabel(f"Name:{arg.Name}", self))
        layout.addWidget(QLabel(f"Data type:{data_type_to_string(arg.DataType)}", self))
        layout.addWidget(QLabel(f"Description:{arg.Description.Text}", self))
        lineedit = QLineEdit(self)
        lineedit.data_type = self.server.get_node(arg.DataType)  # type: ignore[attr-defined]
        self.inputs.append(lineedit)
        layout.addWidget(lineedit)

    def _add_output(self, arg: ua.Argument) -> None:
        layout = QHBoxLayout()
        self.vlayout.addLayout(layout)
        layout.addWidget(QLabel(f"Data Type: {data_type_to_string(arg.DataType)}"))
        layout.addWidget(QLabel("Value:"))
        label = QLabel("", self)
        self.outputs.append(label)
        layout.addWidget(label)
