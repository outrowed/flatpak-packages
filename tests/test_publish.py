import fcntl
import json
import subprocess

import pytest

from flatpak_packages import workflow
from flatpak_packages.recipes import recipe_digest
from flatpak_packages.workflow import WorkflowError


@pytest.fixture
def candidate(manifest_recipe, tmp_path):
    candidate = tmp_path / "candidate"
    (candidate / "repo").mkdir(parents=True)
    destination = tmp_path / "destination"
    destination.mkdir()
    (destination / "config").touch()
    refs = {
        manifest_recipe.app_ref: "a" * 64,
        manifest_recipe.related_refs[0]: "b" * 64,
    }
    (candidate / "candidate.json").write_text(
        json.dumps(
            {
                "app_id": manifest_recipe.app_id,
                "recipe_digest": recipe_digest(manifest_recipe),
                "refs": refs,
            }
        )
    )
    return candidate, destination, refs


@pytest.fixture
def commands(monkeypatch):
    calls = []

    def fake_run(*args, capture=False):
        calls.append(args)
        if args[-2:] == ("get", "core.mode"):
            return "archive-z2"
        return ""

    monkeypatch.setattr(workflow, "run", fake_run)
    return calls


def test_publish_signs_only_recorded_refs(
    manifest_recipe, candidate, commands, monkeypatch
):
    source, destination, refs = candidate
    monkeypatch.setattr(workflow, "repository_refs", lambda _: refs)
    workflow.publish(manifest_recipe, source, destination, "test-key")
    imports = [call for call in commands if "build-commit-from" in call]
    assert len(imports) == 2
    for call in imports:
        assert "--untrusted" in call
        assert "--no-update-summary" in call
        assert "--gpg-sign=test-key" in call
        assert f"--src-ref={refs[call[-1]]}" in call
    assert any(
        "build-update-repo" in call and "--gpg-sign=test-key" in call
        for call in commands
    )


def test_rejects_changed_candidate_refs(
    manifest_recipe, candidate, commands, monkeypatch
):
    source, destination, refs = candidate
    monkeypatch.setattr(
        workflow,
        "repository_refs",
        lambda _: {**refs, manifest_recipe.app_ref: "c" * 64},
    )
    with pytest.raises(WorkflowError, match="refs changed"):
        workflow.publish(manifest_recipe, source, destination, "test-key")
    assert not any("build-commit-from" in call for call in commands)


def test_rejects_unexpected_ref(manifest_recipe, candidate, commands, monkeypatch):
    source, destination, refs = candidate
    monkeypatch.setattr(
        workflow,
        "repository_refs",
        lambda _: {**refs, "app/org.other.App/x86_64/stable": "c" * 64},
    )
    with pytest.raises(WorkflowError, match="Unexpected refs"):
        workflow.publish(manifest_recipe, source, destination, "test-key")


def test_rejects_changed_recipe(manifest_recipe, candidate, commands):
    source, destination, _ = candidate
    manifest_recipe.manifest.write_text("modified")
    with pytest.raises(WorkflowError, match="changed since preparation"):
        workflow.publish(manifest_recipe, source, destination, "test-key")


def test_rejects_non_archive_destination(manifest_recipe, candidate, monkeypatch):
    source, destination, _ = candidate
    monkeypatch.setattr(workflow, "run", lambda *args, **kwargs: "bare")
    with pytest.raises(WorkflowError, match="archive mode"):
        workflow.publish(manifest_recipe, source, destination, "test-key")


def test_rejects_same_candidate_and_destination(manifest_recipe, candidate):
    source, _, _ = candidate
    (source / "repo" / "config").touch()
    with pytest.raises(WorkflowError, match="distinct"):
        workflow.publish(manifest_recipe, source, source / "repo", "test-key")


def test_rejects_concurrent_publish(manifest_recipe, candidate, commands):
    source, destination, _ = candidate
    with (destination / ".publish.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(WorkflowError, match="Another publication"):
            workflow.publish(manifest_recipe, source, destination, "test-key")


def test_import_failure_prevents_summary_update(
    manifest_recipe, candidate, monkeypatch
):
    source, destination, refs = candidate
    calls = []

    def fake_run(*args, capture=False):
        calls.append(args)
        if args[-2:] == ("get", "core.mode"):
            return "archive-z2"
        raise subprocess.CalledProcessError(1, args)

    monkeypatch.setattr(workflow, "run", fake_run)
    monkeypatch.setattr(workflow, "repository_refs", lambda _: refs)
    with pytest.raises(subprocess.CalledProcessError):
        workflow.publish(manifest_recipe, source, destination, "test-key")
    assert not any("build-update-repo" in call for call in calls)


def test_ref_enumeration_failure_is_not_ignored(
    manifest_recipe, candidate, commands, monkeypatch
):
    source, destination, _ = candidate

    def fail(_):
        raise subprocess.CalledProcessError(1, "ostree")

    monkeypatch.setattr(workflow, "repository_refs", fail)
    with pytest.raises(subprocess.CalledProcessError):
        workflow.publish(manifest_recipe, source, destination, "test-key")


def test_rejects_missing_app_ref(manifest_recipe, candidate, commands, monkeypatch):
    source, destination, refs = candidate
    refs.pop(manifest_recipe.app_ref)
    monkeypatch.setattr(workflow, "repository_refs", lambda _: refs)
    with pytest.raises(WorkflowError, match="missing expected application ref"):
        workflow.publish(manifest_recipe, source, destination, "test-key")


def test_rejects_invalid_commit_id(manifest_recipe, candidate, commands, monkeypatch):
    source, destination, refs = candidate
    refs[manifest_recipe.app_ref] = "not-a-checksum"
    monkeypatch.setattr(workflow, "repository_refs", lambda _: refs)
    with pytest.raises(WorkflowError, match="Invalid OSTree commit"):
        workflow.publish(manifest_recipe, source, destination, "test-key")
