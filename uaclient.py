
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

    def connect(self, uri):
        print("Connecting to ", uri)
        if self.client:
            self.client.disconnect()
        self.client = Client(uri)
        self.client.connect()
        print("Connected, root is: ", self.client.get_root_node())
        print(self.get_root_attrs())

    def disconnect(self):
        print("Disconnecting from server")
        self.client.disconnect()

    def browse(self, nodeid):
        """
        """
        pass

    def get_root_attrs(self):
        return self.get_node_attrs(self.client.get_root_node())

    def get_node_attrs(self, node):
        if not type(node) is Node:
            node = self.client.get_node(node)
        attrs = node.get_attributes([AttributeIds.DisplayName, AttributeIds.NodeId, AttributeIds.NodeClass])
        #return [dv.Value.Value for dv in attrs]
        vals =  [dv.Value.Value for dv in attrs]
        vals[0] = vals[0].Text
        return vals


