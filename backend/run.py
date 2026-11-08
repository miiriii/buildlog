"""Prepare outstanding Alembic revisions, then start the development server."""
from pathlib import Path
import sys


def main():
    from alembic import command
    from alembic.config import Config
    from app.core.config import Settings
    try:
        # Validate without printing settings, driver errors or credential values.
        settings = Settings()
        config = Config(str(Path(__file__).with_name('alembic.ini')))
        command.upgrade(config, 'head')
    except Exception:
        print('DB preparation failed. Check backend/.env DATABASE_URL, SECRET_KEY, Supabase project/network/SSL and permissions. No SQLite fallback was attempted.')
        return 1
    print('Database schema is ready. Existing migrations and data are preserved.')
    if not settings.openai_api_key.get_secret_value().strip():
        print('AI summary needs OPENAI_API_KEY in backend/.env; original-file storage remains available.')
    if '--prepare-only' not in sys.argv:
        import uvicorn
        uvicorn.run('app.main:app', host='127.0.0.1', port=8000, reload=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
