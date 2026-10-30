import os
os.environ['DATABASE_URL']='sqlite:///./test_ray.db'
os.environ['ARTIFACT_DIR']='./generated/test_suite'
import pytest
from fastapi.testclient import TestClient
from app.auth import get_current_user
from app.database import Base,engine
from app.main import app

@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_current_user]=lambda:'ray-test-owner'
    with TestClient(app) as c:yield c
    app.dependency_overrides.clear()
