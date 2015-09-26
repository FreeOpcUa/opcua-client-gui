all:
	pyside-uic uaclient_ui.ui -o uaclient_ui.py
run:
	python3 uaclient.py
