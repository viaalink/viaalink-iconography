# Viaalink iconography

The iconography of [Viaalink](https://viaalink.com), and the system that builds it: **71 icons**, each as a **2.5D render made in Blender**
and a **flat SVG twin**, in a **light** and a **dark** edition. Plus the Blender pipeline that makes them,
flow diagrams with pipes between the icons, and story animations.

![relay-ha](docs/examples/relay-ha.png)

## Use the icons

| Folder | What |
|---|---|
| `icons/png/25d/{light,dark}` | 2.5D renders, 1024 px, transparent |
| `icons/png/flat/{light,dark}`, `icons/svg/{light,dark}` | flat twins |
| `icons/svg/themeable` | flat SVGs that follow CSS variables `--via-p --via-s --via-n --via-m --via-r --via-c` |
| `icons/svg/mono` | one colour (`currentColor`), for stamps, favicons and print |
| `icons/mermaid/viaalink.json` | Iconify set for Mermaid (`viaalink:<name>`, `viaalink:<name>-mono`) |
| `icons/drawio/*.xml` | draw.io / diagrams.net libraries (File → Open Library) |
| `icons/scenes/{light,dark}` | desk scenes (doctor, lawyer, student, school, kids, contract, import, search), 2.5D only |
| `icons/platform-marks/` | where Viaalink runs: GitHub, Apple, Android, Linux, Windows, Docker, Raspberry Pi, Bluetooth, Caddy. **Trademarks of their owners**, see [TRADEMARKS.md](TRADEMARKS.md) |

Mermaid (architecture diagrams with `viaalink:<name>`; one-colour stamps with `viaalink:<name>-mono`):

![Mermaid architecture diagram with Viaalink icons](docs/examples/mermaid-architecture.png)

```js
// from the CDN (jsDelivr serves this GitHub repo; pin a release tag)
const CDN = "https://cdn.jsdelivr.net/gh/viaalink/viaalink-iconography@v0.1.0"
mermaid.registerIconPacks([
  { name: "viaalink", loader: () => fetch(`${CDN}/icons/mermaid/viaalink.json`).then((r) => r.json()) },
  { name: "viaalink-platform", loader: () => fetch(`${CDN}/icons/platform-marks/mermaid/viaalink-platform.json`).then((r) => r.json()) },
])
// or self-hosted, nothing loaded from outside: copy icons/mermaid/viaalink.json to your site and fetch("/viaalink.json")
```

```text
architecture-beta
  group home(viaalink:nas)[Your office]
  service user(viaalink:user)[Users]
  service web(viaalink:browser)[Browser]
  service fw(viaalink:firewall)[Firewall] in home
  service lb(viaalink:loadbalancer)[Load balancer] in home
  service api(viaalink:api)[API] in home
  service db(viaalink:database)[Database] in home
  service cache(viaalink:cache)[Cache] in home
  service queue(viaalink:queue)[Queue] in home
  service mon(viaalink:monitoring)[Monitoring] in home
  user:R --> L:web
  web:R --> L:fw
  fw:R --> L:lb
  lb:R --> L:api
  api:R --> L:db
  api:B --> T:cache
  api:T --> B:queue
  db:B --> T:mon
```

(The code is shown as text: GitHub renders Mermaid itself but cannot load an icon pack, so the icons would
show as "?" there. Serve `icons/mermaid/viaalink.json` from your own site and register it as above.
Source: [docs/examples/mermaid-architecture.mmd](docs/examples/mermaid-architecture.mmd).)

Icons: `ai-a` · `api` · `backup` · `bell` · `browser-ext` · `browser` · `bucket` · `cache` · `calendar` · `call` · `certstore` · `chat` · `check` · `cicd` · `cli` · `cloud` · `cluster` · `config` · `container` · `database` · `desktop` · `dns` · `download` · `error` · `files` · `firewall` · `globe` · `info` · `key` · `license` · `link` · `loadbalancer` · `lock` · `logs` · `mail` · `mcp-a` · `meet` · `minutes` · `modem` · `monitoring` · `nas` · `notetaker` · `page` · `payment` · `pending` · `phone` · `qr-pair` · `queue` · `record` · `relay` · `report` · `router` · `search` · `server` · `shield` · `social` · `switch` · `sync` · `tablet` · `team` · `transcribe` · `trash` · `upload` · `user` · `video` · `vm` · `voice-profile` · `vscode` · `warning` · `webhook` · `wifi`

## Make them yourself

### System requirements

| | Minimum | Used to make this set |
|---|---|---|
| OS | Linux x64 (Ubuntu/Debian 24.04+); macOS and Windows via Docker | Ubuntu 24.04 |
| Blender | 4.2 LTS or newer, headless | 5.3 |
| Bun | 1.1+ | 1.4 |
| just, ffmpeg, zip | any recent | just 1.46, ffmpeg 6.1 |
| Fonts (render only, see [Brand](#brand)) | DejaVu Sans Bold, JetBrains Mono Bold (OFL) | |
| GPU | optional: NVIDIA (OptiX/CUDA). Without one Blender renders on the CPU: same result, slower | RTX 5070 Ti |
| Disk / RAM | ~2 GB for the tools, 8 GB RAM | |

### Setup

**Docker (any OS):**

```sh
docker build -t viaalink-iconography .
docker run --rm -v "$PWD":/work --user "$(id -u):$(id -g)" -e HOME=/tmp viaalink-iconography \
  just icons-blender local/icons/rounds/25d-b7 --samples 48 relay
# NVIDIA GPU: add --gpus all. The first run installs the Bun dependencies into the repo (node_modules).
```

**Linux, without Docker:** `scripts/setup-linux.sh` installs ffmpeg, just and the fonts via apt, Blender from
blender.org into `~/.local/opt`, Bun, and runs `bun install`.

**By hand:** install the tools in the table, put JetBrains Mono Bold in `~/.local/share/fonts` (or point
`VIA_ICON_FONT` at it), then `bun install`.

### Run

```sh
just icons-blender local/icons/rounds/25d-b7 --samples 48   # every 2.5D icon, light + dark (or name a few: ... relay lock)
just icons-flat local/icons/rounds/flat-r9                   # the flat twins
just icons-blender-gate                                      # no clipped white, both editions, nothing cropped
just icons-pack                                              # SVG/PNG/Mermaid/draw.io → local/icons/pack
just icons-diagram relay-ha                                  # a flow diagram (scripts/icons/blender/diagrams/relay-ha.json)
just icons-story relay-ha                                    # its story animation: nodes pop in, pipes draw, a Relay fails
just icons-gallery                                           # the gallery on http://127.0.0.1:5330 (needs the via CLI)
```

AI concept sketches (`just icons-render`) need an `OPENROUTER_API_KEY` in your environment. The rest runs
offline.

![story](docs/examples/relay-ha-story.gif)

How the set was made, with AI agents as executor and art director: [docs/HOW-WE-MADE-IT.md](docs/HOW-WE-MADE-IT.md).
Which ideas, choices and rejections came from the human: [docs/HUMAN-DIRECTION.md](docs/HUMAN-DIRECTION.md).
The working rules the agents follow: [docs/skill/SKILL.md](docs/skill/SKILL.md); real task files: [docs/tasks](docs/tasks).

## Feedback rounds

A feedback round is a small internal review: you snapshot the current renders, share one link, people vote and
comment, you decide, and the result can brief the next AI round. It is a test setup, not a website feature: the
gallery runs on your own machine and is shared through your own Viaalink Relay.

**Open a round.** This snapshots every icon (2.5D and flat, dark and light), draws a new random link and password,
and starts the gallery:

```sh
just review-round open 2026-11-a            # a closed circle: feedback stays in the round
just review-round open 2026-11-a --feed     # feed it into the next AI round when it closes
just review-round open 2026-11-a relay lock # only these icons
just review-round open 2026-11-b --changed   # only icons whose renders changed since the last round
just review-round open 2026-11-c --changed --since 2026-11-a
```

The usual rhythm: one round with every icon, then rounds with only what changed. Every round records a content
hash of each render it shows, so `--changed` compares the files themselves, not their names or dates.

**Share the link.** `just review-share` prints the link with the login in it, plus the plain address, user and
password for browsers that drop a login from a link. It is the only command that shows the password.

```
https://reviewer:<password>@icons-<slug>.<your relay domain>/r/<slug>/approve?round=2026-11-a
```

The link is random on purpose. `tools/icon-gallery/tpl.env` asks via for `REVIEW_PASSWORD` and `REVIEW_SLUG` with
the `getRandomString` macro; `via env init` writes them into the gitignored `.env`. The slug is part of the host
(`project.tunnel.prefix` in `via.yaml`) and of the path: through the Relay the gallery answers 404 until a request
has come in once through `/r/<slug>/`. Basic auth (`network.caddy.basic_auth` in `via.yaml`) sits in front of all of
it. Opening a new round rotates the slug and password, so old links stop working (`--no-rotate` keeps them;
`just review-rotate` rotates by hand). Without a Relay everything still works on http://127.0.0.1:5330.

**What reviewers can do.** Anyone with the link enters a display name once (kept in a cookie with a random
reviewer id) and can then:

- give each image a 👍, or a 👎 with a required comment saying what should change;
- comment on an icon and reply to comments, and delete their own comments;
- request an icon that does not exist yet (a name and what it should show);
- see the top images by score.

**What only the owner can do.** The owner is this machine (a direct request to 127.0.0.1 that did not come through
a proxy) or a browser that opened `/owner?key=<local/icons/owner.key>` once. The server checks this on every write;
a request that came through Caddy or the Relay is never treated as local, whatever its headers claim. The owner
sets a verdict per image (approved, needs work, rejected, queue for regeneration) with a note, deletes any
comment, and opens or closes rounds. Verdicts are also written to `local/icons/reviews.json`, so the gallery's
choice of main version follows them. The old version picker is still at `/versions`.

**Close the round and feed the next one.**

```sh
just review-round close 2026-11-a --feed     # freeze it and write the feedback for the next AI round
just review-round close 2026-11-a --no-feed  # closed circle: freeze and archive, nothing is fed
just review-feedback 2026-11-a               # rewrite the feedback files at any time
just icons-regen local/icons/rounds/25d-r12 local/icons/feedback/2026-11-a.json --dry-run   # see the prompts
just icons-regen local/icons/rounds/25d-r12 local/icons/feedback/2026-11-a.json             # render them
```

Without a flag, `close` asks, with the round's own setting as the default. Closing writes
`local/icons/feedback/<round>.json` and a readable `<round>.md`: images to regenerate or that need work, with their
notes and comments as the feedback text; approved images as the "build in Blender" list; rejected images; and the
requested new icons. `icons-regen` (render.ts `--feedback-file`) renders the icons to regenerate again with that
text added to the prompt as "IMPORTANT FEEDBACK TO ADDRESS". A round closed with `--no-feed` stays readable in the
gallery and in the `.md`, and `icons-regen` refuses its file.

All round data lives in `local/icons/review/` (one JSON file per round), which git ignores.

**Reuse it for your brand.** The data model and store are brand-free: `scripts/review/types.ts`,
`scripts/review/store.ts` and `scripts/review/feedback.ts`. What a round contains is decided in one place,
`scripts/review/snapshot.ts` (which render rounds count as current). The page takes its colours from your theme.
Copy `tools/icon-gallery/tpl.env` and the `basic_auth` and `tunnel.prefix` lines of its `via.yaml`, and run
`via config validate` after every change.

## Make it your brand

Everything that is brand or look lives in **one file**: [`theme/brand.json`](theme/brand.json) (checked against
[`theme/brand.schema.json`](theme/brand.schema.json)). The models in `build.py` only hold shapes; every script
reads the theme through one loader per language (`scripts/icons/theme.py`, `scripts/icons/theme.ts`).

| Theme key | What it sets |
|---|---|
| `brand` | name, `slug` (Iconify prefix, pack and zip names), `cssPrefix` (`--via-p` …), `cliWord` (the `> via` prompt) |
| `fonts`, `logo` | font files and logo SVGs (paths relative to the theme file) |
| `colors25d`, `materials` | 2.5D colours per role and mode, cream albedo, navy lift, glow, roughness |
| `flat` | flat role colours per mode (`p s n m r c`), the lip depth |
| `pages`, `gallery` | page colours behind sheets, films and the gallery |
| `camera`, `lights`, `render` | azimuth, pitch, framing margin; key and rim light; samples, exposure, world |
| `shape` | default bevels, smoothing, the device family's pipe port |
| `canvas`, `gate` | icon size, margin, optical size; the gate's thresholds |
| `diagram`, `animation`, `prompt` | pipes, grid, board, labels; film defaults; the AI concept palette |

To make the set for another brand:

1. Copy `theme/brand.json` somewhere of your own (keep `brand.schema.json` next to it if you want editor hints).
2. Change the colours, fonts, logo paths and `brand` names. Paths are relative to your copy.
3. Point the pipeline at it and render:

```sh
export VIA_ICON_THEME=$PWD/my-brand.json
just theme-check                                             # validates it (both loaders), names any missing key
just icons-blender local/icons/rounds/25d-b-mine --samples 48  # 2.5D (the gate checks rounds named 25d-b*)
just icons-flat local/icons/rounds/flat-mine                 # flat twins
just icons-blender-gate                                      # GATE: pass
just icons-pack --r25 local/icons/rounds/25d-b-mine --rflat local/icons/rounds/flat-mine  # packs under your slug
```

Icon names and shapes stay the same; the logo inside the Relay and the record phone comes from `logo`. Not in the
theme, so change them by hand if they matter to you: the Docker icon's containers spell VIA / LINK, the AI concept
subjects in `scripts/icons/catalog.ts` name Viaalink products, and the gallery pages keep some UI colours of their own.

**Lint:** `just lint` (ruff for Python, Biome and `tsc` for TypeScript, plus the theme check) exits 1 on any
problem; `just fmt` fixes what can be fixed. **Refactors:** `just icons-check-dump`, `icons-check-svg` and
`icons-check-png` prove that flat SVGs stay byte-identical and renders stay within Cycles noise.

## Brand

Colours, typography (Space Grotesk, IBM Plex Mono) and logo use: **[viaalink.com/brand](https://viaalink.com/brand)**.
The icon palette follows it: Viaalink Red `#F73F3F`, navy, paper `#F6F3EE`. The fonts in the requirements table
are only what the renderer needs for the few letters inside icons (the `> via` prompt, the Docker containers).

## Licence

- Icons, renders, diagrams and docs: **CC BY 4.0** ([LICENSE-ICONS](LICENSE-ICONS)). Credit: "Icons by Viaalink, viaalink.com".
- Code (the pipeline under `scripts/`): **MIT** ([LICENSE](LICENSE)).
- The **Viaalink mark** (the logo inside some icons and in `static/assets`) and the **platform marks** are trademarks
  and are not covered by these licences: see [TRADEMARKS.md](TRADEMARKS.md).

Made in the Netherlands.
