# RAY — Final AI / Backend / Mobile Integration Contract

**Project:** RAY (fresh product; not old UTPANN)  
**Scope:** Reimagine + AR-guided component inspection  
**Status:** Backend generator and contracts verified locally (15 Python tests). Live Ollama LAN, real Android AR, and Supabase credentials not yet tested.

## Ownership — do not mix responsibilities

| Owner | Does | Does not |
|---|---|---|
| **Sandeep — AI inference** | Runs Ollama `qwen3-vl:4b-instruct-q4_K_M`; serves image analysis; returns structured observations; benchmarks latency; keeps model available for integration. May suggest candidate project categories as *untrusted proposals* for a later phase. | Does not export GLB, set the canonical scene schema, infer exact physical dimensions from photos, guarantee feasible CAD geometry, or author Android components. |
| **Vaibhav — system architect / backend** | Defines Pydantic/REST contracts; receives authenticated app requests; calls Sandeep's Ollama service; checks confirmed measurements and materials; chooses supported parametric templates; allocates stock; generates SceneSpec JSON and GLB; authorizes access to stored designs; orchestrates integration. | Does not maintain Sandeep's GPU stack or Sanyam's Android UI. |
| **Sanyam — Android / AR** | React Native + TypeScript; ViroReact renderer; cameras and forms; downloads GLBs using auth; places 3D parts in AR; taps and highlights individual parts; displays relevant `guidance[component_id]`; mobile error and fallback states. | Does not call Ollama directly, choose geometry from arbitrary AI text, or calculate engineering dimensions independently. |

**Pipeline**: Android → Vaibhav FastAPI → Sandeep Ollama (image observation JSON) → FastAPI validation + template geometry → SceneSpec JSON + whole/part `.glb` assets → Android model and per-part AR guidance.

## Answers to Sandeep's 20 questions

**Q1 — Which Android 3D renderer?**  
**A:** Finalize **ViroReact** (`@reactvision/react-viro`) for Android native 3D/AR after Sanyam confirms a version compatible with his React Native/Expo development build. **Do not develop this app's main renderer using web Three.js/React Three Fiber**.

**Q2 — Same renderer for normal preview and AR?**  
**A:** Prefer the same ViroReact 3D assets and components in a non-AR 3D scene and in an AR scene, minimizing differences. Test both on a real Android device.

**Q3 — Should mobile render JSON shapes directly?**  
**A:** No requirement to implement a custom JSON-to-mesh renderer. The backend exports ready-to-load **GLB**; Android consumes the JSON as **scene metadata, positions, selectable IDs, tools, steps and instructions**.

**Q4 — JSON format?**  
**A:** Use Vaibhav's EXISTING `SceneSpec` Pydantic response schema, `schema_version: '1.0.0'` (not a new AI-invented one).

**Q5 — Unique component ID?**  
**A:** Yes. Stable IDs such as `left_side`, `right_side`, `bottom_shelf`, `top_shelf`. Each component's ID must match `guidance` key, `component_id`, part asset filename and the named GLB node.

**Q6 — Required component properties?**  
**A:** `id`, `label`, `shape`, `dimensions_m` (3 numbers), `position_m` (3), `rotation_deg` (3), `color_hex`, `stock_unit_id`, and `part_model_url`. Material type currently belongs to the *input board stock*, not yet every output component: add an explicit field in a future schema version if multi-material projects require it.

**Q7 — Units?**  
**A:** Confirmed user inputs and outside object dimensions use **centimeters**; 3D component dimensions and positions use **meters**. Scene declares `units: 'meters'`. No unit guessing.

**Q8 — Coordinate convention?**  
**A:** Right-handed, `+X` right, `+Y` up, `+Z` depth. Scene origin is the **floor center** of the complete object.

**Q9 — Center or corner?**  
**A:** `position_m` is each component **center position**. Each separately exported part GLB is modeled around its own local center; placing it at `position_m` reconstructs the complete object.

**Q10 — Rotation?**  
**A:** Yes, `rotation_deg: [x, y, z]` in **degrees**. Initial MVP exports zeros; renderer applies rotation if/when necessary.

**Q11 — Material colors/textures?**  
**A:** Backend supplies `color_hex` (currently wood shades). Texture URLs are optional future schema additions, not AI requirements.

**Q12 — Separate material properties per part?**  
**A:** Parts reference their input inventory unit through `stock_unit_id`, which maps to the confirmed stock record and its `material_type`, face size and thickness. Do not synthesize density, load rating, wood species or strength from images.

**Q13 — Both object and component sizes?**  
**A:** Yes. `outer_dimensions_cm` for the object, `components[].dimensions_m` for parts.

