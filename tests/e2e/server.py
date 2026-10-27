"""ISOLATED BROWSER TEST SERVER — explicit test doubles, never production data."""
import tempfile
from pathlib import Path
from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.models import Base,Organization,User
from backend.app.security import password_hash
from tests.conftest import TestSpeechProvider,TestExtractionProvider
test_data=Path(tempfile.mkdtemp(prefix='neuaura-e2e-'))
settings=Settings(data_dir=test_data,database_url=f'sqlite:///{test_data / "test.sqlite3"}',worker_enabled=True,llm_base_url='http://127.0.0.1:1',allow_cloud=False,_env_file=None)
app=create_app(settings,transcriber=TestSpeechProvider(),extractor=TestExtractionProvider())
Base.metadata.create_all(app.state.engine)
with app.state.factory() as db:
    org=Organization(name='NEUAURA test workspace',industry='restaurant');db.add(org);db.flush()
    db.add(User(org_id=org.id,email='browser@example.test',password_hash=password_hash('browser-test-password')));db.commit()
