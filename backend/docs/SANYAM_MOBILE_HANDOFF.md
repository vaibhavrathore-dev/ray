# RAY — Sanyam mobile 3D/AR handoff

## What you should receive from Vaibhav (FastAPI)

**1. Model `.glb`**: a complete shelf model for regular 3D preview.

**2. Part `.glb` files**: one file per selectable component. Each part GLB is centered at the part's LOCAL origin. Place it at `position_m` from the JSON to reconstruct the entire shelf in AR. This avoids assuming the native engine supports selecting child meshes of a merged GLB. Use component `id` as the UI selection key.

**3. Scene JSON**: stable IDs, centimeter dimensions, meter-based positions, part GLB URLs, assembly stages and per-part instructions/tools.

**4. Qwen JSON** (only as optional `material_observation`): never a GLB and never a measurement authority.

## Mobile implementation stack

- React Native + TypeScript + an Expo development build (not Expo Go for native AR).
- `@reactvision/react-viro` for Android ARCore experience and GLB rendering. Check versions with existing Expo/RN project.
- Expo Router or existing RN navigation.
- For authenticated downloads, download the protected `.glb` files using a request with the Supabase bearer token (or use short-lived signed URLs in a production backend) then pass the local file URI to the 3D loader. Verify loading behavior on your actual Android phone.
- Use the scene JSON in app memory; tapping an individual `<Viro3DObject>` calls `selectPart(part.id)` and shows `scene.guidance[part.id]` in a compact React Native bottom sheet.

### Contract shape

`POST /api/v1/designs` body: the contents of `examples/confirmed_stock_request.json`.

`POST /api/v1/reimagine` body: `multipart/form-data` with:
- `payload_json` = JSON string of the confirmed stock request (required)
- `file` = JPG/PNG/WEBP image (optional)

Response contains `design`, which includes:

```json
{
  "design_id": "uuid",
  "scene_url": "/api/v1/designs/uuid/scene",
  "model_glb_url": "/api/v1/designs/uuid/model.glb",
  "scene": {
    "schema_version": "1.0.0",
    "units": "meters",
    "components": [{
      "id": "left_side",
      "label": "Left side",
      "position_m": [-0.391, 0.25, 0],
      "part_model_url": "/api/v1/designs/uuid/parts/left_side.glb"
    }],
    "guidance": {
      "left_side": {
        "component_id": "left_side",
        "title": "Left side panel",
        "instructions": ["..."],
        "tools_required": ["Measuring tape", "Clamps"],
        "caution": "..."
      }
    },
    "assembly_steps": [{"step": 1, "component_ids": [], "title": "Identify and verify materials"}]
  }
}
```

Numbers above are **illustrative**. Use the actual generated JSON from the endpoint; do not hardcode these positions.

### AR component-selection logic (pseudocode)

```tsx
const [selectedId, setSelectedId] = useState<string | null>(null);
const selectedGuidance = selectedId ? scene.guidance[selectedId] : null;

// For each component:
<Viro3DObject
  key={part.id}
  source={{uri: localPartGlbUri[part.id]}}
  type="GLB"
  position={part.position_m}
  onClick={() => setSelectedId(part.id)}
/>

// Outside AR scene, use a standard RN bottom sheet:
// selectedGuidance?.title, tools_required, instructions, caution
```

Check the current ViroReact component props and use the stable version selected for your app. The above is an implementation sketch, not verified device-side code.

### Important UX rules

- Default: clean AR model, unobtrusive stage indicator and one help button.
- Tap part: highlight it and show **only that part's** tools + steps. Do not clutter the entire AR view with text labels.
- Next/previous stage: highlight that stage's `component_ids`.
- A separate “All tools” action shows project-wide tools and missing supplies before starting.
- Users can dismiss the panel, zoom/rotate preview and fall back to 3D if AR unsupported.
- Camera measurements are approximate and must be manually confirmed; do not use AR overlays as a guide for precision cutting/drilling.

### Integration sequence

1. Open `examples/demo_full_shelf.glb` in a 3D model viewer: it must show four panels.
2. Render it inside a React Native non-AR 3D viewer.
3. Download and render the four separate GLBs using their `position_m` coordinates.
4. Tap panels and show per-part guidance from JSON.
5. Integrate AR plane placement on a supported Android phone.
6. Add the `POST /api/v1/reimagine` upload and confirm-material journey.

### Limitations

The backend generates concept geometry, not verified woodworking plans. There are no certified fastener placements, load capacities, real-time material detection in AR or millimeter-accurate guidance in this MVP.
