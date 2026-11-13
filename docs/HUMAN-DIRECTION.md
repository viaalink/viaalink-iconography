# The system behind the Viaalink iconography

Kelvin Wuite designed this system: the philosophy, the architecture, the infrastructure it runs on, and the
agentic way of working that builds it. AI agents carry out the work inside it. This page describes the system
as he designed it.

## 1. Philosophy: own your technology, own your image

Viaalink lets people run their apps on their own devices instead of someone else's cloud. The iconography
follows the same principle. It is not a set of bought icons or one-off generated images. It is a system
Viaalink owns end to end: the code that generates ideas, the models that turn them into objects, the rules
that keep them consistent, and the infrastructure that serves and reviews them. Every icon can be rebuilt
exactly from source, in light and dark, flat and in depth, for the website, for diagrams and for film.

Three convictions run through everything:

- **One world.** Every icon is an object from the same world: the same camera, light, materials and red. A
  relay, a phone and a padlock could stand on the same desk. The icon *is* the object, never a symbol on a
  tile.
- **The brand is imprinted on the objects.** Like a maker's stamp: the Viaalink mark on the relay, the phone,
  the desktop and the plug; the CLI prompt `> via` on screens; VIA and LINK on the Docker containers; all in
  the brand's own typography.
- **Pictures explain the product.** Operating systems appear as the devices you run them on; network devices
  form one family that plugs into the same pipes; diagrams and animations tell how Viaalink works.

## 2. Architecture

The system is built in layers, each with one job, each reproducible from code:

| Layer | What it does | Where |
|---|---|---|
| **Theme** | One source of truth for the look: brand, colours, fonts, logo, camera, light, materials, canvas, diagram style. Swap it and the same system builds another brand | `theme/brand.json` |
| **Generator** | Explores ideas as images in the house style. Kelvin built it in 2025 at ASD Engineering on OpenAI, and ported it to OpenRouter when access was blocked, so it depends on no single provider | `scripts/icons/render.ts`, `openrouter.ts` |
| **3D models** | Every approved idea becomes a real Blender model, built from parts with colour roles; light and dark are a palette swap | `scripts/icons/blender/build.py` |
| **Flat twins** | The same object drawn flat as SVG, part by part, with the same roles | `scripts/icons/flat.ts` |
| **Gate** | Measures every render: no clipped white, both editions present, nothing cropped | `scripts/icons/blender/gate.ts` |
| **Packs** | SVG, PNG, Mermaid and draw.io libraries for real-world use | `scripts/icons/pack.ts` |
| **Diagrams and stories** | Icons placed on a board with pipes routed between them; story animations where devices appear, pipes connect and a Relay can fail while the network carries on | `diagram.py`, `story.py` |
| **Gallery and approval** | Every round on a review page, with a verdict and a note per image | `tools/icon-gallery` |

## 3. Infrastructure

The system runs on Viaalink's own infrastructure, the way it asks its users to run theirs. Rendering happens on
Viaalink's own machines and GPUs. The review gallery is served from its own machine and published through its
own Relay at a shared URL. Nothing in the loop needs a third-party platform except the image model behind the
generator, and that one is replaceable by design. The setup is portable: a Docker image and a Linux script
rebuild the whole pipeline anywhere.

## 4. The loop

The heart of the system is an iterative loop, designed to be honest: every image is judged by people, in the
open, until it earns its place.

1. **Generate** a round of candidates in the house style.
2. **Share** it through Viaalink's own Relay, so colleagues, testers and outside reviewers can look.
3. **Judge**: every image gets approved, needs work, rejected or regenerate, with a note. Kelvin's verdict
   counts; outside reactions and independent reviews feed into it.
4. **Feed back**: the notes become the brief for the next round, so a rejection is never lost.
5. **Build in 3D, then flat**: an approved image becomes a Blender model, and its flat twin is drawn from it.
6. **Judge again**: the gate, a look at every render, an independent review, the shared gallery.

Between 9 and 13 November 2026 this loop ran twelve AI rounds, eight Blender rounds, nine rounds of flat twins
and three concept rounds, in 144 commits. Next, the same loop opens up: signed-in users on viaalink.com will
vote on icons, comment and request new ones, and their input becomes the next round.

## 5. Agentic logic: many agents, clear roles

Kelvin designed how the agents work together. No single agent does everything, and no agent is trusted on its
word.

- **The orchestrator** acts as product owner and QA. It turns Kelvin's direction into precise task files,
  verifies every result against the real output (renders, measurements, contact sheets), and only then keeps
  it. It never accepts "done" from a report.
- **The executor** (Google's Antigravity CLI) builds in Blender from a task file. Each task names exactly what
  to change, carries the house rules, and ends with the same finish line: the gate must pass, and every render
  must be looked at. At most three iterations, then an honest "done" or "not done, and why".
- **Independent reviewers** are fresh agents that see only the images: an expert scoring of every icon, and
  blind reads that ask "what does this picture say?" without labels. Their findings are input for Kelvin, not
  decisions.
- **Specialised agents work in parallel, each in its own lane.** One builds the icons, one builds the
  website, one runs the film and encoding workers, one leads the app releases. They hand work to each other,
  report back, and never edit each other's files.
- **Gates over promises.** Every new kind of failure becomes a permanent check, so the system gets more
  reliable with every round instead of repeating mistakes.
- **Serial where it must be, parallel where it can be.** Tasks that touch the same files run one after
  another; independent work runs side by side.

## 6. The human role

The machines do the work; the human decides. Kelvin set the vision, the architecture and the rules, and made
every call that shaped the set: what to build, what to reject, which concept to pick, how far is far enough.
Many icons were rejected before they were kept, and each rejection sharpened the rules. Taste is never
delegated. Even colour is looked at, not trusted: when the brand red looked orange, the cause was found, once
on a screen and once in how films were encoded.

## 7. Open, with care

What can help others is shared: the icons, the pipeline, the theme, the rules and the way of working.
Viaalink's own mark and other companies' marks are protected, the internal film and voice tools stay private,
and the repository shows how Viaalink hosts its tools without giving away where. Nothing is published before
Kelvin has read it.
