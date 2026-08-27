# NeoForge migration (dev)

Scaffold for `modpack/neoforge/` — a third environment
(`neoforge.weenyhut.com`) for trialling a NeoForge port of the Fabric pack.
The existing `dev` and `prod` packs are untouched.

## Why Minecraft 1.21.1

NeoForge cannot be trialled on 1.20.1. Surveying all 52 mods in the prod pack
against the Modrinth API for `loaders=["neoforge"]`:

| Minecraft | mods with a NeoForge build |
|-----------|---------------------------:|
| **1.21.1**| **42 / 52**                |
| 1.21.4    | 42 / 52                    |
| 1.21      | 41 / 52                    |
| 1.20.4    | 36 / 52                    |
| **1.20.1**| **13 / 52**                |

So a NeoForge migration necessarily means a Minecraft version bump — the two
can't be separated.

1.21.1 and 1.21.4 tie at 42. They differ by exactly one mod each: `deeperdarker`
has 1.21.1 but not 1.21.4; `dcintegration` has 1.21.4 but not 1.21.1. **1.21.1
was chosen** because NeoForge 21.1.x is the long-supported branch, and losing a
Discord chat bridge (several drop-in alternatives exist) is cheaper than losing a
content mod players interact with.

Loader pinned to NeoForge `21.1.248`.

## What carried over

**45 mods installed** — 42 direct carry-overs plus 3 replacements for
Fabric-only counterparts. Every one verified to have a `neoforge` + `1.21.1`
build. No unmet required dependencies.

| Fabric | NeoForge | Note |
|--------|----------|------|
| `create-fabric` | `create` | Same mod, upstream Forge/NeoForge edition |
| `trinkets` | `curios` | Standard equivalent; `comforts` depends on it |
| `fabric-language-kotlin` | `kotlin-for-forge` | Kotlin runtime |
| `fabric-api` | — | Not needed; NeoForge has a native API |

## Gaps — 7 mods not carried over

Nothing was substituted on your behalf beyond the four above. These need a
decision:

| Mod | Status | Verified NeoForge 1.21.1 candidates |
|-----|--------|-------------------------------------|
| `ledger` | No NeoForge build | `coreprotectneo` — block logging + rollback. Different UX to Ledger. |
| `universal-graves` | No NeoForge build | `ly-graves`, `gravestone-mod` |
| `dcintegration` | NeoForge builds exist, but not for 1.21.1 | `fagas-discord-bridge`, `discord-linker`, `verbatim` |
| `xp-storage` | No NeoForge build | None found |
| `xp-storage-trinkets` | Depended on `xp-storage` + `trinkets` | None found |
| `memoryleakfix` | No NeoForge build | None needed — `modernfix` carried over and overlaps heavily |
| `forge-config-api-port` | **Carried over, but likely redundant** | It's a Fabric port of NeoForge's own config API. Kept deliberately rather than dropped, in case a mod declares a hard dependency on it. Verify and remove if nothing needs it. |

Adding any candidate is one command:

```bash
cd modpack/neoforge && packwiz modrinth add ly-graves && packwiz refresh
```

## Known caveats

- **Three mods resolved to beta-channel builds**: `owo-lib` (only a beta exists
  for NeoForge), plus `open-parties-and-claims` and `unloaded-activity`, which
  were already on `:beta` in the original list.
- **The world will generate differently.** The seed was carried over from dev,
  but 1.20.1 and 1.21.1 worldgen differ, and the structure mod set changed.
  Treat this as a fresh world, not a migrated one.
- **Loader version is only half-synced.** packwiz-installer does not install the
  loader — on the server that's the container's job. `NeoForgeVersion` in the
  deploy file is set to `21.1.248` to match `pack.toml`. **Keep the two in step**;
  if you bump one, bump the other.
- **Sizing was raised** to `t3.large` / `4G` (dev runs `t3.medium` / `3G`).
  45 mods including Create on 1.21 will not fit in a 3G heap on a 4GB instance.
  This costs more than dev — drop it back if the trial is short.
- **`.profile-dev` and dev's Discord channel are reused.** Give the stack its own
  S3 profile and channel if you want its shutdown notices separated from dev's.

## Deploying

The stack does not exist yet — this is a scaffold. Deploy
`minecraft-neoforge-deploy.yml` to create it, which provisions a new EFS, ASG,
and Route 53 record for `neoforge.weenyhut.com`. Players need a **third** Prism
instance pointed at the neoforge pack.
