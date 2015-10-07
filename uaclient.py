
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

    def connect(self, uri):
        self.disconnect()
        print("Connecting to ", uri)
        self.client = Client(uri)
        self.client.connect()
        self._connected = True
        print("Connected, root is: ", self.client.get_root_node())
        print(self.get_root_attrs())

    def disconnect(self):
        if self._connected:
            print("Disconnecting from server")
            self._connected = False
            self._subscription = None
            self.client.disconnect()
            self.client = None

    def subscribe(self, node, handler):
        if not self._subscription:
            self._subscription = self.client.create_subscription(500, handler)
        self._subscription.subscribe_data_change(node)

    def get_root_attrs(self):
        return self.get_node_attrs(self.client.get_root_node())

    def get_node_attrs(self, node):
        if not type(node) is Node:
            node = self.client.get_node(node)
        attrs = node.get_attributes([AttributeIds.DisplayName, AttributeIds.BrowseName, AttributeIds.NodeId])
        return [node] + [attr.Value.Value.to_string() for attr in attrs] 

    def get_children(self, node):
        descs = node.get_children_descriptions()
        children = []
        for desc in descs:
            children.append([self.client.get_node(desc.NodeId), desc.DisplayName.to_string(), desc.BrowseName.to_string(), desc.NodeId.to_string()])
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





