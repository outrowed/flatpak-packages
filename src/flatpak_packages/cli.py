"""Command-line interface for recipes in the current source checkout."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from urllib.error import URLError

from .recipes import RecipeError, find_recipe
from .workflow import WorkflowError, prepare, publish


def checkout(start: Path) -> Path:
    for path in (start, *start.parents):
        if (path / "pyproject.toml").is_file() and (path / "apps").is_dir():
            return path
    raise WorkflowError("Run from the flatpak-packages checkout or specify --root")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare and publish repository-owned Flatpak recipes"
    )
    parser.add_argument("--root", type=Path, help="path to the package recipe checkout")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser(
        "prepare", help="prepare a candidate without signing or publication"
    )
    build.add_argument("app_id")
    build.add_argument("--jobs", type=int, default=2)
    release = commands.add_parser(
        "publish", help="sign and import a reviewed candidate"
    )
    release.add_argument("app_id")
    release.add_argument("candidate", type=Path)
    release.add_argument("destination", type=Path)
    release.add_argument("key")
    args = parser.parse_args()
    try:
        root = (args.root or checkout(Path.cwd())).resolve(strict=True)
        recipe = find_recipe(root, args.app_id)
        if args.command == "prepare":
            prepare(root, recipe, args.jobs)
        else:
            publish(recipe, args.candidate, args.destination, args.key)
    except (
        RecipeError,
        WorkflowError,
        OSError,
        URLError,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0
