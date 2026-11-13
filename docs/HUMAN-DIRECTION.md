# The human in the loop

This icon set is Kelvin Wuite's vision, made real together with AI agents. The agents wrote code, modelled
objects in Blender and checked every render. The vision, the taste and every decision came from Kelvin. This
page sets out that vision, and how each part of the set follows from it.

## The vision

**A company that lets you own your technology should also own its image.** Viaalink is about running your
apps on your own devices instead of someone else's cloud. Its pictures follow the same idea. They are not
stock icons, and not one-off AI images that drift from week to week. They are a library Viaalink owns
completely: models, code and rules that rebuild every icon exactly, in light and dark, flat and in depth,
for the website, for diagrams and for film.

That vision has five parts.

### 1. One world, not a collection of pictures

Every icon is a real object from the same world: the same camera, the same light, the same materials, the
same red. A relay, a phone and a padlock look as if they stand on the same desk. That is why the set moved
from generated images into Blender. A model can be rebuilt; a picture can only be replaced.

From this follow the house rules:

- **The icon is the object, never a symbol on a tile.** A Wi-Fi icon is the waves themselves; a sync icon is
  the two arrows. `sync` is the reference.
- **Things that do the same job belong to the same family.** Every network device keeps its own character
  (a modem stands, a router has antennas, a NAS has drive bays) but shares the same ports. In a diagram they
  all plug into the same pipes. Two ports on the icon keep it calm; the diagram adds a socket where a pipe
  needs one.
- **Flat and depth are one design.** The flat twin is the same object pressed flat, in the same colour
  logic: sand where the 2.5D has cream, navy and red as accents.
- **Brand typography everywhere,** down to the letters on a container: Space Grotesk and IBM Plex Mono, from
  the brand itself.

### 2. Pictures that explain the product

An icon earns its place by explaining something real. So the set grew from Viaalink's own story, not from a
list of generic symbols:

- an operating system is shown as the device you run it on, a phone or a desktop, with its mark;
- an internet webhook catches a globe;
- Caddy carries its own mark on the device block it lives in;
- a Raspberry Pi keeps the two-colour character of the real thing.

The same thinking produced the diagrams. One shows Viaalink today. One shows its future, where every
Viaalink app talks to the next. One shows a router feeding three Relays that keep each other in sync, so
one can fail while the others keep serving. Then came the animations. Things should not drift across the
screen; the story is told: devices appear, pipes connect, and a Relay fails and the network carries on.

### 3. Complete enough to build with

A brand set becomes a tool when others can describe their own systems with it. Kelvin set that bar: the
library must cover real IT architecture (users, networks, firewalls, load balancers, servers, containers,
clusters, databases, caches, queues, APIs, monitoring) and work where people actually draw: Mermaid,
draw.io and Visio, and Blender itself.

### 4. The loop: human judgement decides, machines do the work

The heart of the vision is not one icon but **the loop that makes them**, and that loop is designed to be
honest: every image is judged by people, in the open, until it earns its place. Kelvin designed it.

1. **Generate.** The generator Kelvin built in 2025 at ASD Engineering, first on OpenAI and moved to
   OpenRouter when access was blocked, produces a round of candidates in the house style.
2. **Share.** Every round is published as a gallery, served by Viaalink from its own machine through its own
   Relay, at a shared URL. Anyone with the link can look: colleagues, testers, outside eyes. It is the same
   way Viaalink asks its users to share their own apps.
3. **Judge.** On the approval page each image gets a verdict (approved, needs work, rejected, regenerate)
   with a note. Kelvin's verdict is the one that counts; outside reactions and independent reviewers feed
   into it.
4. **Feed back.** The notes go back into the generator as feedback for the next round, so a rejection is
   never lost: it becomes the brief for the next attempt.
5. **Build in depth, then flat.** An approved image becomes the target for a real 3D design, modelled in
   Blender. From that 3D object its flat twin is drawn as code, with the same parts and colour roles, and
   checked side by side with it. Both are code, so every icon can be rebuilt exactly, in light and dark,
   flat and in depth.
6. **Judge again.** The 3D result goes through the same loop: rendered, measured by a colour gate, reviewed
   by eye, scored by an independent reviewer, shared, approved or sent back.

The numbers show it is a loop and not a single pass. Between 9 and 13 November 2026 the set went through
twelve AI rounds, eight Blender rounds, nine rounds of flat twins and three concept rounds, in 144 commits.
Many icons were rejected before they were kept: a realistic apple, a flat GitHub mark that read as a monster,
a Caddy sculpture that did not fit the family. Each rejection sharpened the rules above. Taste is never
delegated. Even colour is looked at, not trusted: when the brand red looked orange, the cause was found,
once on a screen and once in how films were encoded.

The same loop is what comes next for everyone. On viaalink.com, signed-in users will be able to vote on
icons, comment and request new ones. Their votes and requests become the input for the next round, which
becomes the next 3D design.

### 5. Open, with care

What can help others is shared: the icons, the pipeline, the rules and the way of working, all here in the
open. Viaalink's own mark and other companies' marks are protected, and the internal film and voice tools
stay private. Viaalink hosts its own tools on its own infrastructure, and the repository shows how without
giving away where. Everyone can use the set. Nothing was published before Kelvin had read it.

## Who did what

| Kelvin (human) | The AI agents |
|---|---|
| The vision: one owned, consistent world of objects that explains Viaalink | Turning each part of it into code and models |
| The original generator, and its move to OpenRouter | The Blender pipeline, flat twins, gate, pack, diagrams, animations |
| The loop: generate, share, judge, feed back, build in 3D, judge again | Running each step of the loop, round after round |
| The house rules, and every approval and rejection | Concept sketches, renders, contact sheets, review by eye |
| What the set must cover, and for whom | Gap lists and expert reviews, as input for his decisions |
| Openness, licensing and community | Packaging, documentation, the repository and the release |
