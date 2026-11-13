from pathlib import Path

import pytest

from flatpak_packages.recipes import load_recipe


@pytest.fixture
def manifest_recipe(tmp_path: Path):
    directory = tmp_path / "apps" / "example"
    directory.mkdir(parents=True)
    (directory / "app.yml").write_text("app-id: org.example.App\n", encoding="utf-8")
    path = directory / "recipe.toml"
    path.write_text(
        'id = "org.example.App"\nbranch = "stable"\narchitecture = "x86_64"\n'
        'related_refs = ["runtime/org.example.App.Debug/x86_64/stable"]\n'
        '[source]\ntype = "manifest"\npath = "app.yml"\n',
        encoding="utf-8",
    )
    return load_recipe(path)
