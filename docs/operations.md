# Build and publication operations

This checkout contains package recipes and a Python CLI for preparing, reviewing,
and publishing Flatpaks. Git changes do not automatically build or publish apps.

The publish command supports local test repositories. Public deployment and
atomic publication are not yet implemented.

## Setup

Use Python 3.11 or newer with `uv`, Flatpak, Flatpak Builder, OSTree, `elfutils`,
and GnuPG. The build host must support Flatpak's sandbox and user namespaces.
Keep the signing key separate from the build environment.

```sh
uv sync
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
```

Run the regression suite with `uv run pytest`.

## Prepare

Each `apps/*/recipe.toml` defines an application ID, branch, architecture, and
source. Manifest recipes build with Flatpak Builder; bundle recipes download and
verify the pinned upstream release before importing it. Recipes and manifests
remain in this checkout, while candidates are stored under `.work/candidates/`.

```sh
uv run flatpak-packages prepare io.github.wyze3306.BedrockOnLinux
uv run flatpak-packages prepare rocks.spotifast.Spotifast
```

The command prints the candidate path and records its refs, recipe digest, Git
revision, and whether the recipe tree was dirty. Review the source, license,
permissions, and candidate record; test installation and launch before signing.
Use `--jobs` to set manifest build concurrency (default: 2).

## Sign and publish

Use a dedicated GPG key and keep its private material outside Git, the web root,
and the build environment. Back up the key and verify its fingerprint.

Initialize a new archive-mode local test repository:

```sh
ostree --repo=/absolute/path/to/test/repo init --mode=archive
```

Publish the reviewed candidate using its path and the signing key fingerprint:

```sh
uv run flatpak-packages publish APP_ID /absolute/path/to/candidate /absolute/path/to/test/repo FINGERPRINT
```

The command checks the current recipe and candidate refs against the recorded
values, signs the selected commits, and updates AppStream and summary metadata.
The candidate and key must be available on the publishing machine. Publishing
modifies the destination in place; do not use it on a live repository.

A public release still requires a `.flatpakrepo` with the public key, HTTPS
hosting without browser challenges, and client install and update verification.

Reference: <https://docs.flatpak.org/en/latest/hosting-a-repository.html>
