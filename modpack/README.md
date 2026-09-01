# Weeny Hut Modpack

Single source of truth for the mods running on the servers **and** on every
player's client. Managed with [packwiz](https://packwiz.infra.link/).

```
modpack/
  dev/            -> dev.weenyhut.com            Fabric 1.20.1   (Weeny Hut (dev))
  prod/           -> weenyhut.com                Fabric 1.20.1   (Weeny Hut)
  neoforge-dev/   -> neoforge-dev.weenyhut.com   NeoForge 1.21.1 (Weeny Hut (neoforge-dev))
  neoforge-prod/  -> neoforge-prod.weenyhut.com  NeoForge 1.21.1 (Weeny Hut (neoforge-prod))
```

Two lines, each with a dev and a prod half. `dev` and `prod` are the legacy
Fabric line on CloudFormation. `neoforge-dev` and `neoforge-prod` are the
NeoForge line, deployed from
[minecraft-weeny-hut-terraform](https://github.com/mpryor/minecraft-weeny-hut-terraform),
and they are the ones with a promotion path — see
[Promoting to neoforge-prod](#promoting-to-neoforge-prod) below.
[NEOFORGE-MIGRATION.md](NEOFORGE-MIGRATION.md) covers what carried over from the
Fabric packs and what didn't.

Each directory is a complete, independent pack with its own `pack.toml`,
`index.toml`, and `mods/`. `pack.toml` carries the Minecraft and loader
versions, so packs are free to differ — which is what lets the two lines run
side by side on different loaders.

## How syncing works

Every `mods/*.pw.toml` pins an exact Modrinth version ID plus a SHA-512 hash,
so the server and all clients resolve byte-identical jars.

- **Servers** — `PackwizUrl` in the deploy file sets `PACKWIZ_URL` on the
  container. `packwiz-installer` runs on every container start.
- **Clients** — Prism Launcher runs `packwiz-installer-bootstrap.jar` as a
  pre-launch command, so mods sync on every launch.

`side` controls who gets what: `both` installs everywhere, `server` is skipped
on clients, `client` is skipped on the server.

**Never set a client-only mod to `both` to get it onto players.** NeoForge has
no per-mod dist gate -- it loads every jar in `mods/` and only strips client-only
*classes* -- so a client mod runs its constructor on a dedicated server and takes
it down if that constructor touches anything client-only. This crash-looped the
NeoForge server twice on 2026-08-27. Client mods reach players two other ways:
`packwiz-installer` defaults to `-s client`, so Prism gets them; and
`scripts/build-client-extras.py` packages them for AutoModpack. See
[NEOFORGE-MIGRATION.md](NEOFORGE-MIGRATION.md). Sides were derived from each project's declared `client_side` /
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

### Every add or remove needs a catalog entry

Adding or removing a mod is a two-file change: the `.pw.toml` **and**
`catalog/<env>.toml` at the repo root. CI fails if they disagree.

```bash
python3 scripts/check-catalog.py   # run before committing
```

The catalog records what each mod is and **why we added it** — the one thing the
pack itself cannot tell you six months later.

It has to live outside `modpack/` because packwiz will not hold that
information. `packwiz update` rewrites a mod's `.pw.toml` from a Go struct and
silently discards comments and any key it does not recognise, so a note written
inline survives until the next version bump and then vanishes without warning.
`packwiz refresh` does the same to unknown keys in `pack.toml`. A sidecar file
inside the pack directory does not work either — `packwiz refresh` indexes every
file it finds there, so it would be downloaded to the server and to every
player, unless excluded with a `.packwizignore`.

A `reason` of `TODO` means nobody has written the rationale down yet. CI reports
the count but does not fail on it; filling one in is a good thing to do while
you are touching a mod anyway.

### Mods with no upstream

`modpack/local-mods/` holds jars that packwiz cannot fetch because there is no
Modrinth or CurseForge project behind them — currently the hand-ported
`diesel-jetpack-1.0.0.jar`. They are committed here and served by the same
GitHub Pages site as the packs (`modpack/` is the site root, so the jar resolves
at `<pages-url>/local-mods/<file>.jar`). The directory sits outside every pack
directory, so `packwiz refresh` never indexes it.

Each one gets a hand-written `.pw.toml` with a `[download]` block and **no
`[update]` block** — `refresh` hashes it like any other metafile, and
`packwiz update --all` leaves it alone because there is nothing to check.

```bash
cp build/libs/foo-1.2.0.jar modpack/local-mods/
sha512sum modpack/local-mods/foo-1.2.0.jar
$EDITOR modpack/neoforge-dev/mods/foo.pw.toml   # name, filename, side, [download]
(cd modpack/neoforge-dev && packwiz refresh)
```

**Do not put the jar straight into a pack's `mods/` directory.** `packwiz
refresh` would index it as a raw file, and raw index entries carry only
`{file, hash}` — there is no `side` on them, so the server and every client
would download it whatever it is. And a new build needs a new filename, or
clients keep the old jar alongside it.

The published URL only exists after a push to `master`, so a freshly added local
mod 404s for clients until CI has run.

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

## Client-only content

`client-extras/<env>/` holds files served to players but never installed on the
server -- currently the shader pack. `scripts/build-client-extras.py <env>`
bundles it with every `side = "client"` mod into a zip that the container unpacks
into AutoModpack's host directory. CI builds it on each publish; the zip is
gitignored so it cannot drift from the pack.

```bash
python3 scripts/build-client-extras.py neoforge-dev   # writes modpack/neoforge-dev-client-extras.zip
```

Drop a shader or resource pack into `client-extras/neoforge-dev/shaderpacks/`
(or `resourcepacks/`) and it ships on the next publish. The top-level `config/`
entry the script writes into the zip is load-bearing -- see NEOFORGE-MIGRATION.md.

Only the NeoForge packs have one; the Fabric pair predates the mechanism. The
`EXTRAS_PACKS` list in `.github/workflows/publish-modpack.yml` is what decides.

## Promoting to neoforge-prod

`neoforge-dev` follows master: every merge here republishes it, and the dev
server picks it up on its next start. `neoforge-prod` follows a decision.

Run the **Promote modpack** workflow from the Actions tab. It copies the edge
pack, its catalog, its server config and its client extras onto the prod ones
and opens a pull request:

```bash
scripts/promote-modpack.sh --check   # would anything change?
scripts/promote-modpack.sh           # same copy, locally
```

**That pull request's diff is the list of mod versions about to change under
production**, which is the whole reason promotion is a copy of files rather
than a version number in a URL -- a pinned version would put a one-line diff in
front of the reviewer and hide the part that matters. The pull request body
summarises it as added / removed / updated mods.

Exactly one field does not travel: the pack's display `name`, so the two are
distinguishable in a client's modpack list. It is not covered by any hash
(`pack.toml` hashes `index.toml`, not itself), so the rewrite cannot make
`packwiz refresh` a non-no-op.

Nothing in the Terraform repo changes on a promotion -- the pack URL is
constant. Prod picks the new pack up on its next container start, which, since
autoshutdown stops the server when it empties, is the next `/mcstart`.

## Applying a published pack to a server

Mod changes don't alter the ECS task definition, so no CloudFormation deploy is
needed. Push to `master`; CI publishes to GitHub Pages. Then either let the
server pick it up on its next cold start (autoshutdown idles it out), or force
it now:

```bash
scripts/redeploy <stack-name>
```
