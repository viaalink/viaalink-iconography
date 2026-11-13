# Viaalink icons: the pipeline (run from the repo root). Blender 4.x/5.x, Bun, ffmpeg.
# Rounds land in local/icons/rounds/<round>/{light,dark}; the pack reads 25d-b7 and flat-r9.

# 2.5D icons from the Blender models (light + dark = palette swap): just icons-blender local/icons/rounds/25d-b7 [--samples 48] [names...]
icons-blender out *args:
	blender -b --factory-startup -P scripts/icons/blender/build.py -- --out {{out}} {{args}} 2>&1 | grep -E '^ok|Error|Traceback'
	bun scripts/icons/normalize.ts {{out}}

# Flat twins (SVG on a 24 grid) → <out>/{light,dark}/<name>.svg|png
icons-flat out *args:
	bun scripts/icons/flat.ts --out {{out}} {{args}}

# Gate: no clipped white, both editions, nothing cropped (checks local/icons/rounds/25d-b*)
icons-blender-gate:
	bun scripts/icons/blender/gate.ts

# Flow diagram from scripts/icons/blender/diagrams/<name>.json → local/icons/diagrams/<name>/{light,dark}.png (+ labels.json, .blend)
icons-diagram name *args:
	blender -b --factory-startup -P scripts/icons/blender/diagram.py -- --spec scripts/icons/blender/diagrams/{{name}}.json --out local/icons/diagrams/{{name}} {{args}} 2>&1 | grep -E '^ok|Error|Traceback'

# Desk scene from scripts/icons/blender/scenes/<name>.json
icons-scene name *args:
	blender -b --factory-startup -P scripts/icons/blender/diagram.py -- --spec scripts/icons/blender/scenes/{{name}}.json --out local/icons/scenes/{{name}} {{args}} 2>&1 | grep -E '^ok|Error|Traceback'

# Clip animation of a rendered diagram: packets flow, optional camera push/orbit, webm + labels-anim.json
icons-animate name kind="diagrams" *args:
	blender -b local/icons/{{kind}}/{{name}}/{{name}}.blend -P scripts/icons/blender/animate.py -- --out local/icons/anim/{{name}} {{args}} 2>&1 | grep -E '^ok|^animate|Error|Traceback'

# Story animation (scripts/icons/blender/stories/<name>.json): nodes pop in, pipes draw, packets flow, a node can fail
icons-story name kind="diagrams" *args:
	blender -b local/icons/{{kind}}/{{name}}/{{name}}.blend -P scripts/icons/blender/story.py -- --story scripts/icons/blender/stories/{{name}}.json --out local/icons/anim/{{name}}-story {{args}} 2>&1 | grep -E '^ok|^story|Error|Traceback'

# The pack (SVG/PNG, Mermaid Iconify set, draw.io libraries) → local/icons/pack
icons-pack *args:
	bun scripts/icons/pack.ts {{args}}

# AI concept sketches (OpenRouter, OPENROUTER_API_KEY from the environment), Blender renders as style refs
icons-render out *args:
	bun scripts/icons/render.ts --out {{out}} {{args}}

# The gallery (showcase, overview, approval) on http://127.0.0.1:5330, published via your Viaalink Relay
icons-gallery:
	cd tools/icon-gallery && via config validate && via up

# Refactor guard: dump every flat SVG string (light, dark, themeable, mono, badge) → <out>/<kind>/<name>.svg
icons-check-dump out:
	bun scripts/icons/check-identical.ts dump {{out}}

# Refactor guard: two SVG dumps must be byte-identical
icons-check-svg before after:
	bun scripts/icons/check-identical.ts svg {{before}} {{after}}

# Refactor guard: two renders must match within Cycles noise (per-icon mean abs diff, max channel diff)
icons-check-png before after *args:
	bun scripts/icons/check-identical.ts png {{before}} {{after}} {{args}}
