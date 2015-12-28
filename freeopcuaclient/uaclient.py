
from opcua import ua
from opcua import Client
from opcua import Node
from opcua import AttributeIds
from opcua import ObjectIds


class UaClient(object):
    """
    OPC-Ua client specialized for the need of GUI client
    return exactly whant GUI needs, no customization possible
    """

    def __init__(self):
        self.client = None
        self._connected = False
        self._subscription = None
        self._subs = {}

    def connect(self, uri):
        self.disconnect()
        print("Connecting to ", uri)
        self.client = Client(uri)
        self.client.connect()
        self._connected = True

    def disconnect(self):
        if self._connected:
            print("Disconnecting from server")
            self._subs = {}
            self._connected = False
            self._subscription = None
            self.client.disconnect()
            self.client = None

    def subscribe(self, node, handler):
        if not self._subscription:
            self._subscription = self.client.create_subscription(500, handler)
        handle = self._subscription.subscribe_data_change(node)
        self._subs[node.nodeid] = handle
        return handle

    def unsubscribe(self, node):
        self._subscription.unsubscribe(self._subs[node.nodeid])

    def get_root_node_and_desc(self):
        node = self.client.get_root_node()
        attrs = node.get_attributes([AttributeIds.DisplayName, AttributeIds.BrowseName, AttributeIds.NodeId, AttributeIds.NodeClass])
        desc = ua.ReferenceDescription()
        desc.DisplayName = attrs[0].Value.Value
        desc.BrowseName = attrs[1].Value.Value
        desc.NodeId = attrs[2].Value.Value
        desc.NodeClass = attrs[3].Value.Value
        desc.TypeDefinition = ua.TwoByteNodeId(ua.ObjectIds.FolderType)
        return node, desc

    def get_node_attrs(self, node):
        if not isinstance(node, Node):
            node = self.client.get_node(node)
        attrs = node.get_attributes([AttributeIds.DisplayName, AttributeIds.BrowseName, AttributeIds.NodeId])
        return node, [attr.Value.Value.to_string() for attr in attrs]

    def get_children(self, node):
        descs = node.get_children_descriptions()
        children = []
        for desc in descs:
            children.append((self.client.get_node(desc.NodeId), desc))
        return children

    def get_all_attrs(self, node):
        names = []
        vals = []
        for name, val in ua.AttributeIds.__dict__.items():
            if not name.startswith("_"):
                names.append(name)
                vals.append(val)

        attrs = node.get_attributes(vals)
        res = {}
        for idx, name in enumerate(names):
            if attrs[idx].StatusCode.is_good():
                res[name] = attrs[idx].Value.Value
        return res

    def get_all_refs(self, node):
        return node.get_children_descriptions(refs=ObjectIds.References)
