all:
	pyuic5 uaclient/mainwindow_ui.ui -o uaclient/mainwindow_ui.py
	pyuic5 uaclient/connection_ui.ui -o uaclient/connection_ui.py
	pyrcc5 uawidgets/resources.qrc -o uawidgets/resources.py
run:
	PYTHONPATH=$(shell pwd)
	python3 app.py
edit:
	qtcreator uaclient/mainwindow_ui.ui
