"""Isolated real-provider UI verification. Test login only; never touches the user's workspace."""
import tempfile
from pathlib import Path
from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.models import Base, Organization, User
from backend.app.security import password_hash

test_data=Path(tempfile.mkdtemp(prefix='neuaura-real-ui-'))
settings=Settings(data_dir=test_data,database_url=f'sqlite:///{test_data / "test.sqlite3"}',worker_enabled=True)
settings.allowed_hosts=list(set(settings.allowed_hosts+['127.0.0.1','localhost']))
app=create_app(settings)
Base.metadata.create_all(app.state.engine)
with app.state.factory() as db:
    org=Organization(name='NEUAURA real-engine verification',industry='restaurant');db.add(org);db.flush()
    db.add(User(org_id=org.id,email='real-ui@example.test',password_hash=password_hash('isolated-real-ui-test')));db.commit()
