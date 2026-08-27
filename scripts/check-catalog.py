#!/usr/bin/env python3
"""Verify catalog/<env>.toml stays 1:1 with modpack/<env>/mods/*.pw.toml.

packwiz rewrites .pw.toml files from a Go struct on `packwiz update`, silently
dropping comments and unknown keys, so a mod's rationale cannot be stored
inline. The catalog lives outside the pack directory instead — which means
nothing stops it drifting from the pack unless something checks. This is that
something.

Exit codes: 0 clean, 1 drift or malformed entry.
"""

import sys
import tomllib
from pathlib import Path

ENVS = ("dev", "prod", "neoforge")
REQUIRED_FIELDS = ("name", "description", "category", "side", "reason")

ROOT = Path(__file__).resolve().parent.parent


def pack_mods(env):
    """slug -> side, read straight from the packwiz metadata files."""
    mods = {}
    for f in sorted((ROOT / "modpack" / env / "mods").glob("*.pw.toml")):
        with f.open("rb") as fh:
            data = tomllib.load(fh)
        # packwiz omits `side` when it means "both"
        mods[f.name[: -len(".pw.toml")]] = data.get("side", "both")
    return mods


def main():
    failures = []
    todo_total = 0

    for env in ENVS:
        catalog_path = ROOT / "catalog" / f"{env}.toml"
        if not catalog_path.exists():
            failures.append(f"{env}: missing {catalog_path.relative_to(ROOT)}")
            continue

        with catalog_path.open("rb") as fh:
            catalog = tomllib.load(fh)
        mods = pack_mods(env)

        for slug in sorted(set(mods) - set(catalog)):
            failures.append(
                f"{env}: '{slug}' is in the pack but not in catalog/{env}.toml — "
                f"add a [{slug}] entry describing what it does and why it is here"
            )
        for slug in sorted(set(catalog) - set(mods)):
            failures.append(
                f"{env}: '{slug}' is in catalog/{env}.toml but not in the pack — "
                f"remove the [{slug}] entry"
            )

        for slug in sorted(set(catalog) & set(mods)):
            entry = catalog[slug]
            for field in REQUIRED_FIELDS:
                if field not in entry or entry[field] in ("", []):
                    failures.append(f"{env}: [{slug}] is missing '{field}'")
            # side is duplicated into the catalog for readability, so it can rot
            if "side" in entry and entry["side"] != mods[slug]:
                failures.append(
                    f"{env}: [{slug}] side is '{entry['side']}' but the pack says "
                    f"'{mods[slug]}'"
                )
            if str(entry.get("reason", "")).startswith("TODO"):
                todo_total += 1

        print(f"{env}: {len(mods)} mods, {len(catalog)} catalog entries")

    if failures:
        print(f"\n{len(failures)} problem(s):\n", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    print("\nCatalog matches every pack.")
    if todo_total:
        # Not a failure: undocumented history is pre-existing, and blocking the
        # build on it would only encourage filler text.
        print(f"note: {todo_total} entries still have a TODO reason.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
