"""Prepare isolated candidates and publish reviewed refs to an OSTree repository."""

from __future__ import annotations

import fcntl
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .recipes import Recipe, recipe_digest


class WorkflowError(RuntimeError):
    """A candidate or publishing operation failed validation."""


def run(*args: str, capture: bool = False) -> str:
    result = subprocess.run(
        args, check=True, text=True, stdout=subprocess.PIPE if capture else None
    )
    return result.stdout.strip() if capture else ""


def repository_refs(repo: Path) -> dict[str, str]:
    refs = run("ostree", f"--repo={repo}", "refs", capture=True).splitlines()
    output = {}
    for ref in refs:
        if ref.startswith(("app/", "runtime/")):
            output[ref] = run(
                "ostree", f"--repo={repo}", "rev-parse", ref, capture=True
            )
    return output


def validate_refs(recipe: Recipe, refs: dict[str, str]) -> None:
    if recipe.app_ref not in refs:
        raise WorkflowError(
            f"Candidate is missing expected application ref: {recipe.app_ref}"
        )
    unexpected = set(refs) - recipe.allowed_refs
    if unexpected:
        raise WorkflowError(
            f"Unexpected refs in candidate: {', '.join(sorted(unexpected))}"
        )
    if not all(
        len(commit) == 64 and all(c in "0123456789abcdef" for c in commit)
        for commit in refs.values()
    ):
        raise WorkflowError("Invalid OSTree commit checksum")


class HTTPSRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme != "https":
            raise WorkflowError("Bundle redirects must use HTTPS")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_bundle(recipe: Recipe, destination: Path) -> None:
    assert recipe.url is not None and recipe.sha256 is not None
    request = Request(recipe.url, headers={"User-Agent": "flatpak-packages/0.1"})
    digest = hashlib.sha256()
    opener = build_opener(HTTPSRedirectHandler())
    with opener.open(request, timeout=60) as response, destination.open("xb") as output:
        while chunk := response.read(1024 * 1024):
            digest.update(chunk)
            output.write(chunk)
    if digest.hexdigest() != recipe.sha256:
        raise WorkflowError("Downloaded bundle SHA-256 does not match recipe")


def prepare(root: Path, recipe: Recipe, jobs: int) -> Path:
    if jobs < 1:
        raise WorkflowError("Build jobs must be at least one")
    source_digest = recipe_digest(recipe)
    revision = run("git", "-C", str(root), "rev-parse", "HEAD", capture=True)
    dirty = bool(
        run(
            "git",
            "-C",
            str(root),
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            "apps",
            capture=True,
        )
    )
    candidates = root / ".work" / "candidates"
    candidates.mkdir(parents=True, exist_ok=True)
    candidate = Path(tempfile.mkdtemp(prefix=f"{recipe.app_id}.", dir=candidates))
    repo = candidate / "repo"
    print(f"Candidate: {candidate}", flush=True)
    if recipe.source_type == "manifest":
        assert recipe.manifest is not None
        state = root / ".work" / "state" / recipe.app_id
        state.mkdir(parents=True, exist_ok=True)
        run(
            "flatpak-builder",
            "--sandbox",
            "--disable-rofiles-fuse",
            "--user",
            "--install-deps-from=flathub",
            f"--default-branch={recipe.branch}",
            f"--arch={recipe.architecture}",
            f"--jobs={jobs}",
            f"--state-dir={state}",
            f"--repo={repo}",
            str(candidate / "build"),
            str(recipe.manifest),
        )
    else:
        bundle = candidate / "source.flatpak"
        download_bundle(recipe, bundle)
        run("ostree", f"--repo={repo}", "init", "--mode=archive")
        run("flatpak", "build-import-bundle", str(repo), str(bundle))
    refs = repository_refs(repo)
    validate_refs(recipe, refs)
    if source_digest != recipe_digest(recipe):
        raise WorkflowError("Recipe or manifest changed during preparation")
    record = {
        "app_id": recipe.app_id,
        "recipe_digest": source_digest,
        "source_revision": revision,
        "recipe_tree_dirty": dirty,
        "refs": refs,
    }
    (candidate / "candidate.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Candidate prepared: {candidate}")
    return candidate


def publish(recipe: Recipe, candidate: Path, destination: Path, key: str) -> None:
    candidate = candidate.resolve(strict=True)
    destination = destination.resolve(strict=True)
    repo = (candidate / "repo").resolve(strict=True)
    if not key or key.startswith("-"):
        raise WorkflowError("A GPG signing key ID is required")
    if repo == destination or not (destination / "config").is_file():
        raise WorkflowError("Destination must be a distinct existing OSTree repository")
    mode = run(
        "ostree", f"--repo={destination}", "config", "get", "core.mode", capture=True
    )
    if mode not in {"archive", "archive-z2"}:
        raise WorkflowError("Destination must use archive mode")
    try:
        record = json.loads((candidate / "candidate.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"Cannot read candidate record: {exc}") from exc
    if not isinstance(record, dict) or record.get("app_id") != recipe.app_id:
        raise WorkflowError("Candidate does not match recipe")
    if record.get("recipe_digest") != recipe_digest(recipe):
        raise WorkflowError("Recipe or manifest changed since preparation")
    with (destination / ".publish.lock").open("a", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise WorkflowError("Another publication is in progress") from exc
        refs = repository_refs(repo)
        validate_refs(recipe, refs)
        if record.get("refs") != refs:
            raise WorkflowError("Candidate refs changed since preparation")
        for ref, commit in sorted(refs.items()):
            run(
                "flatpak",
                "build-commit-from",
                "--untrusted",
                "--no-update-summary",
                f"--gpg-sign={key}",
                f"--src-repo={repo}",
                f"--src-ref={commit}",
                str(destination),
                ref,
            )
        run(
            "flatpak",
            "build-update-repo",
            "--title=Taruna Flatpak Packages",
            "--default-branch=stable",
            f"--gpg-sign={key}",
            str(destination),
        )
    print("Repository updated. Verify it with an independent Flatpak client.")
