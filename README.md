# flatpak-packages

`flatpak-packages` is outrowed's personal collection of curated Flatpak applications. This repository contains the apps' recipes and supporting files, plus Python tools to prepare and sign their builds for an OSTree repository.

## Package collection

Each app lives under `apps/` with a `recipe.toml` and any package-specific manifest or upstream notes. The current collection includes:

- [BedrockOnLinux](apps/bedrock-on-linux/UPSTREAM.md), built from its upstream Flatpak Builder manifest.
- [Spotifast](apps/spotifast/UPSTREAM.md), imported from a pinned, checksum-verified upstream Flatpak bundle.

The recipe format supports manifest builds and pre-built bundle imports. See [Recipe files](docs/recipes.md) for the schema and validation rules.

## Tooling and development

The Python CLI reads recipes from this checkout and prepares candidate OSTree repositories. Manifest builds use Flatpak Builder and Flathub for SDK/runtime dependencies; bundle recipes download the pinned upstream artifact and verify its SHA-256 checksum.

### Prerequisites

To prepare packages, install the required tools and configure Flathub for the build user's Flatpak installation:

- Python 3.11 or newer and [`uv`](https://docs.astral.sh/uv/).
- Flatpak, Flatpak Builder, OSTree, GnuPG, and `elfutils`.
- A Linux host where Flatpak sandboxing and user namespaces work.

```sh
uv sync
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
```

### Prepare a candidate

Run the prepare command for the app you want to build or import:

```sh
uv run flatpak-packages prepare io.github.wyze3306.BedrockOnLinux
uv run flatpak-packages prepare rocks.spotifast.Spotifast
```

Each command prints a candidate directory under `.work/candidates/`. Review and test the candidate before publishing it.

### Run tests

Run the regression suite with:

```sh
uv run pytest
```

## Publishing and hosting

A Flatpak remote is a signed archive-mode OSTree repository served as ordinary static files. Its `.flatpakrepo` descriptor gives clients the HTTPS URL and public signing key. The Python tooling prepares candidates and signs their refs; a static web server such as Nginx or Caddy can serve the repository. Object storage or a CDN can also work if it preserves the repository paths and metadata.

### Stage and sign a release

After reviewing and testing a candidate, initialize a separate staging repository and publish the candidate using the repository signing key's full GPG fingerprint:

```sh
ostree --repo=/path/to/staging-repo init --mode=archive
uv run flatpak-packages publish APP_ID /path/to/candidate /path/to/staging-repo GPG_FINGERPRINT
```

The publish command imports and signs the selected app/runtime refs, then updates the repository summary. Keep the private signing key outside Git and away from the build host. Only its public key belongs in the descriptor:

```sh
GPG_FINGERPRINT=YOUR_FULL_GPG_FINGERPRINT
GPG_KEY=$(gpg --export "$GPG_FINGERPRINT" | base64 -w0)
cat > outrowed.flatpakrepo <<EOF
[Flatpak Repo]
Title=outrowed Flatpak Packages
Url=https://packages.example.org/repo/
Homepage=https://github.com/outrowed/flatpak-packages
GPGKey=$GPG_KEY
EOF
```

### Host the repository

Configure the web server to serve the complete repository directory over valid HTTPS. Flatpak clients need HTTP keep-alive and direct access to repository files, so do not put interactive login or browser-only bot challenges in front of downloads. Use authenticated deployment access and keep public client access read-only.

For production updates, publish to a staging copy, verify it from a clean Flatpak client, and only then promote it. Use a versioned directory and controlled switch or another atomic deployment method so clients cannot see a partially copied repository.

The collection is hosted at [`https://flatpak.taruna.me/`](https://flatpak.taruna.me/). Clients can add it and install packages with:

```sh
flatpak remote-add --user --if-not-exists outrowed-packages https://flatpak.taruna.me/flatpak-packages.flatpakrepo
flatpak install --user outrowed-packages io.github.wyze3306.BedrockOnLinux
flatpak install --user outrowed-packages rocks.spotifast.Spotifast
flatpak update --user
```

> **Current status:** Public static hosting and HTTPS client installs have been verified. The checked-in publish command modifies its destination in place, so use it for staging; production promotion and rollback are not automated yet.

See [Build and publication operations](docs/operations.md) for more deployment details. This project does not mirror Flathub; shared runtimes are obtained from Flathub during builds.

## License

The original Python tooling and recipe files authored by Taruna Prasetya are licensed under the MIT License; see [LICENSE](LICENSE) and [LICENSE.MIT](LICENSE.MIT). Each upstream application, manifest, and bundle retains its own license and redistribution terms. Review the package-specific upstream notes before distributing app-specific materials.
