Simple OPC-UA GUI client.

Written using freeopcua python api and pyside. Pull requests / Patches are welcome!

![Screenshot](/screenshot.png?raw=true "Screenshot")

What works:
* Connecting and disconnecting
* showing attributes and references
* subscribing to variable

TODO (listed after priority):
* remember connections and show connection history
* detect lost connection and automatically reconnect 
* more human friendly attributes and refs display
* subscribing to events
* make available on pip
* installer for windows

NOT PLANNED:
* support for certificates (need to be implemented in python-opcua)
* support for encryption (need to be implemented in python-opcua)


