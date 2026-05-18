# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- `make` — regenerates everything generated from Qt sources. `pyuic6` for the `.ui` files and `pyside6-rcc` for `uawidgets/resources.qrc`. The Makefile rewrites the rcc output's `from PySide6` import to `from PyQt6` (PyQt6 dropped `pyrcc6`; the binary resource format is framework-agnostic).
- `make run` — launches the app via `python3 app.py`.
- `make edit` — opens `mainwindow_ui.ui` in Qt Creator.
- `python3 tests.py` — runs the unittest suite. Tests spin up a real `asyncua` server on `opc.tcp://localhost:48400/freeopcua/server/` and drive the live `Window`, so a display is required. Headless runs work with `QT_QPA_PLATFORM=offscreen`. Run a single test with `python3 tests.py TestClient.test_select_objects`.
- `python3 release.py` — bumps `version` in `pyproject.toml`, tags, pushes, and runs `uv build` + `uv publish`.

## Architecture

This is a PyQt6 desktop OPC-UA client. The split between "Qt glue" and "OPC-UA logic" matters when making changes:

- **`app.py`** — entry point; delegates to `uaclient.mainwindow.main`. The `opcua-client` console script in `setup.py` points at the same `main`.
- **`uaclient/uaclient.py`** — `UaClient` is the only place that talks to `asyncua`. It wraps `asyncua.sync.Client` so the rest of the app stays on the Qt main thread. Security settings (mode, policy, user cert/key, application cert/key) are persisted per-URI via `QSettings`. Any new server-side capability should land here, not in the UI.
- **`uawidgets/`** — sibling package of `uaclient/`. Holds the reusable Qt widgets (`TreeWidget`, `AttrsWidget`, `RefsWidget`, the call-method dialog, the `QtHandler` log sink, and the `trycatchslot` decorator). Used to live in a separate `opcua-widgets` repo on PyPI; folded back into this project once the GUI was the only consumer.
- **`uaclient/mainwindow.py`** — the `Window` (a `QMainWindow`) wires `UaClient` to the widgets from `uawidgets`. Local sub-UIs live in this file as plain classes:
  - `DataChangeUI` / `DataChangeHandler` — subscription model for variable values.
  - `EventUI` / `EventHandler` — subscription model for events.
  - Both handlers emit `pyqtSignal`s with `Qt.QueuedConnection` so notifications arriving on the asyncua background thread are marshaled back to the Qt thread before touching models.
- **`uaclient/graphwidget.py`** — pyqtgraph-based live plot of subscribed variables.
- **`uaclient/connection_dialog.py`** + **`application_certificate_dialog.py`** — per-connection security config and application certificate config. Their `*_ui.py` siblings are generated; edit the `.ui` files and re-run `make`.
- **`uaclient/theme/`** — Breeze qrc-compiled stylesheets (`breeze_resources.py`); dark mode is toggled by `QSettings["dark_mode"]` and requires a restart.
- **`connection/`** — a separate Qt/C++ implementation of the connection dialog. Not built into the Python app; treat as reference only unless you're rebuilding that project.

### Generated files — do not hand-edit

`uaclient/mainwindow_ui.py`, `uaclient/connection_ui.py`, `uaclient/applicationcertificate_ui.py`, `uaclient/theme/breeze_resources.py`, and `uawidgets/resources.py` are produced by `make` from `.ui` / `.qrc` sources. Edit the source, then regenerate.

### State persistence

The app stores virtually all user state in `QSettings` under organization `FreeOpcUa`, application `OpcUaClient`: address history (`address_list`), last-browsed node per URI (`current_node`), window geometry/state, dark mode, and per-URI security settings. When changing settings keys, search for the string usage in `uaclient.py` and `mainwindow.py` together.

### External dependencies

Runtime deps are `asyncua` (>=2.0a0, needed for the auto-reconnect supervisor and Python 3.14 compatibility), `PyQt6`, `pyqtgraph`, and `numpy`. asyncua is currently consumed via a `[tool.uv.sources]` path source pointing at `../opcua-asyncio`.
