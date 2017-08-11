#! /usr/bin/env python3



import logging
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QLabel

from opcua import ua
from opcua import Node

from uawidgets.utils import trycatchslot

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


class GraphUI(object):

    # use tango color schema (public domain)
    colorCycle = ['#4e9a06ff', '#ce5c00ff', '#3465a4ff', '#75507bff', '#cc0000ff', '#edd400ff']
    acceptedDatatypes = ['Decimal128', 'Double', 'Float', 'Integer', 'UInteger']

    def __init__(self, window, uaclient):
        self.window = window
        self.uaclient = uaclient

        # exit if the modules are not present
        if not use_graph:
            self.window.ui.graphLayout.addWidget(QLabel("pyqtgraph or numpy not installed"))
            return
        self._node_list = [] # holds the nodes to poll
        self._channels = [] # holds the actual data
        self._curves = [] # holds the curve objects
        self.pw = pg.PlotWidget(name='Plot1')
        self.pw.showGrid(x = True, y = True, alpha = 0.3)
        self.legend = self.pw.addLegend()
        self.window.ui.graphLayout.addWidget(self.pw)

        self.window.ui.actionAddToGraph.triggered.connect(self._add_node_to_channel)
        self.window.ui.actionRemoveFromGraph.triggered.connect(self._remove_node_from_channel)

        # populate contextual menu
        self.window.ui.treeView.addAction(self.window.ui.actionAddToGraph)
        self.window.ui.treeView.addAction(self.window.ui.actionRemoveFromGraph)

        # connect Apply button
        self.window.ui.buttonApply.clicked.connect(self.restartTimer)
        self.restartTimer()


    def restartTimer(self):
        # stop current timer, if it exists
        if hasattr(self ,'timer') and self.timer.isActive():
            self.timer.stop()

        # define the number of polls displayed in graph
        self.N = self.window.ui.spinBoxNumberOfPoints.value()
        self.ts = np.arange(self.N)
        # define the poll intervall
        self.intervall = self.window.ui.spinBoxIntervall.value( ) *1000

        # overwrite current channel buffers with zeros of current length and add to curves again
        for i ,channel in enumerate(self._channels):
            self._channels[i] = np.zeros(self.N)
            self._curves[i].setData(self._channels[i])

        # starting new timer
        self.timer = QTimer()
        self.timer.setInterval(self.intervall)
        self.timer.timeout.connect(self.pushtoGraph)
        self.timer.start()

    @trycatchslot
    def _add_node_to_channel(self ,node=None):
        if not isinstance(node, Node):
            node = self.window.get_current_node()
            if node is None:
                return
        if node not in self._node_list:
            dtype = node.get_attribute(ua.AttributeIds.DataType)

            dtypeStr = ua.ObjectIdNames[dtype.Value.Value.Identifier]



            if dtypeStr in self.acceptedDatatypes and not isinstance(node.get_value() ,list):
                self._node_list.append(node)
                displayName = node.get_display_name().Text
                colorIndex = len(self._node_list) % len(self.colorCycle)
                self._curves.append \
                    (self.pw.plot(pen=pg.mkPen(color=self.colorCycle[colorIndex] ,width=3 ,style=Qt.SolidLine), name=displayName))
                # set initial data to zero
                self._channels.append(np.zeros(self.N)) # init data sequence with zeros
                # add the new channel data to the new curve
                self._curves[-1].setData(self._channels[-1])
                logger.info("Variable %s added to graph", displayName)

            else:
                logger.info("Variable cannot be added to graph because it is of type %s or an array", dtypeStr)


    @trycatchslot
    def _remove_node_from_channel(self ,node=None):
        if not isinstance(node, Node):
            node = self.window.get_current_node()
            if node is None:
                return
        if node in self._node_list:
            idx = self._node_list.index(node)
            self._node_list.pop(idx)
            displayName = node.get_display_name().Text
            self.legend.removeItem(displayName)
            self.pw.removeItem(self._curves[idx])
            self._curves.pop(idx)
            self._channels.pop(idx)


    def pushtoGraph(self):
        # ringbuffer: shift and replace last
        for i ,node in enumerate(self._node_list):
            self._channels[i] = np.roll(self._channels[i] ,-1) # shift elements to the left by one
            self._channels[i][-1] = float(node.get_value())
            self._curves[i].setData(self.ts ,self._channels[i])


    def clear(self):
        pass


    def show_error(self, *args):
        self.window.show_error(*args)
