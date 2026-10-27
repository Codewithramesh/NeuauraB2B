from alembic import context
from sqlalchemy import create_engine, pool
from backend.app.config import Settings
from backend.app.models import Base

config = context.config
settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
url = settings.database_url
if context.is_offline_mode():
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()
