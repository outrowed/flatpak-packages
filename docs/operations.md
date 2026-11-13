# Build and publication operations

This checkout contains the Flatpak manifests and tooling used to build and
publish packages. Git updates change the packaging sources; building, testing,
and publishing are separate steps.

The tooling currently supports local test repositories. Public deployment has
not been verified, and the publish script is not ready for use against a live
repository.

## Build

Use a trusted x86_64 Linux build machine with `flatpak`, `flatpak-builder`,
`ostree`, `elfutils`, GnuPG, and `flock`. Flatpak's sandbox and user namespaces must work
on the build machine. Keep signing keys separate from the build environment.

Configure Flathub as a user remote for the SDK and runtime dependencies:

```sh
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
```

Build an application from the checkout:

```sh
./scripts/build io.github.wyze3306.BedrockOnLinux
```

The script prints the candidate repository path. Review the upstream sources,
license terms, changes, and sandbox permissions, then test the candidate on an
isolated client before signing it. Builds use two jobs by default; set `JOBS`
to change this.

## Sign and publish

Use a dedicated GPG signing key and keep its private material outside Git, the
public web root, and the build environment. Back up the key securely and
verify its fingerprint independently.

Initialize a new archive-mode OSTree repository on the signing machine:

```sh
ostree --repo=/absolute/path/to/destination/repo init --mode=archive
```

Publish a reviewed candidate using the signing key's fingerprint:

```sh
./scripts/publish /absolute/path/to/candidate/repo /absolute/path/to/destination/repo FINGERPRINT
```

The script signs the application and runtime refs and updates the repository's
summary and AppStream metadata. The candidate, destination, and signing key must
be available on the same machine.

Public hosting still requires a `.flatpakrepo` file containing the HTTPS URL
and public key, a web server without browser authentication challenges, and a
successful client install and update test. Production deployment and atomic
publication are not yet implemented.

Reference: <https://docs.flatpak.org/en/latest/hosting-a-repository.html>
