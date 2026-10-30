from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class Space(BaseModel):
    width_cm: float = Field(gt=0, le=600)
    height_cm: float = Field(gt=0, le=400)
    depth_cm: float = Field(gt=0, le=400)

class BoardStock(BaseModel):
    source_id: str = Field(min_length=1, max_length=64, pattern=r'^[a-zA-Z0-9_-]+$')
    material_type: Literal['wood', 'plywood'] = 'wood'
    length_cm: float = Field(gt=0, le=600)
    width_cm: float = Field(gt=0, le=300)
    thickness_cm: float = Field(gt=0.3, le=8)
    quantity: int = Field(ge=1, le=25, default=1)
    condition: Literal['good', 'fair', 'unknown', 'damaged'] = 'unknown'

class TargetDimensions(BaseModel):
    width_cm: float = Field(ge=35, le=100)
    height_cm: float = Field(ge=30, le=90)
    depth_cm: float = Field(ge=12, le=40)

class DesignRequest(BaseModel):
    template_id: Literal['mini_shelf_v1'] = 'mini_shelf_v1'
    space: Space
    boards: list[BoardStock] = Field(min_length=1, max_length=25)
    target: TargetDimensions | None = None

    @model_validator(mode='after')
    def unique_board_source(self):
        ids = [b.source_id for b in self.boards]
        if len(ids) != len(set(ids)):
            raise ValueError('Each stock source_id must be unique')
        if sum(b.quantity for b in self.boards) > 60:
            raise ValueError('Maximum 60 boards across all stock entries')
        return self

class Observation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    material_type: str = Field(max_length=80)
    visible_condition: str = Field(max_length=100)
    visible_features: list[str] = Field(default_factory=list)
    visible_defects: list[str] = Field(default_factory=list)
    uncertainty_notes: list[str] = Field(default_factory=list)
    needs_manual_confirmation: bool = True

class Guidance(BaseModel):
    component_id: str
    title: str
    instructions: list[str]
    tools_required: list[str]
    notes: list[str] = Field(default_factory=list)
    caution: str

class Component(BaseModel):
    id: str
    label: str
    shape: Literal['box'] = 'box'
    dimensions_m: list[float] = Field(min_length=3, max_length=3)
    position_m: list[float] = Field(min_length=3, max_length=3)
    rotation_deg: list[float] = Field(default_factory=lambda: [0,0,0])
    color_hex: str
    stock_unit_id: str
    part_model_url: str | None = None

class CutPreview(BaseModel):
    component_id: str
    stock_unit_id: str
    required_face_cm: list[float]
    source_face_cm: list[float]
    thickness_cm: float

class AssemblyStep(BaseModel):
    step: int
    title: str
    component_ids: list[str]
    description: str

class SceneSpec(BaseModel):
    schema_version: Literal['1.0.0'] = '1.0.0'
    title: str
    template_id: str
    units: Literal['meters'] = 'meters'
    coordinate_system: str = 'right-handed; +x right, +y up, +z depth; origin at floor center'
    outer_dimensions_cm: TargetDimensions
    components: list[Component]
    guidance: dict[str, Guidance]
    assembly_steps: list[AssemblyStep]
    cut_previews: list[CutPreview]
    project_tools: list[str]
    missing_supplies: list[str]
    safety_notes: list[str]
    model_glb_url: str | None = None

    @model_validator(mode='after')
    def verify_links(self):
        ids = [p.id for p in self.components]
        if len(ids) != len(set(ids)) or set(ids) != set(self.guidance):
            raise ValueError('Each unique 3D component must have exactly one guidance entry')
        if any(s.component_ids and not set(s.component_ids).issubset(ids) for s in self.assembly_steps):
            raise ValueError('Assembly step references unknown components')
        if any(c.component_id != k for k,c in self.guidance.items()):
            raise ValueError('Guidance IDs do not match keys')
        return self

class DesignCreated(BaseModel):
    design_id: str
    scene_url: str
    model_glb_url: str
    scene: SceneSpec
