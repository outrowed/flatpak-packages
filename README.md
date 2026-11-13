# flatpak-packages

`flatpak-packages` is outrowed's personal collection of curated Flatpak applications. The repository holds each package's recipe and supporting build files, along with Python tooling to prepare, validate, and sign builds for a personal Flatpak OSTree repository. It is both the package collection and the tools used to maintain it.

## Packages

Packages are added to this repository after their upstream source, license, sandbox permissions, and release process have been reviewed. Each app has a directory under `apps/` containing its `recipe.toml` and any package-specific manifests or notes.

The current collection includes:
- [BedrockOnLinux](apps/bedrock-on-linux/UPSTREAM.md), prepared from its upstream Flatpak Builder manifest.
- [Spotifast](apps/spotifast/UPSTREAM.md), prepared from a pinned, checksum-verified upstream Flatpak bundle.

The recipe format supports both source-manifest builds and upstream bundle imports. See [Recipe files](docs/recipes.md) for the schema and validation rules.

## Prepare a package

The Python CLI reads recipes from this repository and creates a candidate OSTree repository for review. Manifest builds use Flatpak Builder and the configured Flathub remote for SDK/runtime dependencies; bundle recipes download the pinned upstream artifact and verify its SHA-256 checksum.

Prerequisites are Python 3.11+, [`uv`](https://docs.astral.sh/uv/), Flatpak, Flatpak Builder, OSTree, GnuPG, `elfutils`, and Linux sandbox/user-namespace support.

```sh
uv sync
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
uv run flatpak-packages prepare io.github.wyze3306.BedrockOnLinux
uv run flatpak-packages prepare rocks.spotifast.Spotifast
```

The command prints the candidate directory under `.work/candidates/`. Inspect the candidate and test it on a client before publishing.

## Development and publishing

Run the test suite with `uv run pytest`. Recipes and helper functions are covered by tests; Ruff is used for linting and formatting.

After reviewing and testing a candidate, the CLI can import and sign its refs into an existing archive-mode OSTree repository:

```sh
uv run flatpak-packages publish APP_ID CANDIDATE DESTINATION GPG_KEY
```

See [Build and publication operations](docs/operations.md) for the candidate review and signing workflow. **Public repository hosting and safe production promotion are still in progress; the current publisher is for local test repositories and writes its destination in place.**

The long-term goal is to serve the curated collection as a Flatpak remote, so clients can install and update these apps using normal Flatpak commands. The repo does not mirror Flathub; shared runtimes are currently obtained from Flathub during builds.

The original Python tooling and recipe files authored by Taruna Prasetya are licensed under the MIT License; see [LICENSE](LICENSE) and [LICENSE.MIT](LICENSE.MIT). Each upstream application, manifest, and bundle retains its own license and redistribution terms. Review the package-specific upstream notes before distributing a build.
