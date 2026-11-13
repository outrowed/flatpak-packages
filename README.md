# flatpak-packages

`flatpak-packages` is outrowed's personal collection of curated Flatpak applications. The repository keeps app recipes and supporting files together with the Python tools used to prepare, validate, and sign their builds. The intended destination is outrowed's own Flatpak OSTree repository.

## Packages

Each app lives in its own directory under `apps/`, with a `recipe.toml` and any package-specific manifests or upstream notes. The collection currently includes:

- [BedrockOnLinux](apps/bedrock-on-linux/UPSTREAM.md), built from its upstream Flatpak Builder manifest.
- [Spotifast](apps/spotifast/UPSTREAM.md), imported from a pinned, checksum-verified upstream Flatpak bundle.

The recipe format supports manifest builds and pre-built bundle imports. See [Recipe files](docs/recipes.md) for the schema and validation rules.

## Prepare a package

The Python CLI reads recipes from this repository and prepares a candidate OSTree repository for review. Manifest builds use Flatpak Builder and Flathub for SDK/runtime dependencies; bundle recipes download the pinned upstream artifact and verify its SHA-256 checksum.

To prepare a candidate, install the required tools, configure Flathub for the build user's Flatpak installation, and run the command for the package:

- Python 3.11 or newer and [`uv`](https://docs.astral.sh/uv/).
- Flatpak, Flatpak Builder, OSTree, GnuPG, and `elfutils`.
- A Linux host where Flatpak sandboxing and user namespaces work.

```sh
uv sync
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
uv run flatpak-packages prepare io.github.wyze3306.BedrockOnLinux
```

To prepare the bundled Spotifast release instead, run:

```sh
uv run flatpak-packages prepare rocks.spotifast.Spotifast
```

Each command prints a candidate directory under `.work/candidates/`. Review and test the candidate before publishing it.

## Development and publishing

The Python project provides two commands for the package workflow:

- `flatpak-packages prepare APP_ID` builds from the app's manifest or imports its pinned bundle, then records the candidate refs and recipe digest.
- `flatpak-packages publish APP_ID CANDIDATE DESTINATION GPG_KEY` validates a reviewed candidate, imports and signs its refs, and updates the destination OSTree repository's summary metadata.

Run the regression suite with `uv run pytest`. See [Build and publication operations](docs/operations.md) for candidate review and signing guidance.

The long-term goal is to serve this curated collection as a Flatpak remote, allowing clients to install and update apps through normal Flatpak commands. This project does not mirror Flathub; shared runtimes are currently obtained from Flathub during builds.

## Copyright

The original Python tooling and recipe files authored by Taruna Prasetya are licensed under the MIT License; see [LICENSE](LICENSE) and [LICENSE.MIT](LICENSE.MIT). Each upstream application, manifest, and bundle retains its own license and redistribution terms. Review the package-specific upstream notes before distributing app-specific materials.
