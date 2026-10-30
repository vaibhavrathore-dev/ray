"""RAY supported-template geometry. Neither AI interpretation nor visual geometry is a safety certificate.

All stock dimensions are user-confirmed; cannot infer dimensions from an image.
One source board per part (no nesting optimization). This deliberately limits MVP claims.
"""
from dataclasses import dataclass
from itertools import product
import numpy as np
import trimesh
from app.schemas import (DesignRequest, SceneSpec, Component, Guidance, CutPreview,
                         AssemblyStep, TargetDimensions)

class NotFeasible(ValueError):
    pass

@dataclass(frozen=True)
class StockUnit:
    id: str
    length: float
    width: float
    thickness: float

def units_from(req: DesignRequest):
    return [StockUnit(f'{b.source_id}#{i+1}', b.length_cm, b.width_cm, b.thickness_cm)
            for b in req.boards if b.condition == 'good' for i in range(b.quantity)]

def side_fits(stock: StockUnit, face_a: float, face_b: float, t: float) -> bool:
    # Deliberately require equal thickness within 0.05cm. Board faces can rotate 90 degrees.
    if abs(stock.thickness - t) > 0.05:
        return False
    return ((stock.length+1e-8 >= face_a and stock.width+1e-8 >= face_b) or
            (stock.length+1e-8 >= face_b and stock.width+1e-8 >= face_a))

def allocate(units: list[StockUnit], dim: TargetDimensions, t: float):
    w,h,d = dim.width_cm, dim.height_cm, dim.depth_cm
    if w-2*t < 20 or h <= 2*t:
        return None
    specs = {
        'left_side': (h,d),
        'right_side': (h,d),
        'bottom_shelf': (w-2*t,d),
        'top_shelf': (w-2*t,d),
    }
    candidates={part:[unit for unit in units if side_fits(unit,a,b,t)]
                for part,(a,b) in specs.items()}
    if any(not options for options in candidates.values()):
        return None
    order = sorted(specs, key=lambda p: (len(candidates[p]),-specs[p][0]))
    assignment={}
    used=set()
    def search(i):
        if i==len(order): return True
        part=order[i]
        for u in sorted(candidates[part], key=lambda u:u.length*u.width):
            if u.id in used: continue
            used.add(u.id); assignment[part]=u
            if search(i+1): return True
            used.remove(u.id); del assignment[part]
        return False
    return (specs,assignment) if search(0) else None

def choose(req: DesignRequest):
    stock=units_from(req)
    if len(stock)<4:
        raise NotFeasible('Four confirmed-good boards are required for this supported shelf template')
    if req.target:
        possibilities=[req.target]
    else:
        possibilities=[TargetDimensions(width_cm=w,height_cm=h,depth_cm=d)
                       for w,h,d in product([80,70,60,50,40],[50,45,40,35,30],[25,20,18,15,12])]
    thicknesses=sorted({round(u.thickness,2) for u in stock})
    for dim in possibilities:
        if (dim.width_cm+2 > req.space.width_cm or dim.height_cm+2 > req.space.height_cm
            or dim.depth_cm+2 > req.space.depth_cm):
            continue
        for t in thicknesses:
            result=allocate(stock,dim,t)
            if result:
                return dim,t,result[0],result[1]
    raise NotFeasible('No supported shelf fits this space and confirmed stock. Change dimensions or add suitable boards.')

def guidance_for(part_id, label, stock_unit):
    common_tools=['Measuring tape', 'Carpenter square', 'Clamps']
    info={
        'left_side': ('Left side panel', ['Verify panel dimensions and condition.', 'Preview the left side location in the 3D scene.', 'Hold the panel in position; only fasten after a suitable joint is independently verified.']),
        'right_side': ('Right side panel', ['Verify panel dimensions and condition.', 'Preview its alignment with the left side.', 'Confirm the assembly is supported before fastening.']),
        'bottom_shelf': ('Bottom shelf panel', ['Identify the assigned stock board.', 'Preview the bottom shelf position between both sides.', 'Verify clearance and safe joinery before assembly.']),
        'top_shelf': ('Top shelf panel', ['Identify the assigned stock board.', 'Preview top-panel alignment with both sides.', 'Do not load the shelf until fixings and stability are independently checked.']),
    }
    title, notes=info[part_id]
    return Guidance(component_id=part_id,title=title,instructions=notes,
                    tools_required=common_tools,notes=[f'Stock: {stock_unit.id}', 'Check the approved cut preview before any fabrication.'],
                    caution='Concept guidance only: no structural loads, fastener placements, or cut safety are certified.')

