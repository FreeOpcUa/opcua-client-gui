"""Release helper: bump version in pyproject.toml, tag, build and publish via uv."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path


PYPROJECT = Path("pyproject.toml")


def read_version() -> str:
    with PYPROJECT.open("rb") as f:
        return tomllib.load(f)["project"]["version"]


def write_version(new: str) -> None:
    text = PYPROJECT.read_text()
    new_text, n = re.subn(
        r'^(version\s*=\s*")[^"]+(")',
        rf"\g<1>{new}\g<2>",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if n != 1:
        sys.exit("could not locate version line in pyproject.toml")
    PYPROJECT.write_text(new_text)


def bump_version() -> str:
    old = read_version()
    parts = old.split(".")
    if len(parts) != 3 or not parts[-1].isdigit():
        sys.exit(f"non-trivial version {old!r}; bump manually")
    suggested = f"{parts[0]}.{parts[1]}.{int(parts[-1]) + 1}"
    print(f"Current version: {old}")
    ans = input(f"new version [{suggested}]: ").strip()
    new = ans or suggested
    write_version(new)
    return new


def ask(prompt: str) -> bool:
    return input(f"{prompt} (Y/n) ").strip().lower() in ("", "y", "yes")


def run(*cmd: str) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def release() -> None:
    v = bump_version()
    if not ask("commit and tag?"):
        return
    run("git", "add", "pyproject.toml")
    run("git", "commit", "-m", "new release")
    run("git", "tag", v)
    if ask("push to remote?"):
        run("git", "push")
        run("git", "push", "--tags")
    if ask("publish to PyPI?"):
        dist = Path("dist")
        if dist.exists():
            shutil.rmtree(dist)
        run("uv", "build")
        run("uv", "publish")


if __name__ == "__main__":
    release()
