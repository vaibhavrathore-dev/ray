"""Generate example 3D assets without auth/Ollama. These are public fictional DEMO inputs."""
import json
from pathlib import Path
from app.schemas import DesignRequest
from app.services.geometry import build_scene, export_glb

root=Path(__file__).resolve().parents[1]
payload=json.loads((root/'examples/confirmed_stock_request.json').read_text())
scene=build_scene(DesignRequest.model_validate(payload))
(root/'examples/demo_scene.json').write_text(scene.model_dump_json(indent=2),encoding='utf-8')
(root/'examples/demo_full_shelf.glb').write_bytes(export_glb(scene))
for part in scene.components:
    (root/'examples/parts'/f'{part.id}.glb').write_bytes(export_glb(scene,part.id))
print('Generated scene and 5 GLB files in examples/ (one full model + four parts)')
