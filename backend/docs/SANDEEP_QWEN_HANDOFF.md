# RAY — Sandeep's Qwen3-VL integration contract

**Exact tested model supplied by Sandeep:** `qwen3-vl:4b-instruct-q4_K_M`, Ollama 0.40.13 on Windows with an RTX 5050 Laptop GPU. His local image analysis works. **LAN reachability remains untested.**

## Sandeep → FastAPI: JSON only

`POST {OLLAMA_BASE_URL}/api/chat` is handled by our backend. The mobile client MUST NOT call Ollama.

The inference request uses an internal prompt, the material photo as base64, `stream: false`, and `format: Observation.model_json_schema()`.

Expected observation schema (no geometry):

```json
{
  "material_type": "wood",
  "visible_condition": "uncertain",
  "visible_features": ["visible grain"],
  "visible_defects": ["rough edge"],
  "uncertainty_notes": ["wood species and strength unknown"],
  "needs_manual_confirmation": true
}
```

**Do not return** raw GLB, base64 3D models, React components, procedural model code, cut coordinates or measured centimeters from a standalone photo. Physical dimensions must be confirmed by the user or a separate spatial measurement process.

**Why?** Qwen is good at proposing visible observations, not certified mechanical geometry. Backend Pydantic and parametric generation remain the authority.

## LAN checklist

1. On Sandeep's Windows laptop, run `ollama list` and verify the exact installed model tag.
2. Verify local `http://127.0.0.1:11434/api/tags` works.
3. Configure Ollama to listen on the intended trusted LAN interface with Windows environment setting `OLLAMA_HOST` if needed; restrict Windows Firewall to the backend's machine/network. Restart Ollama after environment changes.
4. On Vaibhav's laptop, test `http://<SANDEEP_LAN_IP>:11434/api/tags`; use a trusted private network, never public port-forwarding.
5. Set FastAPI `OLLAMA_BASE_URL` to the tested address, and compare exact request/response schema.
6. Benchmark cold/warm image request latency and timeouts. Test interrupted power, offline model, malformed JSON and consecutive calls.
7. The backend is currently set up for sequential single-request testing; production capacity and inference queuing are not implemented.

To test a protected RAY endpoint (requires valid Supabase bearer token):

```bash
curl -X POST http://<BACKEND_IP>:8000/api/v1/materials/analyze \
  -H "Authorization: Bearer <SUPABASE_ACCESS_TOKEN>" \
  -F "file=@wood.jpg;type=image/jpeg"
```

For the **one-click Reimagine** call, the React Native app supplies a JSON string of confirmed measurements as `payload_json` plus an optional image as `file`. The server calls Ollama, checks the observation, then builds the parametric design.

If Qwen is unavailable, the mobile app should allow an explicit manual-only re-submit without a photo. No AI result should be faked.
