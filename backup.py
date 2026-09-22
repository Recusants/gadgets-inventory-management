"""
Nightly Automated Database Backup Engine for 21 Void Technologies.
Backs up SQLite or PostgreSQL databases into dated backup folders.
"""

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BACKUPS_DIR = BASE_DIR / 'backups'
BACKUPS_DIR.mkdir(exist_ok=True)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

def backup_sqlite():
    """Backup local SQLite database."""
    db_file = BASE_DIR / 'db.sqlite3'
    if not db_file.exists():
        print(f"Database file not found: {db_file}")
        return False
    
    backup_file = BACKUPS_DIR / f"db_backup_{timestamp}.sqlite3"
    shutil.copy2(db_file, backup_file)
    print(f"[SUCCESS] SQLite database backed up to: {backup_file} ({backup_file.stat().st_size} bytes)")
    return True

def backup_postgres():
    """Backup PostgreSQL database via pg_dump."""
    db_name = os.environ.get('POSTGRES_DB', 'twentyone_void_prod_db')
    db_user = os.environ.get('POSTGRES_USER', 'postgres')
    db_host = os.environ.get('POSTGRES_HOST', 'localhost')
    db_port = os.environ.get('POSTGRES_PORT', '5432')
    
    backup_file = BACKUPS_DIR / f"pg_backup_{timestamp}.sql"
    cmd = [
        'pg_dump',
        '-h', db_host,
        '-p', str(db_port),
        '-U', db_user,
        '-F', 'c',
        '-b',
        '-v',
        '-f', str(backup_file),
        db_name
    ]
    try:
        subprocess.run(cmd, check=True)
        print(f"[SUCCESS] PostgreSQL database backed up to: {backup_file}")
        return True
    except Exception as e:
        print(f"[ERROR] pg_dump failed: {e}")
        return False

if __name__ == '__main__':
    print(f"Starting 21 Void Technologies backup at {datetime.now()}...")
    # Check if SQLite exists
    if (BASE_DIR / 'db.sqlite3').exists():
        backup_sqlite()
    elif os.environ.get('POSTGRES_DB'):
        backup_postgres()
    else:
        print("No active database detected.")
