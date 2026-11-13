# Package recipes

Each package in this repository is defined by a `recipe.toml` file located in
its own directory under `apps/<name>/`. The recipe declares the application
identity, the target architecture and branch, any permitted auxiliary refs, and
the upstream source used to prepare candidate Flatpak builds.

Recipes remain committed to Git alongside any companion packaging files, such
as Flatpak manifests and license files. Binary artifacts, downloads, and build
caches are never committed and reside in `.work/` during execution.

## Recipe structure

A recipe is a TOML document containing top-level package metadata and a single
`[source]` table. Unknown top-level keys or source fields are rejected during
validation.

The top-level table defines the expected package identity:

- The `id` field specifies the reverse-DNS Flatpak application ID, such as
  `io.github.wyze3306.BedrockOnLinux` or `rocks.spotifast.Spotifast`. It must
  contain at least three period-separated segments.
- The `branch` field defines the OSTree branch name, commonly `stable` or
  `master`. It must start with an alphanumeric character or underscore and may
  contain periods, hyphens, and underscores.
- The `architecture` field specifies the target CPU architecture, such as
  `x86_64`.
- The optional `related_refs` list specifies auxiliary application or runtime
  refs that the candidate build is permitted to export, such as debug symbols or
  locale extensions. Every entry must belong to the same application ID,
  architecture, and branch.

The combination of `id`, `architecture`, and `branch` determines the primary
application ref: `app/<id>/<architecture>/<branch>`.

## Source types

The `[source]` table specifies how candidate Flatpak artifacts are obtained or
assembled. Two source types are supported: `manifest` and `bundle`.

### Manifest sources

A manifest source instructs the tooling to build the package from source or raw
components using `flatpak-builder`:

```toml
id = "io.github.wyze3306.BedrockOnLinux"
branch = "stable"
architecture = "x86_64"
related_refs = [
    "runtime/io.github.wyze3306.BedrockOnLinux.Debug/x86_64/stable",
]

[source]
type = "manifest"
path = "io.github.wyze3306.BedrockOnLinux.yml"
```

The `path` field points to a Flatpak Builder manifest file stored in the same
recipe directory. The file must exist and cannot escape the recipe directory via
relative path traversal.

### Bundle sources

A bundle source instructs the tooling to import a pre-built upstream `.flatpak`
single-file bundle rather than compiling from source:

```toml
id = "rocks.spotifast.Spotifast"
branch = "master"
architecture = "x86_64"

[source]
type = "bundle"
url = "https://github.com/crmne/spotifast/releases/download/v0.17.0/spotifast-v0.17.0-x86_64.flatpak"
sha256 = "30537c5105dfc3145294f61b9d88a9bf09d58addec3ba1b490087e7c35c44cfd"
```

The `url` field specifies an HTTPS download URL without embedded user
credentials. The `sha256` field specifies the expected cryptographic digest as
64 lowercase hexadecimal characters.

The bundle's internal branch must match the recipe's declared `branch` exactly.
Flatpak bundles cannot be renamed or retargeted to another branch on import;
the recipe must declare whatever branch upstream used when building the bundle.

## Validation and consistency guarantees

Recipes enforce strict validation during candidate preparation and publication:

- Strict ref boundaries ensure that candidate repositories only contain the
  primary application ref and explicitly allowed `related_refs`. Any unexpected
  application or runtime ref halts the pipeline.
- Directory digests fingerprint all regular files inside the recipe directory,
  including manifests and auxiliary patches. If any file in the recipe directory
  is modified after preparation, publication is refused until a fresh candidate
  is prepared.
- Symlinks inside recipe directories are prohibited to prevent directory escape
  and indeterminate digest calculation.
- Bundle downloads enforce HTTPS across all redirects and verify the complete
  SHA-256 digest before invoking Flatpak bundle import.
