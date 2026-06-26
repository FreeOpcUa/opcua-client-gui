"""cx_Freeze build script that produces a Windows MSI installer.

Executed on the GitHub Actions ``windows-latest`` runner at release time, but can
also be run locally on Windows from the repository root:

    python packaging/msi_setup.py bdist_msi

The resulting installer is written to ``dist/``.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

from cx_Freeze import Executable, setup

ROOT = Path(__file__).resolve().parent.parent

with (ROOT / "pyproject.toml").open("rb") as f:
    VERSION = tomllib.load(f)["project"]["version"]

# Stable across releases so each MSI upgrades the previous install in place.
UPGRADE_CODE = "{6F2A1E84-3B5C-4D9E-A1F2-7C8B9D0E1A2B}"

build_exe_options = {
    "packages": ["uaclient", "uawidgets", "asyncua", "pyqtgraph", "numpy"],
    "excludes": ["tkinter", "test", "unittest"],
}

bdist_msi_options = {
    "upgrade_code": UPGRADE_CODE,
    "add_to_path": False,
    "initial_target_dir": r"[ProgramFilesFolder]\OPC-UA Client",
    "all_users": True,
}

executable = Executable(
    script=str(ROOT / "app.py"),
    base="gui" if sys.platform == "win32" else None,
    target_name="opcua-client",
    shortcut_name="OPC-UA Client",
    shortcut_dir="ProgramMenuFolder",
)

setup(
    name="opcua-client",
    version=VERSION,
    description="OPC-UA Client GUI",
    options={"build_exe": build_exe_options, "bdist_msi": bdist_msi_options},
    executables=[executable],
)
