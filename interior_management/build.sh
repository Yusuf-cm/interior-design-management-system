#!/usr/bin/env bash
set -eu

pip install -r requirements.txt

# Preserve installations that use a dedicated schema without creating users.
python - <<'PY'
import os
import psycopg2

admin_url = os.environ.get('ADMIN_DATABASE_URL')
if admin_url:
    with psycopg2.connect(admin_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute('CREATE SCHEMA IF NOT EXISTS studio')
PY

python manage.py collectstatic --noinput
python manage.py migrate --noinput
