"""Sandeep's Windows Ollama server; *only* interpreted material JSON, never GLB or measurements."""
import base64
import httpx
from io import BytesIO
from PIL import Image,UnidentifiedImageError
from pydantic import ValidationError
from app.config import settings
from app.schemas import Observation

MAX_BYTES=10*1024*1024
class QwenUnavailable(Exception): pass
class InvalidMaterialImage(Exception): pass

def validate_image(blob: bytes):
    if not blob or len(blob)>MAX_BYTES:
        raise InvalidMaterialImage('Upload a JPG, PNG or WEBP image of at most 10 MB')
    try:
        with Image.open(BytesIO(blob)) as img:
            if img.format not in ('JPEG','PNG','WEBP') or min(img.size)<50:
                raise InvalidMaterialImage('Use JPG, PNG or WEBP at least 50x50 pixels')
            img.verify()
    except (UnidentifiedImageError,OSError,ValueError) as e:
        raise InvalidMaterialImage('Invalid image contents') from e

async def analyze(blob: bytes) -> Observation:
    validate_image(blob)
    cfg=settings()
    payload={
        'model':cfg.ollama_model,'stream':False,
        'format':Observation.model_json_schema(),
        'options':{'temperature':0.1,'num_ctx':8192},
        'messages':[{'role':'user',
            'content':('Return only JSON describing what is visible in this material image. '
                       'Do not infer sizes, thicknesses, structural safety, wood species, '
                       'material composition percentages or hidden properties. '
                       'If uncertain, say so and require manual confirmation.'),
            'images':[base64.b64encode(blob).decode('ascii')]}],
    }
    try:
        async with httpx.AsyncClient(timeout=cfg.ollama_timeout_seconds) as client:
            response=await client.post(cfg.ollama_base_url.rstrip('/')+'/api/chat',json=payload)
            response.raise_for_status()
            content=response.json()['message']['content']
            result=Observation.model_validate_json(content)
            return result
    except (httpx.HTTPError,KeyError,TypeError,ValueError,ValidationError) as e:
        raise QwenUnavailable('Qwen inference is unavailable or returned invalid observations') from e
