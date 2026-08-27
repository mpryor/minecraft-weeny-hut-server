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

The pack started at **45 mods** — 42 direct carry-overs plus 3 replacements for
Fabric-only counterparts. Every one verified to have a `neoforge` + `1.21.1`
build. No unmet required dependencies.

It is now **76 mods**. See [What was added after the migration](#what-was-added-after-the-migration)
below, and `catalog/neoforge.toml` for what every one of them is and why it is
here. Counts in this document describe the original migration; the catalog is
the live list, and CI keeps it in step with the pack.

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

## What was added after the migration

**2026-08-27 — 31 mods, taking the pack from 45 to 76.** All pinned to explicit
Modrinth project + version IDs, release channel wherever one exists.

- **15 client mods** for parity with the prod Modrinth profile, which had been
  the de-facto client pack: Sodium, Iris, Distant Horizons, Jade, REI, Xaero's
  Minimap and World Map, Chat Heads, LambDynamicLights, Inventory Profiles Next,
  libIPN, Enchantment Descriptions, Freecam, Mouse Tweaks, Smart Completion.
- **5 content carry-overs** the original migration missed because they were only
  ever in the client profile: Create Jetpack, Create: Diesel Generators,
  GeckoLib, Bookshelf, Prickle.
- **4 NeoForge-only mods** with no Fabric equivalent, the point of the trial:
  Ars Nouveau, Apotheosis, Sophisticated Storage, Sophisticated Backpacks.
- **7 transitive dependencies** resolved by packwiz: `placebo`,
  `apothic-attributes`, `apothic-enchanting`, `apothic-spawners`, `patchouli`,
  `sophisticated-core`, `prickle`.

Two resolved to beta builds because no release-channel NeoForge 1.21.1 build
exists at all: **Distant Horizons** (0 of 22) and **REI** (0 of 6).

Every `side = "client"` mod was initially set to `both`, on the assumption that
NeoForge would skip them on a dedicated server the way Fabric does. **That
assumption is wrong, and it took the server down twice on 2026-08-27.**

Fabric reads `"environment": "client"` from `fabric.mod.json` and never loads the
mod on a server. **NeoForge has no equivalent per-mod gate.** It loads every jar
in `mods/` and only strips client-only *classes* at runtime via
`RuntimeDistCleaner`. A client mod therefore runs its constructor on the server,
and dies if that constructor touches anything client-only:

```
RuntimeDistCleaner: Attempted to load class me/shedaniel/clothconfig2/api/ConfigEntryBuilder
                    for invalid dist DEDICATED_SERVER
Failed to create mod instance. ModID: freecam
```

Sodium failed even earlier, before the mod list was read at all. It registers a
`META-INF/services/net.neoforged.neoforgespi.earlywindow.GraphicsBootstrapper`,
and FML invokes every one of those from `ImmediateWindowHandler.load()` during
ModLauncher bootstrap. That path touches LWJGL, which a dedicated server does not
ship:

```
NoClassDefFoundError: org/lwjgl/Version
  at LAYER SERVICE/sodium_service@0.8.12/...PreLaunchChecks.checkEnvironment
  at MC-BOOTSTRAP/fml_loader@4.0.43/...ImmediateWindowHandler.load
```

**Sides are now taken from each project's declared Modrinth support, not from
what we want the distribution mechanism to do.** The nine mods with
`server_side: unsupported` are `client`: Sodium, Iris, Freecam, Chat Heads,
LambDynamicLights, Inventory Profiles Next, libIPN, Mouse Tweaks, Smart
Completion. 67 of the 76 mods load on the server.

Distant Horizons, Jade, REI, and both Xaero's maps stay `both` — Modrinth
declares them `optional` on the server, and they are genuinely dual-sided.

### Two client delivery paths, and what each carries

**Prism + packwiz-installer — unaffected.** `packwiz-installer` defaults to
`-s client`, and a client takes both `both` and `client` mods. Verified against
the published pack: 62 of 76 jars, Sodium and Iris included. Marking those nine
mods `client` changed nothing for players on this path; it only changed what the
*server* loads.

**AutoModpack — needed help.** The image runs `packwiz-installer -s server`
(`start-setupModpack:40`, hardcoded, no env var), so `client` mods never reach
`/data/mods`, and AutoModpack only serves `/data/mods`. Players who join without
a Prism instance would get none of them.

`GENERIC_PACKS` closes that gap. `handleGenericPacks` runs *after*
`handlePackwiz` and copies a zip's contents into `/data`, so it can place client
content under `automodpack/host-modpack/main/`, where AutoModpack serves it and
the server never loads it. `scripts/build-client-extras.py` builds that zip from
the pack itself -- every `side = "client"` mod, downloaded and checked against
the SHA-512 packwiz recorded -- plus anything in `client-extras/neoforge/`.
CI builds it on every publish, so it cannot drift from the pack.

**The top-level `config/` directory in that zip is load-bearing.**
`start-setupModpack:244` recomputes the content base with

```
mc-image-helper find --max-depth=3 --type=directory \
    --name=mods,plugins,config --only-shallowest --fail-no-matches
```

Verified in the image: with the anchor the base resolves to the zip root; without
it the call exits 1 and the container start fails. Were the layout ever made
shallower, the base would resolve to `automodpack/host-modpack/main` and the
client jars would be copied straight into `/data/mods` -- crashing the server
exactly as before. Do not remove it.

**Do not set a client mod to `both`.** Before adding any new client mod, check
both hazards:

```bash
# bootstrap-level service -> crashes before mod loading (Sodium class)
unzip -l <mod>.jar | grep -E 'META-INF/services/(cpw\.mods\.modlauncher|net\.neoforged\.(fml\.loading|neoforgespi\.(locating|earlywindow)))'
# declared support -> server_side "unsupported" means client-only (Freecam class)
curl -s https://api.modrinth.com/v2/project/<slug> | jq '{client_side, server_side}'
```

### Shaderpacks

`client-extras/neoforge/shaderpacks/` ships shader packs to players through the
same zip. Currently Complementary Reimagined r5.5.1, taken from the prod client
profile. Iris is in the pack as `client`, so both paths get the loader; before
this, neither path carried the shader files themselves and players supplied their
own. `resourcepacks/` and `config/` alongside it work the same way.

### Still not carried over

`ledger`, `universal-graves`, `dcintegration`, `xp-storage`,
`xp-storage-trinkets`, `memoryleakfix` remain gaps — see the table above.
Polymer-based server mods (`universal-graves`, `taterzens`) are structurally
unportable: Polymer is a Fabric-only framework.

Two mods in the prod client profile are local builds with no upstream, so they
cannot be pulled by packwiz and must be ported by hand:
`diesel-jetpack-1.0.0.jar` and `hollowharvest-1.0.0.jar`. Both of their
dependencies (Create Jetpack, Create: Diesel Generators, GeckoLib) now have
NeoForge 1.21.1 builds in the pack, so the ports are viable.

FTB Library, Quests, and Teams are in the prod client profile but are
CurseForge-only — reachable with `packwiz curseforge add`, not the Modrinth
path used everywhere else here.

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
- **Heap has not been re-checked since the pack grew to 76 mods.** The `4G`
  figure was sized for 45. The 2026-08-27 additions include Ars Nouveau,
  Apotheosis (plus three `apothic-*` modules), and Sophisticated
  Storage/Backpacks, all of which carry real world-data and registry cost.
  **Watch heap on the first boot after this change and before inviting players
  in**; budget for a larger instance.
- **`.profile-dev` and dev's Discord channel are reused.** Give the stack its own
  S3 profile and channel if you want its shutdown notices separated from dev's.

## Deploying

The stack does not exist yet — this is a scaffold. Deploy
`minecraft-neoforge-deploy.yml` to create it, which provisions a new EFS, ASG,
and Route 53 record for `neoforge.weenyhut.com`. Players need a **third** Prism
instance pointed at the neoforge pack.
