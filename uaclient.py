
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
        #if self.client:
            #print("we are already connected, disconnecting from current server")
            #self.client.disconnect()
        print("Connecting to ", uri)
        self.client = Client(uri)
        self.client.connect()
        print("Connected, root is: ", self.client.get_root_node())
        print(self.get_root_attrs())

    def disconnect(self):
        if self.client:
            print("Disconnecting from server")
            self.client.disconnect()
            self.client = None

    def browse(self, nodeid):
        """
        """
        pass

    def get_root_attrs(self):
        return self.get_node_attrs(self.client.get_root_node())

    def get_node_attrs(self, node):
        if not type(node) is Node:
            node = self.client.get_node(node)
        attrs = node.get_attributes([AttributeIds.DisplayName, AttributeIds.NodeId, AttributeIds.BrowseName])
        #return [dv.Value.Value for dv in attrs]
        vals = [dv.Value.Value for dv in attrs]
        vals[0] = vals[0].Text
        return [node] + vals

    def get_children(self, node):
        descs = node.get_children_descriptions()
        children = []
        for desc in descs:
            children.append([self.client.get_node(desc.NodeId), desc.DisplayName.Text, desc.NodeId, desc.BrowseName])
        return children


