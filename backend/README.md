# RAY — Reimagine + AR backend (fresh product)

**Purpose:** A narrow, working backend contract for the two RAY features: (1) Reimagine from user-confirmed materials and space dimensions, and (2) part-specific AR building guidance. No old UTPANN marketplace, community, or billing implementation is included.

## Most important architecture rule

- **Qwen3-VL → JSON observations only.** It does not generate GLB meshes, measurements or load-bearing instructions.
- **FastAPI → structured, validated scene JSON + GLB assets.** One complete GLB for 3D preview and four independent, local-origin GLBs for tappable components.
- **Sanyam mobile app → loads GLB, uses JSON for part selection, tools and text instructions.** No additional Qwen request on component tap.

These are conceptual models. Unsafe fabrication details and loads are **not** certified by generated geometry.

## Stack

- Python 3.11+ / FastAPI / Pydantic
- Trimesh + NumPy for real `.glb` export
- Ollama HTTP API, model `qwen3-vl:4b-instruct-q4_K_M` on Sandeep's Windows laptop
- SQLAlchemy + SQLite for local development, configurable PostgreSQL for later integration
- Supabase Auth (tokens verified server-side using the `/auth/v1/user` endpoint)
- RAY Android frontend: React Native + TypeScript + ViroReact / ARCore (built by Sanyam)

## Install & run

```bash
cd RAY_Reimagine_AR_Starter
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell:
# .venv\\Scripts\\Activate.ps1
python -m pip install -r requirements-dev.txt
cp .env.example .env
python -m uvicorn app.main:app --reload --port 8000
# http://127.0.0.1:8000/docs
```

**Auth is fail-closed**. To call protected APIs normally, configure `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` in `.env` and pass a real Supabase `access_token` in `Authorization: Bearer ...`. Do not paste private service-role keys into client code. In tests only, a fixture overrides the auth dependency to simulate signed-in users.

For an **offline demo with no auth or Qwen setup**, generate the example files:

```bash
python -m scripts.generate_sample
```

The ZIP already includes these example GLBs and JSON.

## API contracts

| Method / Path | Usage |
|---|---|
| `GET /health` | Public health, not Ollama readiness |
| `GET /api/v1/templates` | Available template IDs (currently only wooden mini shelf) |
| `POST /api/v1/materials/analyze` | Multipart `file` image → Qwen observation JSON, authenticated |
| `POST /api/v1/designs` | Confirmed stock/space JSON → GLB and scene, authenticated |
| `POST /api/v1/reimagine` | One-click multipart `payload_json` and optional image `file`; Qwen+geometry, authenticated |
| `GET /api/v1/designs/{id}/scene` | Complete scene spec, authenticated owner only |
| `GET /api/v1/designs/{id}/model.glb` | Full GLB, authenticated owner only |
| `GET /api/v1/designs/{id}/parts/{part_id}.glb` | Tappable individual part GLB, owner only |
| `GET /api/v1/designs/{id}/guidance/{part_id}` | Tools and steps for a selected part, owner only |

The create endpoints return relative URLs. Prefix with the backend origin, and download protected models with the user's bearer token. No public files or unsigned download URLs are issued by the API.

### Manual-only test

```bash
curl -X POST http://127.0.0.1:8000/api/v1/designs \\
  -H 'Authorization: Bearer <SUPABASE_ACCESS_TOKEN>' \\
  -H 'Content-Type: application/json' \\
  --data-binary @examples/confirmed_stock_request.json
```

### One-click test with optional image

```bash
curl -X POST http://127.0.0.1:8000/api/v1/reimagine \\
  -H 'Authorization: Bearer <SUPABASE_ACCESS_TOKEN>' \\
  -F "payload_json=$(cat examples/confirmed_stock_request.json)" \\
  -F 'file=@wood.jpg;type=image/jpeg'
```

If the user already confirmed material properties and has no photo, omit the file form field. Backend can generate a shelf without Qwen. If Qwen is unreachable with an image, the API returns 503 instead of pretending to have run AI.

## What is tested

```bash
python -m pytest -q
```

- Four named GLB components and individual component assets
- Matching IDs between JSON, all component models and each guidance card
- Unique board allocation, user-provided dimensions and stock sufficiency
- Dimensions that do not fit and damaged/unknown board rejection
- API generation, GLB downloads, guide retrieval and per-user access control
- Auth failure when unconfigured
- Image input validation
- One-click endpoint in no-photo mode and with a mocked Qwen response

**Not tested against real Sandeep's machine:** Wi-Fi/LAN connectivity, live Qwen inference, concurrency, cold/warm model latency and timeouts. **Not tested:** real Android AR rendering, secure cloud asset delivery, production durability/structural safety.

## Why one GLB plus four part GLBs?

The full GLB is for normal 3D preview. The mobile AR scene can display one GLB per part and attach a click callback directly to the corresponding component. Part GLBs are centered locally; the JSON includes each part's world-space `position_m`. This avoids assuming a GLB loader can return child-mesh hit IDs. Part instructions are precomputed; tapping a component does not require AI inference.

## Scope and safety

The MVP is intentionally restricted to **one wood/plywood non-structural shelf template**. It does not design metal structures, pressure systems, electrical work, heavy-duty furniture, load-rated shelves, fastener layouts, saw/drill placement or certified assembly plans. A geometry preview does not prove build safety. Expand templates only after reviewing material compatibility and safe construction requirements.

## Next milestones

1. Sandeep exposes Ollama to a trusted backend client via restricted LAN, then verify one real photo-to-JSON call.
2. Configure Supabase Auth and verify Sanyam can authenticate and access only his own saved designs.
3. Sanyam loads the example full and part GLBs, maps taps to `guidance[id]`, and tests on an ARCore-compatible Android device.
4. Replace local artifact files with private cloud storage and production download design, implement migrations, rate limits, queue/backpressure, monitoring and cancellation before external users.
5. Add reviewed support for cardboard and other low-risk material templates only after wood end-to-end works.

## Team handoffs

- [Sandeep: Qwen contract and LAN checklist](docs/SANDEEP_QWEN_HANDOFF.md)
- [Sanyam: Mobile viewer and AR contract](docs/SANYAM_MOBILE_HANDOFF.md)
