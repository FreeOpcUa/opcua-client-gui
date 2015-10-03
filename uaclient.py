
from opcua import ua
from opcua import Client
from opcua import Node
from opcua import AttributeIds
from opcua import ObjectIds

from IPython import embed



class UaClient(object):
    """
    OPC-Ua client specialized for the need of GUI client
    return exactly whant GUI needs, no customization possible
    """
    def __init__(self):
        self.client = None
        self._connected = False

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
            self.client.disconnect()
            self.client = None

    def get_root_attrs(self):
        return self.get_node_attrs(self.client.get_root_node())

    def get_node_attrs(self, node):
        if not type(node) is Node:
            node = self.client.get_node(node)
        attrs = node.get_attributes([AttributeIds.BrowseName, AttributeIds.NodeId])
        #return [dv.Value.Value for dv in attrs]
        vals = [dv.Value.Value.to_string() for dv in attrs]
        #vals[0] = vals[0].to_string()
        return [node] + vals

    def get_children(self, node):
        descs = node.get_children_descriptions()
        children = []
        for desc in descs:
            children.append([self.client.get_node(desc.NodeId), desc.BrowseName.to_string(), desc.NodeId.to_string()])
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





