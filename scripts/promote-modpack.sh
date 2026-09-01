#!/usr/bin/env bash
#
# Copy an edge pack onto a promoted one.
#
#   scripts/promote-modpack.sh [--check] [FROM] [TO]
#
# Defaults to neoforge-dev -> neoforge-prod.
#
# The two servers run different pack URLs on purpose. modpack/neoforge-dev is
# the edge: every merge to master republishes it, and neoforge-dev picks it up
# on its next start. modpack/neoforge-prod only changes when this script runs
# and someone merges the result, so production's mod list moves when a person
# decides it does.
#
# Promotion is a file copy rather than a version pinned in a URL, and that is
# the whole design. A pinned version would put a one-line diff in front of the
# reviewer; copying the tree puts every mod version that is about to change
# under production in front of them instead. That diff is the artifact worth
# having -- it is the only place the question "what actually changes for the
# players?" gets answered.
#
# Everything that defines the pack travels together:
#
#   modpack/<name>/        the packwiz pack -- pack.toml, index.toml, mods/
#   catalog/<name>.toml    why each mod is in it (scripts/check-catalog.py)
#   server-config/<name>/  server-side mod config, shipped in the generic pack
#   client-extras/<name>/  shaderpacks and other client-only content
#
# Duplicating client-extras/ means a second copy of a 460K shaderpack in the
# tree, which looks wasteful and is not: git stores blobs by content, so an
# identical file costs a tree entry and nothing else. It becomes a second
# object only when it actually differs, which is exactly when you want it to.
#
# --check reports whether a promotion would change anything and leaves the tree
# untouched. Exit 0 means the promoted pack already matches the edge, 1 means it
# does not. CI uses it to avoid opening an empty pull request.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CHECK=0
if [ "${1:-}" = "--check" ]; then
    CHECK=1
    shift
fi

FROM="${1:-neoforge-dev}"
TO="${2:-neoforge-prod}"

# These names are interpolated into `rm -rf`. Anything but a plain pack name
# stops here rather than a few lines further down.
for n in "$FROM" "$TO"; do
    case "$n" in
        *[!a-z0-9-]* | "" | -*)
            echo "refusing to work on pack name '$n'" >&2
            exit 2
            ;;
    esac
done

if [ "$FROM" = "$TO" ]; then
    echo "refusing to promote '$FROM' onto itself" >&2
    exit 2
fi

if [ ! -d "modpack/$FROM" ]; then
    echo "no such pack: modpack/$FROM" >&2
    exit 2
fi

# The promotion is always built in full under a staging directory first, and
# only then either diffed (--check) or moved into place. Building it twice --
# once to compare, once to apply -- is how the two modes drift apart, and a
# --check that disagrees with the promotion it is checking is worse than no
# --check at all.
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

mkdir -p "$STAGE/modpack" "$STAGE/catalog" "$STAGE/server-config" "$STAGE/client-extras"

stage() {
    local src="$1" dest="$2"
    [ -e "$src" ] || return 0
    cp -a "$src" "$dest"
}

stage "modpack/$FROM" "$STAGE/modpack/$TO"
stage "catalog/$FROM.toml" "$STAGE/catalog/$TO.toml"
stage "server-config/$FROM" "$STAGE/server-config/$TO"
stage "client-extras/$FROM" "$STAGE/client-extras/$TO"

# The one field that does not travel verbatim. `name` is what packwiz and
# AutoModpack show a player, and two packs both called "Weeny Hut (neoforge-dev)"
# are indistinguishable in a client's modpack list. It is not covered by any
# hash -- pack.toml hashes index.toml, not itself -- so rewriting it cannot make
# `packwiz refresh` a non-no-op, which the publish workflow asserts.
python3 - "$STAGE/modpack/$TO/pack.toml" "$TO" <<'PY'
import re
import sys
from pathlib import Path

path, to = Path(sys.argv[1]), sys.argv[2]
want = f'name = "Weeny Hut ({to})"'
s = path.read_text()
new = re.sub(r'^name\s*=\s*".*"$', want, s, count=1, flags=re.M)
if want not in new:
    sys.exit(f"could not rewrite the pack name in {path}")
path.write_text(new)
PY

# `rm -rf` then move, never a copy over the top. A mod dropped from the edge
# pack has to disappear from the promoted one too, and merging would leave it
# behind -- a mod nobody has reviewed for two releases, still served to
# production.
targets=(
    "modpack/$TO"
    "catalog/$TO.toml"
    "server-config/$TO"
    "client-extras/$TO"
)

if [ "$CHECK" = 1 ]; then
    changed=()
    for t in "${targets[@]}"; do
        staged="$STAGE/$t"
        if [ ! -e "$staged" ]; then
            # Nothing to promote into this path. It is stale only if it
            # exists. `if`, not `[ -e ] && ...`: under `set -e` the AND-list's
            # non-zero status when the path is absent would end the script.
            if [ -e "$t" ]; then changed+=("$t (would be removed)"); fi
            continue
        fi
        if [ ! -e "$t" ]; then
            changed+=("$t (new)")
        elif ! diff -rq "$t" "$staged" >/dev/null 2>&1; then
            changed+=("$t")
        fi
    done
    if [ ${#changed[@]} -eq 0 ]; then
        echo "$TO already matches $FROM; nothing to promote"
        exit 0
    fi
    echo "$TO differs from $FROM; a promotion would change:"
    printf '  %s\n' "${changed[@]}"
    exit 1
fi

for t in "${targets[@]}"; do
    rm -rf "$t"
    if [ -e "$STAGE/$t" ]; then mv "$STAGE/$t" "$t"; fi
done

echo "promoted $FROM -> $TO"
