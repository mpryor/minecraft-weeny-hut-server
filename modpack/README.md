# Weeny Hut Modpack

Single source of truth for the mods running on the servers **and** on every
player's client. Managed with [packwiz](https://packwiz.infra.link/).

```
modpack/
  dev/       -> dev.weenyhut.com        Fabric 1.20.1   (Weeny Hut (dev))
  prod/      -> weenyhut.com            Fabric 1.20.1   (Weeny Hut)
  neoforge/  -> neoforge.weenyhut.com   NeoForge 1.21.1 (Weeny Hut (neoforge))
```

`dev` and `prod` are the live Fabric line. `neoforge/` is a **migration trial**
running a different loader and Minecraft version — it is not part of the
dev -> prod promotion path. See [NEOFORGE-MIGRATION.md](NEOFORGE-MIGRATION.md)
for what carried over and what didn't.

Each directory is a complete, independent pack with its own `pack.toml`,
`index.toml`, and `mods/`. `pack.toml` carries the Minecraft and loader
versions, so packs are free to differ — which is exactly how the NeoForge trial
runs alongside the Fabric pair.

## How syncing works

Every `mods/*.pw.toml` pins an exact Modrinth version ID plus a SHA-512 hash,
so the server and all clients resolve byte-identical jars.

- **Servers** — `PackwizUrl` in the deploy file sets `PACKWIZ_URL` on the
  container. `packwiz-installer` runs on every container start.
- **Clients** — Prism Launcher runs `packwiz-installer-bootstrap.jar` as a
  pre-launch command, so mods sync on every launch.

`side` controls who gets what: `both` installs everywhere, `server` is skipped
on clients. Sides were derived from each project's declared `client_side` /
`server_side` support on Modrinth. At time of writing: 35 `both`, 17 `server`,
none client-only.

## Making changes

Always work in `modpack/dev/` first.

```bash
cd modpack/dev
packwiz modrinth add <slug>      # add
packwiz update <slug>            # update one
packwiz update --all             # update everything
packwiz remove <slug>            # remove
packwiz refresh                  # ALWAYS run before committing
```

`packwiz refresh` rewrites `index.toml` (a hash of every mod file) and
`pack.toml` (a hash of the index). **Edit a `.pw.toml` by hand and skip the
refresh, and clients will silently install the stale version with no error.**
CI runs `packwiz refresh` on both packs and fails if it produces a diff.

To pin a mod to a specific version:

```bash
packwiz modrinth add --project-id <id> --version-id <version-id>
```

## Promoting dev to prod

Copy the specific mod files you're promoting, then refresh:

```bash
cp modpack/dev/mods/<slug>.pw.toml modpack/prod/mods/
(cd modpack/prod && packwiz refresh)
```

`diff -r modpack/dev modpack/prod` shows the current delta between environments.

**Prefer promoting file-by-file over `cp dev/mods/* prod/mods/`.** A wholesale
copy silently drags along every mod dev happens to be testing, and would undo
deliberate prod pins — see below.

### Deliberate prod pins

- `deeperdarker` is pinned to version `vk0DMgtP` (1.3.3-plus, beta channel).
  This was pinned by hand in the old `ModrinthProjects` list while every other
  mod floated, so it is assumed deliberate — **the reason was never recorded.**
  Confirm before promoting a newer version over it.

## Applying a published pack to a server

Mod changes don't alter the ECS task definition, so no CloudFormation deploy is
needed. Push to `master`; CI publishes to GitHub Pages. Then either let the
server pick it up on its next cold start (autoshutdown idles it out), or force
it now:

```bash
scripts/redeploy <stack-name>
```
