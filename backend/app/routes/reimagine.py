from pathlib import Path
import json
from uuid import uuid4,UUID
from fastapi import APIRouter,Depends,File,Form,HTTPException,UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models import Design
from app.schemas import DesignRequest,DesignCreated,SceneSpec
from pydantic import ValidationError
from app.services.geometry import NotFeasible,build_scene,export_glb
from app.services.ollama import InvalidMaterialImage,QwenUnavailable,analyze,MAX_BYTES

router=APIRouter(prefix='/api/v1',tags=['RAY Reimagine'])

def load_design(db:Session,design_id:str,user_id:str)->Design:
    try:
        if str(UUID(design_id,version=4)) != design_id:
            raise ValueError('invalid')
    except ValueError as e:
        raise HTTPException(404,'Design not found') from e
    d=db.get(Design,design_id)
    if not d or d.user_id!=user_id:
        raise HTTPException(404,'Design not found')
    return d

def artifact_path(design_id:str,filename:str)->Path:
    return Path(settings().artifact_dir).resolve()/design_id/filename

@router.get('/templates')
def templates():
    return [{'template_id':'mini_shelf_v1','material_types':['wood','plywood'],
             'required_panels':4,'geometry':'parametric_boxes','status':'concept_only'}]

@router.post('/materials/analyze')
async def analyze_image(file:UploadFile=File(...),user_id:str=Depends(get_current_user)):
    if file.content_type not in ('image/jpeg','image/png','image/webp'):
        raise HTTPException(415,'Use JPG, PNG or WEBP')
    blob=await file.read(MAX_BYTES+1)
    try:
        return await analyze(blob)
    except InvalidMaterialImage as e:
        raise HTTPException(422,str(e)) from e
    except QwenUnavailable as e:
        raise HTTPException(503,str(e)+'; manual material entry is available') from e

def persist_design(payload:DesignRequest,user_id:str,db:Session)->DesignCreated:
    try:
        scene=build_scene(payload)
    except NotFeasible as e:
        raise HTTPException(422,{'code':'NO_FEASIBLE_DESIGN','message':str(e)}) from e
    design_id=str(uuid4())
    base=f'/api/v1/designs/{design_id}'
    scene.model_glb_url=base+'/model.glb'
    for part in scene.components:
        part.part_model_url=f'{base}/parts/{part.id}.glb'
    folder=Path(settings().artifact_dir).resolve()/design_id
    folder.mkdir(parents=True,exist_ok=True)
    try:
        (folder/'model.glb').write_bytes(export_glb(scene))
        for p in scene.components:
            (folder/f'{p.id}.glb').write_bytes(export_glb(scene,p.id))
        db.add(Design(id=design_id,user_id=user_id,template_id=scene.template_id,
                      scene=scene.model_dump(mode='json')))
        db.commit()
    except Exception:
        db.rollback()
        # Local MVP files and DB are not one transaction; remove files on DB error.
        import shutil
        shutil.rmtree(folder,ignore_errors=True)
        raise
    return DesignCreated(design_id=design_id,scene_url=base+'/scene',model_glb_url=base+'/model.glb',scene=scene)

@router.post('/designs',status_code=201,response_model=DesignCreated)
def create_design(payload:DesignRequest,user_id:str=Depends(get_current_user),db:Session=Depends(get_db)):
    """Manual confirmed-data path; works even with Qwen offline."""
    return persist_design(payload,user_id,db)

@router.post('/reimagine',status_code=201)
async def reimagine_one_click(
    payload_json:str=Form(...),file:UploadFile|None=File(default=None),
    user_id:str=Depends(get_current_user),db:Session=Depends(get_db)):
    """One mobile action: optional Qwen image observation then deterministic approved design.

    App sends CONFIRMED dimensions in payload_json. Qwen does NOT generate dimensions or geometry.
    """
    try:
        payload=DesignRequest.model_validate_json(payload_json)
    except ValidationError as e:
        raise HTTPException(422,'Invalid or incomplete confirmed material and space details') from e
    observation=None
    if file is not None:
        if file.content_type not in ('image/jpeg','image/png','image/webp'):
            raise HTTPException(415,'Use JPG, PNG or WEBP')
        image=await file.read(MAX_BYTES+1)
        try:
            observation=await analyze(image)
        except InvalidMaterialImage as e:
            raise HTTPException(422,str(e)) from e
        except QwenUnavailable as e:
            raise HTTPException(503,str(e)+'; retry without photo after confirming materials') from e
        # An obvious mismatch is a reason to stop, not silently generate wood geometry.
        if observation.material_type.lower().strip() in ('metal','iron','steel','plastic','glass','ceramic'):
            raise HTTPException(422,{'code':'MATERIAL_MISMATCH',
                                     'message':'Photo appears incompatible with the wood-only MVP. Confirm material manually.'})
    result=persist_design(payload,user_id,db)
    return {'design':result.model_dump(mode='json'),
            'material_observation':observation.model_dump(mode='json') if observation else None,
            'note':'Only user-confirmed measurements were used for 3D geometry.'}

@router.get('/designs/{design_id}/scene',response_model=SceneSpec)
def get_scene(design_id:str,user_id:str=Depends(get_current_user),db:Session=Depends(get_db)):
    d=load_design(db,design_id,user_id)
    return SceneSpec.model_validate(d.scene)

@router.get('/designs/{design_id}/guidance/{part_id}')
def get_part_guide(design_id:str,part_id:str,user_id:str=Depends(get_current_user),db:Session=Depends(get_db)):
    d=load_design(db,design_id,user_id)
    scene=SceneSpec.model_validate(d.scene)
    if part_id not in scene.guidance:
        raise HTTPException(404,'Component not found')
    return scene.guidance[part_id]

@router.get('/designs/{design_id}/model.glb')
def get_glb(design_id:str,user_id:str=Depends(get_current_user),db:Session=Depends(get_db)):
    load_design(db,design_id,user_id)
    path=artifact_path(design_id,'model.glb')
    if not path.is_file():raise HTTPException(404,'3D file not found')
    return FileResponse(path,media_type='model/gltf-binary',filename='ray_model.glb')

@router.get('/designs/{design_id}/parts/{part_id}.glb')
def get_part_glb(design_id:str,part_id:str,user_id:str=Depends(get_current_user),db:Session=Depends(get_db)):
    d=load_design(db,design_id,user_id)
    scene=SceneSpec.model_validate(d.scene)
    if part_id not in scene.guidance:raise HTTPException(404,'Component not found')
    path=artifact_path(design_id,part_id+'.glb')
    if not path.is_file():raise HTTPException(404,'Part file not found')
    return FileResponse(path,media_type='model/gltf-binary',filename=f'{part_id}.glb')
