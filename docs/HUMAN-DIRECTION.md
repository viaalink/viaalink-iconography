# The human in the loop

This set was made by Kelvin Wuite together with AI agents. The agents wrote most of the code, modelled the
icons in Blender and checked every render by looking at it. But the **ideas, the taste and the decisions** came
from Kelvin. This page lists them, in the order they happened, so it is clear which parts are human.

Quotes are Kelvin's own words from the working sessions, translated from Dutch where needed.

## 1. The foundation

- **The generator.** Kelvin designed the icon generator in 2025 at ASD Engineering for the ASD Manager. He
  first used OpenAI, and moved the code to OpenRouter after OpenAI blocked his access. Everything here
  starts from that code.
- **The ambition.** "Keep validating with vision, and make sure we build a high-quality 3D, 2.5D and 2D icon
  library." This made the set a library, not a handful of pictures.
- **Own models, not pictures.** He noticed that many icons were still plain AI images and not built from
  our own models. That pushed the whole 2.5D set into Blender, where every icon is a real model.

## 2. The house style came from his eye

- **"The icon is the object."** Looking at a Wi-Fi icon sitting on a square tile, he said the icon itself
  should be the object, not a picture on a tile. He picked `sync` as the approved reference. This became
  the main rule of the set.
- **Faces, not surfaces.** Speech waves should come from the face of a person, not from some upper surface.
- **Platform marks with character.** He asked for GitHub, Windows, Mac, Linux, Android and iOS "in our own
  design", with the ASD Manager icons as the bar.
- **Docker, his idea.** "Write VIA on top and LINK in the containers below, one letter per container."
- **Colour vigilance.** He noticed when the brand red looked orange. Twice this led to a real problem: a
  screen-mode question, and later a film encoding bug (BT.601 without colour tags) that turned red into
  orange in every video.
- **2D matches 2.5D.** He chose sand as the flat secondary colour, so the flat twins match the cream parts
  of the 2.5D icons, with navy and red as accents.
- **Raspberry Pi with navy leaves** (picked from three options). Also more navy in the set, for example a
  globe caught in the `webhook` hook.

## 3. What to make, and what not

- **Missing icons.** He named the gaps: NAS, Raspberry Pi, router, modem, Caddy, Let's Encrypt, DNS. Then:
  "keep looking, there are more things", and finally: make the set complete enough for real IT
  architecture diagrams.
- **Rejecting what does not fit.** The realistic apple fruit, a GitHub flat that "looks like a monster",
  and a Caddy sculpture that "looked odd and not fitting when used as an example in our project". Each
  rejection became a better icon.
- **The concept workflow.** "Can we make a few suggestions so I can approve one?" From this came the method:
  ideas in text, then AI sketches in our style, then he picks one, then it is built in Blender.
- **One device family.** "Ports for all": every network device keeps its own shape but gets the same pipe
  ports. Then the final call on how many ports: two on the icon, with extra sockets added in diagrams where
  a pipe needs them.
- **Real use cases.** "If os-ios is a phone with the logo, do the same for the rest": Android on the phone,
  Linux, Windows and macOS on a desktop screen.
- **Caddy's own mark.** He found Caddy's official logo and asked to put it on "the default block we use".

## 4. From icons to a system

- **Diagrams that explain the company.** Flow diagrams of Viaalink now and in the future ("every Viaalink
  app will be able to talk to the next"). A router feeding three NATS-linked Relays for zero downtime. The
  CLI as a web publisher, with Caddy inside the Relay on a NAS.
- **Animation.** He asked for the Blender objects to become animations for the product films, and was not
  happy with a drifting camera. That led to story animations: things appear, pipes connect, a Relay fails
  and the rest keeps serving.
- **Publishing.** A Mermaid icon set and draw.io/Visio stencils: "we're not there yet". Without that, the
  set would not be usable outside the website.

## 5. Strategy and openness

- **Open source, with boundaries.** Icons, pipeline and process in the open; the Viaalink mark and
  third-party marks protected; the film engine and voice kept private.
- **Show that we host it, keep the rest private.** The gallery's `via.yaml` shows how Viaalink hosts its own
  tools, without any infrastructure details.
- **A submodule, like the ASD Manager.** The website takes the icons from this repo.
- **A community page.** An iconography page on viaalink.com built from the latest release, with downloads
  from Mermaid to Blender, and votes, comments and icon requests from signed-in users.
- **Review before public.** Nothing went public before he had read the code.

## Who did what

| Kelvin (human) | The AI agents |
|---|---|
| The original generator and its move to OpenRouter | The Blender pipeline, flat twins, gate, pack, diagrams, animations |
| The vision: a complete, consistent library in Viaalink's style | Modelling every icon from his descriptions and picks |
| The house rules: the icon is the object, one device family, 2D matches 2.5D | Rules written down (docs/skill) and enforced in every task |
| Every approval and rejection, every pick between concepts | Concept sketches, renders, contact sheets, vision QA |
| What the set must cover, and why | Gap lists and expert reviews, offered as input for his decisions |
| Publishing, licensing and community strategy | Packaging, docs, the repo and the release |
