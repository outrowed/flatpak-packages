import hashlib
import io
import json
import subprocess
from dataclasses import replace

import pytest

from flatpak_packages import workflow
from flatpak_packages.workflow import WorkflowError


class FakeOpener:
    def __init__(self, payload):
        self.payload = payload

    def open(self, request, timeout):
        assert request.full_url.startswith("https://")
        assert timeout == 60
        return io.BytesIO(self.payload)


def test_bundle_download_verifies_checksum(manifest_recipe, monkeypatch, tmp_path):
    payload = b"bundle contents"
    recipe = replace(
        manifest_recipe,
        url="https://example.com/test.flatpak",
        sha256=hashlib.sha256(payload).hexdigest(),
    )
    monkeypatch.setattr(workflow, "build_opener", lambda *_: FakeOpener(payload))
    target = tmp_path / "bundle.flatpak"
    workflow.download_bundle(recipe, target)
    assert target.read_bytes() == payload
    with pytest.raises(WorkflowError, match="SHA-256"):
        workflow.download_bundle(
            replace(recipe, sha256="0" * 64), tmp_path / "bad.flatpak"
        )


def test_rejects_http_redirect():
    handler = workflow.HTTPSRedirectHandler()
    with pytest.raises(WorkflowError, match="HTTPS"):
        handler.redirect_request(None, None, 302, "", {}, "http://example.com/a")


def test_prepare_manifest_records_candidate(manifest_recipe, tmp_path, monkeypatch):
    calls = []
    ref = manifest_recipe.app_ref

    def fake_run(*args, capture=False):
        calls.append(args)
        if args[0] == "git":
            return "a" * 40 if "rev-parse" in args else ""
        if args[0] == "flatpak-builder":
            return ""
        if args[-1] == "refs":
            return ref
        if "rev-parse" in args:
            return "b" * 64
        raise AssertionError(args)

    monkeypatch.setattr(workflow, "run", fake_run)
    candidate = workflow.prepare(tmp_path, manifest_recipe, 2)
    record = json.loads((candidate / "candidate.json").read_text())
    assert record["refs"] == {ref: "b" * 64}
    assert record["source_revision"] == "a" * 40
    assert not record["recipe_tree_dirty"]
    builder = next(args for args in calls if args[0] == "flatpak-builder")
    assert {
        "--sandbox",
        "--disable-rofiles-fuse",
        "--default-branch=stable",
        "--jobs=2",
    } <= set(builder)


def test_prepare_failed_builder_has_no_candidate_record(
    manifest_recipe, tmp_path, monkeypatch
):
    def fail(*args, capture=False):
        if args[0] == "git":
            return "a" * 40 if "rev-parse" in args else ""
        raise subprocess.CalledProcessError(1, args)

    monkeypatch.setattr(workflow, "run", fail)
    with pytest.raises(subprocess.CalledProcessError):
        workflow.prepare(tmp_path, manifest_recipe, 2)
    assert not list((tmp_path / ".work" / "candidates").glob("*/candidate.json"))


def test_prepare_rejects_zero_jobs(manifest_recipe, tmp_path):
    with pytest.raises(WorkflowError, match="at least one"):
        workflow.prepare(tmp_path, manifest_recipe, 0)
