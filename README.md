simple OPC-UA GUI client.

Written using freeopcua python api and pyside. Pull requests / Patches are welcome!

![Screenshot](/screenshot.png?raw=true "Screenshot")

What works:
* Connecting and disconnecting
* showing attributes and references
* catch and display some errors

TODO (listed after priority):
* catch and display all errors in UI
* more human friendly attributes and refs display
* subscribing to variable
* subscribing to events
* remember connections and show history
* make available on pip
* login with user (need UI change)
* improve UI
* installer for windows

NOT PLANNED:
* support for certificates (need to be implemented in python-opcua)
* support for encryption (need to be implemented in python-opcua)


