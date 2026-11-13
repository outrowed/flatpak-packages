#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "$0")/.." && pwd -P)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT
mkdir -p "$tmp/project/scripts" "$tmp/project/apps/example" "$tmp/bin" "$tmp/destination" "$tmp/source"
cp "$root/scripts/build" "$root/scripts/publish" "$tmp/project/scripts/"
touch "$tmp/project/apps/example/org.example.App.yml" "$tmp/destination/config" "$tmp/source/config"
export CALLS="$tmp/calls"
: > "$CALLS"
cat > "$tmp/bin/flatpak-builder" <<'MOCK'
#!/usr/bin/env bash
printf 'builder' >> "$CALLS"; printf ' <%s>' "$@" >> "$CALLS"; printf '\n' >> "$CALLS"
[[ ${FAIL_BUILD:-0} != 1 ]]
MOCK
cat > "$tmp/bin/flatpak" <<'MOCK'
#!/usr/bin/env bash
printf 'flatpak' >> "$CALLS"; printf ' <%s>' "$@" >> "$CALLS"; printf '\n' >> "$CALLS"
[[ ${FAIL_FLATPAK:-0} != 1 ]]
MOCK
cat > "$tmp/bin/ostree" <<'MOCK'
#!/usr/bin/env bash
case "$*" in
  *'config get core.mode'*) echo "${FAKE_MODE:-archive-z2}" ;;
  *' refs') [[ ${FAIL_REFS:-0} != 1 ]] || exit 1; printf '%s\n' 'app/org.example.App/x86_64/stable' 'runtime/org.example.App.Locale/x86_64/stable' 'appstream/x86_64' ;;
  *) exit 1 ;;
esac
MOCK
chmod +x "$tmp/bin/"*
export PATH="$tmp/bin:$PATH"
fail() { echo "FAIL: $*" >&2; exit 1; }
"$tmp/project/scripts/build" org.example.App >/dev/null
grep -Fq '<--default-branch=stable>' "$CALLS" || fail 'build branch'
grep -Fq '<--sandbox>' "$CALLS" || fail 'build sandbox'
grep -Fq '<--disable-rofiles-fuse>' "$CALLS" || fail 'FUSE-independent build'
if "$tmp/project/scripts/build" '../bad' >/dev/null 2>&1; then fail 'invalid ID accepted'; fi
if "$tmp/project/scripts/build" org.missing.App >/dev/null 2>&1; then fail 'missing manifest accepted'; fi
if FAIL_BUILD=1 "$tmp/project/scripts/build" org.example.App >/dev/null 2>&1; then fail 'builder error ignored'; fi
: > "$CALLS"
"$tmp/project/scripts/publish" "$tmp/source" "$tmp/destination" test-key >/dev/null
[[ $(grep -c 'build-commit-from' "$CALLS") == 2 ]] || fail 'expected app and locale refs'
grep -Fq '<--gpg-sign=test-key>' "$CALLS" || fail 'commit signing'
grep -Fq '<build-update-repo>' "$CALLS" || fail 'missing metadata update'
if grep -Fq 'appstream/x86_64' "$CALLS"; then fail 'source appstream ref imported'; fi
if FAKE_MODE=bare "$tmp/project/scripts/publish" "$tmp/source" "$tmp/destination" test-key >/dev/null 2>&1; then fail 'non-archive destination accepted'; fi
if FAIL_REFS=1 "$tmp/project/scripts/publish" "$tmp/source" "$tmp/destination" test-key >/dev/null 2>&1; then fail 'ref listing error ignored'; fi
if "$tmp/project/scripts/publish" "$tmp/source" "$tmp/source" test-key >/dev/null 2>&1; then fail 'same source and destination accepted'; fi
if FAIL_FLATPAK=1 "$tmp/project/scripts/publish" "$tmp/source" "$tmp/destination" test-key >/dev/null 2>&1; then fail 'import error ignored'; fi
printf 'All tooling checks passed.\n'
