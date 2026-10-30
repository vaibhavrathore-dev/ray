from fastapi import FastAPI
from app.database import Base,engine
from app.models import Design
from app.routes.reimagine import router

app=FastAPI(title='RAY: Reimagine + AR Backend',version='0.1.0',
    description='Fresh RAY 3D concept generator. Qwen observations -> confirmed stock -> approved JSON scene + GLB assets.')
Base.metadata.create_all(bind=engine) # Local MVP only; migrate using Alembic for production.
app.include_router(router)

@app.get('/health')
def health():
    return {'product':'RAY','status':'ok','qwen_status':'not_checked'}
