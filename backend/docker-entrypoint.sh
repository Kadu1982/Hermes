#!/bin/sh
set -e

echo "Waiting for database..."
until python -c "
import os
from sqlalchemy import create_engine, text
url = os.environ['HERMES_DATABASE_URL']
engine = create_engine(url, pool_pre_ping=True)
with engine.connect() as c:
    c.execute(text('SELECT 1'))
" 2>/dev/null; do
  sleep 1
done

echo "Running migrations..."
alembic upgrade head

echo "Bootstrapping admin (no-op if user exists)..."
python -m app.scripts.bootstrap_admin

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
