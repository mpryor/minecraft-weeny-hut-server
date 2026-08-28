#!/usr/bin/env python3
"""Build the generic pack that delivers client-only content to players.

itzg's image hardcodes `packwiz-installer -s server` (start-setupModpack:40),
so a mod marked `side = "client"` never reaches /data/mods -- and AutoModpack
only serves what is in /data/mods. Players who sync the pack themselves through
Prism get those mods fine; players who rely on AutoModpack do not.

Marking client mods `both` to force them through is what crash-looped the server
on 2026-08-27, twice. NeoForge has no per-mod dist gate: it loads every jar in
mods/ and only strips client-only classes, so a client mod runs its constructor
on the server and dies if that constructor touches anything client-only.

This builds a zip that itzg's GENERIC_PACKS handling unpacks into /data *after*
packwiz has run, placing client content under automodpack/host-modpack/main/,
where AutoModpack serves it to clients and the server never loads it.

Zip layout:

    config/.generic-pack-anchor            <- see ANCHOR below
    automodpack/host-modpack/main/mods/*.jar
    automodpack/host-modpack/main/shaderpacks/*.zip

ANCHOR: start-setupModpack recomputes the content base with

    mc-image-helper find --max-depth=3 --type=directory \
        --name=mods,plugins,config --only-shallowest --fail-no-matches

Without a shallow mods/plugins/config directory it either fails outright, or --
worse -- resolves the base to automodpack/host-modpack/main and copies the
client jars straight into /data/mods, reproducing the crash. The top-level
config/ directory pins the base at the zip root. Do not remove it.

Usage: scripts/build-client-extras.py <env> [-o OUT]
"""

import argparse
import hashlib
import sys
import tomllib
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST_MODPACK = "automodpack/host-modpack/main"
ANCHOR_PATH = "config/.generic-pack-anchor"
ANCHOR_TEXT = (
    "Pins the generic pack's content base at the zip root.\n"
    "start-setupModpack finds the shallowest mods/plugins/config directory and\n"
    "treats its parent as the base. Without this, the base would resolve to\n"
    "automodpack/host-modpack/main and the client jars would land in /data/mods,\n"
    "which crashes a dedicated NeoForge server. See scripts/build-client-extras.py.\n"
)
UA = {"User-Agent": "weenyhut-client-extras/1.0"}


def client_mods(env):
    """(filename, url, hash, hash-format) for every side = "client" mod."""
    out = []
    for f in sorted((ROOT / "modpack" / env / "mods").glob("*.pw.toml")):
        d = tomllib.loads(f.read_text())
        if d.get("side") != "client":
            continue
        dl = d["download"]
        out.append((d["filename"], dl["url"], dl["hash"], dl.get("hash-format", "sha512")))
    return out


def fetch(url, expected, fmt):
    """Download and verify against the hash packwiz recorded."""
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA)) as r:
        blob = r.read()
    actual = hashlib.new(fmt.replace("-", ""), blob).hexdigest()
    if actual != expected:
        raise SystemExit(
            f"hash mismatch for {url}\n  expected {expected}\n  got      {actual}"
        )
    return blob


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("env")
    ap.add_argument("-o", "--out")
    args = ap.parse_args()

    env = args.env
    out = Path(args.out) if args.out else ROOT / "modpack" / f"{env}-client-extras.zip"
    extras = ROOT / "client-extras" / env

    mods = client_mods(env)
    if not mods:
        print(f"{env}: no side = \"client\" mods; nothing to deliver", file=sys.stderr)

    out.parent.mkdir(parents=True, exist_ok=True)
    written = []
    # deterministic: fixed timestamp so an unchanged pack produces an identical zip
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        def add(arcname, blob):
            info = zipfile.ZipInfo(arcname, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, blob)
            written.append(arcname)

        add(ANCHOR_PATH, ANCHOR_TEXT)

        for filename, url, expected, fmt in mods:
            print(f"  fetching {filename}")
            add(f"{HOST_MODPACK}/mods/{filename}", fetch(url, expected, fmt))

        for sub in ("shaderpacks", "resourcepacks", "config"):
            src = extras / sub
            if not src.is_dir():
                continue
            for f in sorted(src.rglob("*")):
                if f.is_file():
                    rel = f.relative_to(src)
                    add(f"{HOST_MODPACK}/{sub}/{rel.as_posix()}", f.read_bytes())

    size = out.stat().st_size
    # -o may point outside the repo (CI writes to /tmp), so relative_to can fail
    try:
        shown = out.relative_to(ROOT)
    except ValueError:
        shown = out
    print(f"\n{shown}  ({size/1024/1024:.1f} MiB, {len(written)} entries)")
    for a in written:
        print(f"  {a}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