**Q14 — Assembly and joining metadata?**  
**A:** `assembly_steps[].component_ids` and `guidance[component_id]` are included. **Actual joining/fastener design is not certified or implemented**; don't invent screw positions or unsafe fabrication steps.

**Q15 — Cut list and feasibility?**  
**A:** Vaibhav's backend computes feasibility; if impossible, returns HTTP **422 `NO_FEASIBLE_DESIGN`**. `cut_previews` and `missing_supplies` are in existing scene JSON but are **conceptual previews**, not a validated fabrication plan.

**Q16 — What if invalid or insufficient?**  
**A:** Reject with validation/feasibility error. Ask users to correct measurements, confirm condition or add material. Do not silently invent boards or give fake GLB content.

**Q17 — Sample JSON available?**  
**A:** Yes: `RAY_Reimagine_AR_Starter/examples/demo_scene.json` and `examples/demo_full_shelf.glb`; four sample part GLBs in `examples/parts/`.

**Q18 — Android device test?**  
**A:** Not yet verified. Sanyam must first load a sample `.glb`, then reconstruct from four parts, test taps and guidance, then perform an AR placement test on an ARCore-capable Android phone.

**Q19 — JSON only or extra format?**  
**A:** **Qwen → JSON only. FastAPI → JSON + full `.glb` + part `.glb` files. Android consumes both.** Sandeep should NOT attempt to generate geometry for Android directly.

**Q20 — Final response contract?**  
**A:** `POST /api/v1/reimagine` accepts `multipart/form-data` (`payload_json` = confirmed `DesignRequest`, optional image `file`). Response contains `{ "design": { "design_id", "scene_url", "model_glb_url", "scene" }, "material_observation": {...} | null, "note": "..." }`. `scene` follows `SceneSpec v1.0.0`. For no-photo manual mode, `POST /api/v1/designs` accepts `DesignRequest` JSON.

## Current backend capabilities (verified in code)

- **Only `mini_shelf_v1`**, a basic four-panel non-structural shelf made of **wood or plywood**, represented by 4 box meshes.
- Four **confirmed-good boards**, each allocated at most once; checks face dimensions, matching thickness, quantities and fit against confirmed room space.
- Can choose among a finite list of target width/height/depth combinations, or use a requested target within schema limits.
- Writes a full `.glb`, four centered part `.glb` files, scene JSON, per-part tool lists and preliminary text guidance.
- 15 local Python tests pass; no direct live AI-to-phone test yet.
- **Does not** produce arbitrary cabinets, metal/plastic objects, load-certified furniture, screw/drill coordinates, physically validated assembly instructions or reliable measurements from a single photo.

## Key API endpoints (current code)

| HTTP route | Purpose |
|---|---|
| `GET /api/v1/templates` | Current supported template list; public |
| `POST /api/v1/materials/analyze` | Authenticated image → Ollama observations |
| `POST /api/v1/designs` | Authenticated design from confirmed input; independent of Qwen |
| `POST /api/v1/reimagine` | Authenticated one-click design, optional image and Qwen analysis |
| `GET /api/v1/designs/{id}/scene` | Authenticated full scene JSON |
| `GET /api/v1/designs/{id}/model.glb` | Authenticated full GLB |
| `GET /api/v1/designs/{id}/parts/{part_id}.glb` | Authenticated part GLB |
| `GET /api/v1/designs/{id}/guidance/{part_id}` | Authenticated guidance |

Authentication uses Supabase user-token verification. If Supabase environment settings are missing, protected routes return **503**. This is deliberate; don't bypass authentication in a publicly exposed demo.

## Stage-gated mentor demo

1. **Connectivity:** Linux→Windows `GET /api/tags`, then one remote `POST /api/chat` test with Qwen.
2. **Backend-only proof:** `pytest` pass, show `demo_full_shelf.glb` and `demo_scene.json` and the four part GLBs.
3. **Authenticated live backend:** Configure Supabase; test `POST /api/v1/designs`, get scene and GLB using a real bearer token.
4. **Qwen integrated:** Send photo + confirmed measurements to `POST /api/v1/reimagine`, see Qwen observation JSON and validated shelf scene.
5. **Android 3D:** Sanyam downloads authenticated GLBs, rotates model, taps parts, sees part-only guidance.
6. **Android AR:** On a compatible phone, place model, tap panel and display instructions. Label this feature not yet verified until the real device passes.

## Safety and honesty

AI visuals do not provide certified measurements, structural safety, tool-grade AR tracking or validated fastening. RAY MVP is a concept preview with non-structural projects, confirmed inputs and reviewed guidance. No Gemini API, no Razorpay integration, and no old UTPANN feature modules in this contract.
