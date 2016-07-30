all:
	pyuic5 uaclient/mainwindow_ui.ui -o uaclient/mainwindow_ui.py
	pyrcc5 uaclient/resources.qrc -o uaclient/resources.py
run:
	PYTHONPATH=$(shell pwd)
	python3 app.py
edit:
	qtcreator uaclient/mainwindow_ui.ui
