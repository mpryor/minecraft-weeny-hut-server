#!/usr/bin/env bash
#
# Regenerate server-config/neoforge/simple-discord-link/simple-discord-link.toml
# from sdlink's own defaults. Run this after bumping sdlink or CraterLib.
#
# The config has to carry every key sdlink knows about -- see the comment block in
# GenSdlinkConfig.java for why a partial file cannot work -- so it is generated from
# the mod's compiled defaults rather than maintained by hand.
#
# Needs a JDK (javac + java). The mod jars come from the packwiz files, so this
# always tracks the versions the pack actually ships.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out="$repo/server-config/neoforge/simple-discord-link/simple-discord-link.toml"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

url_from() {
    sed -n '/^\[download\]/,/^\[/p' "$1" | sed -n 's/^url = "\(.*\)"$/\1/p'
}

for mod in sdlink craterlib; do
    url="$(url_from "$repo/modpack/neoforge/mods/$mod.pw.toml")"
    [ -n "$url" ] || { echo "no download url in $mod.pw.toml" >&2; exit 1; }
    echo "fetching $mod: ${url##*/}"
    curl -sSLf -o "$work/$mod.jar" "$url"
done

# javac warns unconditionally about sun.misc.Unsafe; only surface output on failure.
if ! javac -nowarn -cp "$work/sdlink.jar:$work/craterlib.jar" -d "$work/classes" \
        "$repo/scripts/GenSdlinkConfig.java" >"$work/javac.log" 2>&1; then
    cat "$work/javac.log" >&2
    exit 1
fi

java -cp "$work/classes:$work/sdlink.jar:$work/craterlib.jar" \
    GenSdlinkConfig "$work/generated.toml"

# The generator emits only the mod's own comments. Ours explain why the file is
# checked in whole, and have to survive regeneration.
cat "$repo/scripts/sdlink-config-header.txt" "$work/generated.toml" > "$out"

placeholders="$(grep -c 'CFG_SDLINK_' "$out" || true)"
[ "$placeholders" -eq 3 ] || { echo "expected 3 CFG_SDLINK_ placeholders, found $placeholders" >&2; exit 1; }

echo "wrote $out"
