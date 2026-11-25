# G7B and Geoda · instructions for agents

**Read the [official Amatista project base](https://github.com/Maximiliano-cabello-mata/amatista-recuperada-20261106/blob/recuperacion/BASE.md) first** (version 1, frozen on November 22, 2026). It defines the components, the workflow and the priorities, and it overrides any other plan. The base is in Spanish; its official terms are kept in Spanish here.

> **Amatista** teaches and measures; **G7B** extracts and stores; **Amatista IA** audits; **Geoda** adapts; **Amatista Machine Learning** creates.

## Place of this repository in the base

| Component | Role in the base |
|---|---|
| **G7B** | The data extraction flow and warehouse: spiders, Geodar Radar and probes → lake (bronze) → quality funnel and validation (silver) → **cube** (measurements) and **MongoDB** (knowledge). Stores no personal data |
| **Geoda** (`geoda/`) | The **kernel**: the adaptive engine. Starts from the N1–N4 profiles and adapts each computer's 3D engine in real time (cost model, planner, controller, visual quality). Runs inside the Amatista add-on for Blender and the web viewer |

- **One door:** Amatista IA (the auditor, [AMATISTA-IA-](https://github.com/Maximiliano-cabello-mata/AMATISTA-IA-)) approves; approved data enters the cube or MongoDB. **Geoda always reads from the cube**, never from unaudited data.
- **Two outputs, two projects:** the cube feeds Geoda; MongoDB will feed Amatista Machine Learning (parked).
- **Public data is never accepted on its own:** it needs G7B's own reproduction or corroboration. The «corroborado» state is a pending decision of the base.

## Rules

- Do not add components, services, databases, sources or AI providers. A new idea goes to the base's parking list.
- One active change at a time, and only inside the current priority of the base:
  1. turn on the daily audit flow;
  2. finish the Amatista web redesign;
  3. minimal Geoda, the adaptive engine in Blender's 3D viewport on the N1–N2 profiles.
- No personal data enters G7B. Measurements from Amatista arrive aggregated and with the student's consent, through the Amatista API.
- Open PRs that change standards (#26, #27, #28) need the owner's decision before they become part of the base.
- Do not claim something is deployed or tested without evidence.
