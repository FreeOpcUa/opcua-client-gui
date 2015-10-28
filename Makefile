all:
	pyuic5 freeopcuaclient/mainwindow_ui.ui -o freeopcuaclient/mainwindow_ui.py
run:
	python3 freeopcuaclient/mainwindow.py
edit:
	qtcreator freeopcuaclient/mainwindow_ui.ui
