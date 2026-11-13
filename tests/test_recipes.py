from dataclasses import replace

import pytest

from flatpak_packages.recipes import (
    RecipeError,
    find_recipe,
    load_recipe,
    recipe_digest,
)


def test_manifest_recipe_and_expected_refs(manifest_recipe):
    assert manifest_recipe.app_ref == "app/org.example.App/x86_64/stable"
    assert manifest_recipe.allowed_refs == {
        "app/org.example.App/x86_64/stable",
        "runtime/org.example.App.Debug/x86_64/stable",
    }


def test_recipe_directory_fingerprint_covers_extra_files(manifest_recipe):
    before = recipe_digest(manifest_recipe)
    (manifest_recipe.path.parent / "fix.patch").write_text("patch", encoding="utf-8")
    assert recipe_digest(manifest_recipe) != before


def test_recipe_rejects_symlinks(manifest_recipe, tmp_path):
    (manifest_recipe.path.parent / "link").symlink_to(tmp_path)
    with pytest.raises(RecipeError, match="Symlinks"):
        recipe_digest(manifest_recipe)


def test_rejects_manifest_outside_recipe(manifest_recipe):
    path = manifest_recipe.path
    path.write_text(path.read_text().replace('"app.yml"', '"../../outside.yml"'))
    with pytest.raises(RecipeError, match="inside the recipe"):
        load_recipe(path)


def test_missing_and_duplicate_app_ids(manifest_recipe, tmp_path):
    with pytest.raises(RecipeError, match="found 0"):
        find_recipe(tmp_path, "org.example.Missing")
    other = tmp_path / "apps" / "other"
    other.mkdir()
    (other / "app.yml").write_text("source", encoding="utf-8")
    (other / "recipe.toml").write_text(
        manifest_recipe.path.read_text(), encoding="utf-8"
    )
    with pytest.raises(RecipeError, match="found 2"):
        find_recipe(tmp_path, manifest_recipe.app_id)


@pytest.mark.parametrize(
    "url", ["http://example.com/a", "https://user:pass@example.com/a"]
)
def test_bundle_url_requires_https_without_credentials(manifest_recipe, url):
    path = manifest_recipe.path
    path.write_text(
        'id = "org.example.App"\nbranch = "stable"\narchitecture = "x86_64"\n'
        f'[source]\ntype = "bundle"\nurl = "{url}"\nsha256 = "{"a" * 64}"\n'
    )
    with pytest.raises(RecipeError, match="HTTPS"):
        load_recipe(path)


def test_bundle_checksum_format(manifest_recipe):
    path = manifest_recipe.path
    path.write_text(
        'id = "org.example.App"\nbranch = "stable"\narchitecture = "x86_64"\n'
        '[source]\ntype = "bundle"\nurl = "https://example.com/a"\nsha256 = "bad"\n'
    )
    with pytest.raises(RecipeError, match="SHA-256"):
        load_recipe(path)


def test_recipe_rejects_unexpected_related_ref(manifest_recipe):
    path = manifest_recipe.path
    path.write_text(path.read_text().replace("org.example.App.Debug", "org.other.App"))
    with pytest.raises(RecipeError, match="Invalid related ref"):
        load_recipe(path)


def test_recipe_digest_changes_with_manifest(manifest_recipe):
    old = recipe_digest(manifest_recipe)
    manifest_recipe.manifest.write_text("changed", encoding="utf-8")
    assert old != recipe_digest(replace(manifest_recipe))


@pytest.mark.parametrize("branch", ["..", ".", "-option", "bad/branch"])
def test_rejects_invalid_branches(manifest_recipe, branch):
    path = manifest_recipe.path
    path.write_text(
        path.read_text().replace('branch = "stable"', f'branch = "{branch}"')
    )
    with pytest.raises(RecipeError, match="Invalid branch"):
        load_recipe(path)
