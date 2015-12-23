all:
	pyuic5 freeopcuaclient/mainwindow_ui.ui -o freeopcuaclient/mainwindow_ui.py
	pyrcc5 freeopcuaclient/resources.qrc -o freeopcuaclient/resources.py
run:
	PYTHONPATH=$(shell pwd)
	python3 app.py
edit:
	qtcreator freeopcuaclient/mainwindow_ui.ui
