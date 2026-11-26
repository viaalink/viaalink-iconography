# Changelog

## 0.1.0 (2026-11-26): first public release

- 72 Viaalink icons (2.5D Blender + flat SVG twin, light + dark), plus 10 platform marks in `icons/platform-marks/`
  (OS marks shown on a Viaalink phone or desktop, as in real diagrams).
- Enough for complete IT architecture diagrams: people (user, team), clients, network (router, modem, switch,
  firewall, load balancer, DNS, Caddy, relay), compute (server, VM, container, cluster, cloud, NAS), data
  (database, cache, queue, bucket, backup, files), security (lock, key, shield, certificate store), integration
  (API, webhook, MCP), delivery (CI/CD, monitoring, logs) and UI basics (bell, search, trash).
- Desk scenes in `icons/scenes` (doctor, lawyer, student, school, kids, contract, import, search, finance, consult,
  interview, coach, board), 2.5D in light and dark.
- Packs: themeable and mono SVG, PNG 1024 px, Mermaid Iconify set, draw.io libraries.
- The pipeline: Blender models (`scripts/icons/blender/build.py`), flat twins (`flat.ts`), the gate, the pack,
  flow diagrams with pipes (`diagram.py`), clip and story animations (`animate.py`, `story.py`).
- An independent expert vision review scored the set 7.2/10 before the last fixes; the weakest icons were redone.

Known gaps: some icons are still busy at 16–24 px; Mermaid examples for IT diagrams come next.
