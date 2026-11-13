# BedrockOnLinux

- Upstream: <https://github.com/Wyze3306/BedrockOnLinux>
- Manifest copied from upstream commit `cc6ac3235bfbbf9d05fe6870b09ef71e7f1a4f52`.
- The manifest pins application source tag `v2.2.10` and its commit. Check both
  this pin and upstream's build guidance when updating the manifest.
- `LICENSE.upstream` is the upstream license and redistribution notice.
- The launcher downloads Minecraft and other components separately at runtime;
  review their respective terms and requirements before publishing.

The manifest requests network, all devices, X11, Wayland, audio, multiarch,
`devel`, and specific filesystem paths. Review these permissions and the
upstream release before distributing. The candidate builds and installs from
a local signed test repository; interactive launch and game functionality have
not been tested.