def build_scene(req: DesignRequest) -> SceneSpec:
    dim,t,specs,assigned=choose(req)
    w,h,d=dim.width_cm,dim.height_cm,dim.depth_cm
    entries=[
      ('left_side','Left side',[t,h,d],[-w/2+t/2,h/2,0],'#a77345'),
      ('right_side','Right side',[t,h,d],[w/2-t/2,h/2,0],'#a77345'),
      ('bottom_shelf','Bottom shelf',[w-2*t,t,d],[0,t/2,0],'#bb8957'),
      ('top_shelf','Top shelf',[w-2*t,t,d],[0,h-t/2,0],'#bb8957'),
    ]
    components=[]; guides={}; cuts=[]
    for part_id,label,cm_dims,cm_pos,color in entries:
        stock=assigned[part_id]
        components.append(Component(id=part_id,label=label,dimensions_m=[round(v/100,6) for v in cm_dims],
            position_m=[round(v/100,6) for v in cm_pos],color_hex=color,stock_unit_id=stock.id))
        guides[part_id]=guidance_for(part_id,label,stock)
        a,b=specs[part_id]
        cuts.append(CutPreview(component_id=part_id,stock_unit_id=stock.id,
            required_face_cm=[round(a,2),round(b,2)],source_face_cm=[stock.length,stock.width],thickness_cm=t))
    steps=[
        AssemblyStep(step=1,title='Identify and verify materials',component_ids=[],
                     description='Inspect each board and verify material, dimensions and potential defects.'),
        AssemblyStep(step=2,title='Preview the side panels',component_ids=['left_side','right_side'],
                     description='Use the 3D view to understand the intended location of both side panels.'),
        AssemblyStep(step=3,title='Preview the bottom shelf',component_ids=['bottom_shelf'],
                     description='Review the bottom panel location and its relationship with side panels.'),
        AssemblyStep(step=4,title='Preview the top shelf',component_ids=['top_shelf'],
                     description='Review top-panel alignment; confirm safe fastener design externally.'),
    ]
    return SceneSpec(title='RAY Mini Shelf — Concept Preview',template_id='mini_shelf_v1',
        outer_dimensions_cm=dim,components=components,guidance=guides,cut_previews=cuts,
        assembly_steps=steps,project_tools=['Measuring tape','Carpenter square','Clamps','Appropriate safety equipment'],
        missing_supplies=['Suitable verified fixings / joinery','Additional tools if required by reviewed assembly plan'],
        safety_notes=['Concept only: not a certified fabrication or load-bearing design.',
                      'Confirm physical dimensions and material condition manually.',
                      'AR tracking and positioning are approximate; do not use for accurate cutting or drilling.',
                      'Get joinery, load capacity and stability independently verified before construction.'])

def _mesh(part: Component, *, transformed: bool):
    mesh=trimesh.creation.box(extents=np.asarray(part.dimensions_m,dtype=float))
    rgba=[int(part.color_hex[i:i+2],16) for i in (1,3,5)]+[255]
    mesh.visual.vertex_colors=np.tile(np.asarray(rgba,dtype=np.uint8),(len(mesh.vertices),1))
    matrix=np.eye(4)
    if transformed: matrix[:3,3]=part.position_m
    return mesh,matrix

def export_glb(scene: SceneSpec, part_id: str | None=None) -> bytes:
    result=trimesh.Scene()
    parts=[c for c in scene.components if part_id is None or c.id==part_id]
    if not parts:
        raise KeyError(part_id)
    for p in parts:
        mesh,mat=_mesh(p,transformed=part_id is None)
        result.add_geometry(mesh,geom_name=p.id,node_name=p.id,transform=mat)
    return result.export(file_type='glb')
