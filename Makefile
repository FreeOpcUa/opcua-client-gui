all:
	pyuic5 mainwindow_ui.ui -o mainwindow_ui.py
run:
	python3 mainwindow.py
