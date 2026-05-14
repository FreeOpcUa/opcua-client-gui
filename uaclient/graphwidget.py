import logging
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QLabel

from asyncua import ua
from asyncua.sync import SyncNode

from uaclient.uaclient import UaClient
from uawidgets.utils import trycatchslot

if TYPE_CHECKING:
    from uaclient.mainwindow import Window

use_graph = True
try:
    import pyqtgraph as pg
    import numpy as np
except ImportError:
    print("pyqtgraph or numpy are not installed, use of graph feature disabled")
    use_graph = False

if use_graph:
    pg.setConfigOptions(antialias=True)
    pg.setConfigOption('background', 'w')
    pg.setConfigOption('foreground', 'k')

logger = logging.getLogger(__name__)


class GraphUI:

    # use tango color schema (public domain)
    colorCycle = ['#4e9a06ff', '#ce5c00ff', '#3465a4ff', '#75507bff', '#cc0000ff', '#edd400ff']
    acceptedDatatypes = ['Decimal128', 'Double', 'Float', 'Integer', 'UInteger']

    def __init__(self, window: "Window", uaclient: UaClient) -> None:
        self.window = window
        self.uaclient = uaclient

        if not use_graph:
            self.window.ui.graphLayout.addWidget(QLabel("pyqtgraph or numpy not installed"))
            return
        self._node_list: list[SyncNode] = []
        self._channels: list[Any] = []
        self._curves: list[Any] = []
        self.pw = pg.PlotWidget(name='Plot1')
        self.pw.showGrid(x=True, y=True, alpha=0.3)
        self.legend = self.pw.addLegend()
        self.window.ui.graphLayout.addWidget(self.pw)

        self.window.ui.actionAddToGraph.triggered.connect(self._add_node_to_channel)
        self.window.ui.actionRemoveFromGraph.triggered.connect(self._remove_node_from_channel)

        self.window.ui.treeView.addAction(self.window.ui.actionAddToGraph)
        self.window.ui.treeView.addAction(self.window.ui.actionRemoveFromGraph)

        self.window.ui.buttonApply.clicked.connect(self.restartTimer)
        self.restartTimer()

    def restartTimer(self) -> None:
        existing: QTimer | None = getattr(self, "timer", None)
        if existing is not None and existing.isActive():
            existing.stop()

        self.N: int = self.window.ui.spinBoxNumberOfPoints.value()
        self.ts = np.arange(self.N)
        self.intervall: int = self.window.ui.spinBoxIntervall.value() * 1000

        for i, _channel in enumerate(self._channels):
            self._channels[i] = np.zeros(self.N)
            self._curves[i].setData(self._channels[i])

        self.timer = QTimer()
        self.timer.setInterval(self.intervall)
        self.timer.timeout.connect(self.pushtoGraph)
        self.timer.start()

    @trycatchslot
    def _add_node_to_channel(self, node: SyncNode | None = None) -> None:
        if not isinstance(node, SyncNode):
            node = self.window.get_current_node()
            if node is None:
                return
        if node not in self._node_list:
            dtype = node.read_attribute(ua.AttributeIds.DataType)

            dtypeStr = ua.ObjectIdNames[dtype.Value.Value.Identifier]

            if dtypeStr in self.acceptedDatatypes and not isinstance(node.get_value(), list):
                self._node_list.append(node)
                displayName = node.read_display_name().Text
                colorIndex = len(self._node_list) % len(self.colorCycle)
                self._curves.append(
                    self.pw.plot(
                        pen=pg.mkPen(color=self.colorCycle[colorIndex], width=3, style=Qt.PenStyle.SolidLine),
                        name=displayName,
                    )
                )
                self._channels.append(np.zeros(self.N))
                self._curves[-1].setData(self._channels[-1])
                logger.info("Variable %s added to graph", displayName)

            else:
                logger.info("Variable cannot be added to graph because it is of type %s or an array", dtypeStr)

    @trycatchslot
    def _remove_node_from_channel(self, node: SyncNode | None = None) -> None:
        if not isinstance(node, SyncNode):
            node = self.window.get_current_node()
            if node is None:
                return
        if node in self._node_list:
            idx = self._node_list.index(node)
            self._node_list.pop(idx)
            displayName = node.read_display_name().Text
            self.legend.removeItem(displayName)
            self.pw.removeItem(self._curves[idx])
            self._curves.pop(idx)
            self._channels.pop(idx)

    def pushtoGraph(self) -> None:
        for i, node in enumerate(self._node_list):
            self._channels[i] = np.roll(self._channels[i], -1)
            self._channels[i][-1] = float(node.get_value())
            self._curves[i].setData(self.ts, self._channels[i])

    def clear(self) -> None:
        pass

    def show_error(self, *args: Any) -> None:
        self.window.show_error(*args)
