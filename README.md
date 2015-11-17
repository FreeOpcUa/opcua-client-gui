Simple OPC-UA GUI client.

Written using freeopcua python api and pyqt. This is alpha quality with strange window resizing happening. Pull requests / Patches are welcome!

![Screenshot](/screenshot.png?raw=true "Screenshot")

What works:
* Connecting and disconnecting
* showing attributes and references
* subscribing to variable
* make available on pip: sudo pip install freeopcua-client

TODO (listed after priority):
* remember connections and show connection history
* detect lost connection and automatically reconnect 
* more human friendly attributes and refs display
* subscribing to events
* installer for windows

NOT PLANNED:
* support for certificates (need to be implemented in python-opcua)
* support for encryption (need to be implemented in python-opcua)


