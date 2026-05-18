all:
	pyuic6 uaclient/mainwindow_ui.ui -o uaclient/mainwindow_ui.py
	pyuic6 uaclient/connection_ui.ui -o uaclient/connection_ui.py
	pyuic6 uaclient/applicationcertificate_ui.ui -o uaclient/applicationcertificate_ui.py
	pyside6-rcc uawidgets/resources.qrc -o uawidgets/resources.py
	sed -i 's/from PySide6 import QtCore/from PyQt6 import QtCore/' uawidgets/resources.py
run:
	PYTHONPATH=$(shell pwd)
	python3 app.py
edit:
	qtcreator uaclient/mainwindow_ui.ui
