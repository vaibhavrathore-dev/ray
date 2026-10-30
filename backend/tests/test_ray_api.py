import io
import json
import trimesh
import pytest
from PIL import Image
from app.schemas import DesignRequest
from app.services.geometry import build_scene,export_glb,NotFeasible
from app.services.ollama import validate_image,InvalidMaterialImage


def payload():
    return {'space':{'width_cm':95,'height_cm':85,'depth_cm':45},'boards':[
       {'source_id':'wood-A','length_cm':85,'width_cm':30,'thickness_cm':1.8,'condition':'good','quantity':2},
       {'source_id':'wood-B','length_cm':90,'width_cm':30,'thickness_cm':1.8,'condition':'good','quantity':2},
    ]}

def test_valid_scene_has_unique_parts_and_guides():
    spec=build_scene(DesignRequest.model_validate(payload()))
    assert len(spec.components)==4
    assert set(spec.guidance)=={p.id for p in spec.components}
    assert len({p.stock_unit_id for p in spec.components})==4
    assert all(len(c.position_m)==3 and len(c.dimensions_m)==3 for c in spec.components)
    assert all(len(g.tools_required)>0 and len(g.instructions)>0 for g in spec.guidance.values())
    assert spec.units=='meters'

def test_glb_named_nodes_and_part_glb():
    spec=build_scene(DesignRequest.model_validate(payload()))
    glb=export_glb(spec)
    assert glb[:4]==b'glTF'
    model=trimesh.load(io.BytesIO(glb),file_type='glb',force='scene')
    assert set(p.id for p in spec.components).issubset(set(model.graph.nodes_geometry))
    part_glb=export_glb(spec,'left_side')
    sub=trimesh.load(io.BytesIO(part_glb),file_type='glb',force='scene')
    assert set(sub.graph.nodes_geometry)=={'left_side'}
    with pytest.raises(KeyError):export_glb(spec,'not_a_part')

def test_space_too_small():
    p=payload();p['space']={'width_cm':20,'height_cm':20,'depth_cm':10}
    with pytest.raises(NotFeasible):build_scene(DesignRequest.model_validate(p))

def test_missing_material_rejected():
    p=payload();p['boards'][0]['quantity']=1;p['boards'][1]['quantity']=2
    with pytest.raises(NotFeasible):build_scene(DesignRequest.model_validate(p))

def test_damaged_material_rejected():
    p=payload();p['boards'][0]['condition']='damaged'
    with pytest.raises(NotFeasible):build_scene(DesignRequest.model_validate(p))

def test_board_rotation_supported():
    p=payload();p['boards'][0]['length_cm']=30;p['boards'][0]['width_cm']=85
    build_scene(DesignRequest.model_validate(p))

def test_duplicate_stock_rejected():
    p=payload();p['boards'][1]['source_id']=p['boards'][0]['source_id']
    with pytest.raises(ValueError):DesignRequest.model_validate(p)

def test_create_and_fetch_glb(client):
    assert client.get('/health').status_code==200
    r=client.post('/api/v1/designs',json=payload())
    assert r.status_code==201,r.text
    data=r.json();id_=data['design_id'];scene=data['scene']
    assert scene['model_glb_url']==data['model_glb_url']
    assert all(x['part_model_url'] for x in scene['components'])
    r=client.get(data['model_glb_url']);assert r.status_code==200
    assert r.headers['content-type'].startswith('model/gltf-binary')
    assert r.content[:4]==b'glTF'
    assert client.get(data['scene_url']).json()==scene
    assert client.get(f'/api/v1/designs/{id_}/guidance/left_side').json()['component_id']=='left_side'
    for c in scene['components']:
        assert client.get(c['part_model_url']).content[:4]==b'glTF'
    assert client.get(f'/api/v1/designs/{id_}/guidance/nonexistent').status_code==404

def test_api_rejects_unusable_stock(client):
    p=payload();p['boards'][0]['condition']='unknown'
    r=client.post('/api/v1/designs',json=p)
    assert r.status_code==422
    assert r.json()['detail']['code']=='NO_FEASIBLE_DESIGN'

def test_owner_cannot_fetch_other_design(client):
    from app.auth import get_current_user
    from app.main import app
    d=client.post('/api/v1/designs',json=payload()).json()
    app.dependency_overrides[get_current_user]=lambda:'someone-else'
    for endpoint in [d['scene_url'],d['model_glb_url'],d['scene']['components'][0]['part_model_url']]:
        assert client.get(endpoint).status_code==404

def test_auth_fails_closed_without_config(client):
    from app.auth import get_current_user
    from app.main import app
    app.dependency_overrides.pop(get_current_user)
    assert client.get('/api/v1/templates').status_code==200
    assert client.post('/api/v1/designs',json=payload()).status_code==503

def test_image_input_format_validation():
    i=Image.new('RGB',(100,100),(150,90,55));buf=io.BytesIO();i.save(buf,format='JPEG')
    validate_image(buf.getvalue())
    with pytest.raises(InvalidMaterialImage):validate_image(b'not an image')
    with pytest.raises(InvalidMaterialImage):validate_image(b'0'*(10*1024*1024+1))

def test_one_click_manual_only(client):
    import json
    r=client.post('/api/v1/reimagine',data={'payload_json':json.dumps(payload())})
    assert r.status_code==201,r.text
    assert r.json()['material_observation'] is None
    assert r.json()['design']['scene']['components']

def test_one_click_with_mock_qwen(client,monkeypatch):
    import json,io
    from PIL import Image
    from app.schemas import Observation
    import app.routes.reimagine as rmod
    async def mock_analyze(data):
        return Observation(material_type='wood',visible_condition='uncertain',
            visible_features=['grain'],visible_defects=[],uncertainty_notes=['species unknown'],
            needs_manual_confirmation=True)
    monkeypatch.setattr(rmod,'analyze',mock_analyze)
    im=Image.new('RGB',(100,100),(160,100,60));buf=io.BytesIO();im.save(buf,format='JPEG')
    r=client.post('/api/v1/reimagine',data={'payload_json':json.dumps(payload())},
                  files={'file':('wood.jpg',buf.getvalue(),'image/jpeg')})
    assert r.status_code==201,r.text
    assert r.json()['material_observation']['needs_manual_confirmation']
    assert r.json()['design']['model_glb_url']

def test_one_click_rejects_obvious_material_mismatch(client,monkeypatch):
    import json
    from app.schemas import Observation
    import app.routes.reimagine as rmod
    async def mock_analyze(data):
        return Observation(material_type='metal',visible_condition='uncertain',needs_manual_confirmation=True)
    monkeypatch.setattr(rmod,'analyze',mock_analyze)
    r=client.post('/api/v1/reimagine',data={'payload_json':json.dumps(payload())},
                  files={'file':('metal.jpg',b'sample','image/jpeg')})
    assert r.status_code==422
    assert r.json()['detail']['code']=='MATERIAL_MISMATCH'
