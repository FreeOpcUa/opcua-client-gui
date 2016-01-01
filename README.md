Simple OPC-UA GUI client.

[![Scrutinizer Code Quality](https://scrutinizer-ci.com/g/FreeOpcUa/opcua-client-gui/badges/quality-score.png?b=master)](https://scrutinizer-ci.com/g/FreeOpcUa/opcua-client-gui/?branch=master)

Written using freeopcua python api and pyqt. Basic functionnalities are implemented including subscribing to nodes and listing attributes and references.


![Screenshot](/screenshot.png?raw=true "Screenshot")

What works:
* connecting and disconnecting
* browsing with icons per node types
* showing attributes and references
* subscribing to variable
* make available on pip: sudo pip install freeopcua-client
* remember connections and show connection history

TODO (listed after priority):

* detect lost connection and automatically reconnect 
* more human friendly attributes and refs display
* subscribing to events
* gui for certificates
* gui for encryption 


