
from opcua import ua
from opcua import Client
from opcua import Node


class UaClient(object):
    """
    OPC-Ua client specialized for the need of GUI client
    return exactly whant GUI needs, no customization possible
    """

    def __init__(self):
        self.client = None
        self._connected = False
        self._datachange_sub = None
        self._event_sub = None
        self._subs_dc = {}
        self._subs_ev = {}

    def get_node(self, nodeid):
        return self.client.get_node(nodeid)

    def connect(self, uri):
        self.disconnect()
        print("Connecting to ", uri)
        self.client = Client(uri)
        self.client.connect()
        self._connected = True

    def disconnect(self):
        if self._connected:
            print("Disconnecting from server")
            self._subs_dc = {}
            self._subs_ev = {}
            self._connected = False
            self._subscription = None
            self.client.disconnect()
            self.client = None

    def subscribe_datachange(self, node, handler):
        if not self._datachange_sub:
            self._datachange_sub = self.client.create_subscription(500, handler)
        handle = self._datachange_sub.subscribe_data_change(node)
        self._subs_dc[node.nodeid] = handle
        return handle

    def unsubscribe_datachange(self, node):
        self._datachange_sub.unsubscribe(self._subs_dc[node.nodeid])

    def subscribe_events(self, node, handler):
        if not self._event_sub:
            print("subscirbing with handler: ", handler, dir(handler))
            self._event_sub = self.client.create_subscription(500, handler)
        handle = self._event_sub.subscribe_events(node)
        self._subs_ev[node.nodeid] = handle
        return handle

    def unsubscribe_events(self, node):
        self._event_sub.unsubscribe(self._subs_ev[node.nodeid])

    def get_node_attrs(self, node):
        if not isinstance(node, Node):
            node = self.client.get_node(node)
        attrs = node.get_attributes([ua.AttributeIds.DisplayName, ua.AttributeIds.BrowseName, ua.AttributeIds.NodeId])
        return node, [attr.Value.Value.to_string() for attr in attrs]

    def get_children(self, node):
        descs = node.get_children_descriptions()
        descs.sort(key=lambda x: x.BrowseName)
        return descs

