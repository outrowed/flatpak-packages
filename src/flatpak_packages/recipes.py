"""Parse and validate the package recipes stored in the checkout."""

from __future__ import annotations

import hashlib
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


class RecipeError(ValueError):
    """A package recipe is missing or invalid."""


@dataclass(frozen=True)
class Recipe:
    app_id: str
    branch: str
    architecture: str
    related_refs: tuple[str, ...]
    source_type: str
    manifest: Path | None
    url: str | None
    sha256: str | None
    path: Path

    @property
    def app_ref(self) -> str:
        return f"app/{self.app_id}/{self.architecture}/{self.branch}"

    @property
    def allowed_refs(self) -> set[str]:
        return {self.app_ref, *self.related_refs}


def _string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise RecipeError(f"{name} must be a nonempty string")
    return value


def load_recipe(path: Path) -> Recipe:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise RecipeError(f"Cannot read recipe {path}: {exc}") from exc
    if set(data) - {"id", "branch", "architecture", "related_refs", "source"}:
        raise RecipeError(f"Unknown recipe keys in {path}")
    app_id = _string(data.get("id"), "id")
    branch = _string(data.get("branch"), "branch")
    arch = _string(data.get("architecture"), "architecture")
    if not re.fullmatch(
        r"[A-Za-z_][A-Za-z0-9_-]*(?:\.[A-Za-z_][A-Za-z0-9_-]*){2,}", app_id
    ):
        raise RecipeError(f"Invalid app ID: {app_id}")
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", branch) or not re.fullmatch(
        r"[A-Za-z0-9_]+", arch
    ):
        raise RecipeError("Invalid branch or architecture")
    raw_refs = data.get("related_refs", [])
    if not isinstance(raw_refs, list) or not all(
        isinstance(ref, str) for ref in raw_refs
    ):
        raise RecipeError("related_refs must be a list of strings")
    for ref in raw_refs:
        if not re.fullmatch(
            rf"(?:app|runtime)/{re.escape(app_id)}\.[A-Za-z0-9_.-]+/{re.escape(arch)}/{re.escape(branch)}",
            ref,
        ):
            raise RecipeError(f"Invalid related ref: {ref}")
    if len(set(raw_refs)) != len(raw_refs):
        raise RecipeError("Duplicate related refs")
    source = data.get("source")
    if not isinstance(source, dict):
        raise RecipeError("source must be a table")
    source_type = _string(source.get("type"), "source.type")
    manifest = None
    url = None
    digest = None
    if source_type == "manifest":
        if set(source) != {"type", "path"}:
            raise RecipeError("Manifest source requires only type and path")
        name = _string(source.get("path"), "source.path")
        manifest = (path.parent / name).resolve()
        if not manifest.is_relative_to(path.parent.resolve()) or not manifest.is_file():
            raise RecipeError(
                "Manifest must be an existing file inside the recipe directory"
            )
    elif source_type == "bundle":
        if set(source) != {"type", "url", "sha256"}:
            raise RecipeError("Bundle source requires only type, url and sha256")
        url = _string(source.get("url"), "source.url")
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise RecipeError("Bundle URL must be HTTPS without credentials")
        digest = _string(source.get("sha256"), "source.sha256")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise RecipeError(
                "Bundle SHA-256 must be 64 lowercase hexadecimal characters"
            )
    else:
        raise RecipeError(f"Unsupported source type: {source_type}")
    return Recipe(
        app_id,
        branch,
        arch,
        tuple(raw_refs),
        source_type,
        manifest,
        url,
        digest,
        path.resolve(),
    )


def find_recipe(root: Path, app_id: str) -> Recipe:
    matches = [
        recipe
        for path in sorted((root / "apps").glob("*/recipe.toml"))
        if (recipe := load_recipe(path)).app_id == app_id
    ]
    if len(matches) != 1:
        raise RecipeError(f"Expected one recipe for {app_id}; found {len(matches)}")
    return matches[0]


def recipe_digest(recipe: Recipe) -> str:
    """Fingerprint every regular file in a package recipe directory."""
    digest = hashlib.sha256()
    root = recipe.path.parent
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise RecipeError(
                f"Symlinks are not supported in recipe directories: {path}"
            )
        if path.is_file():
            name = path.relative_to(root).as_posix().encode("utf-8")
            content = path.read_bytes()
            digest.update(len(name).to_bytes(8, "big"))
            digest.update(name)
            digest.update(len(content).to_bytes(8, "big"))
            digest.update(content)
    return digest.hexdigest()
