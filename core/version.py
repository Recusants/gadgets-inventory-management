"""
Automatic Version Tracking Engine for Clarity Retail: Gadgets store.
Tracks version metrics dynamically on git commits/pushes with persistent caching to version.json.
"""
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
VERSION_FILE = BASE_DIR / 'version.json'
SYSTEM_NAME = "Clarity Retail: Gadgets store"
SHORT_NAME = "Clarity Retail"
BASE_VERSION = "2.4"


def get_git_info():
    """Extract latest git commit count, short hash, date, and branch."""
    base_dir = str(BASE_DIR)

    
    # 1. Total commit count
    try:
        count = subprocess.check_output(
            ['git', 'rev-list', '--count', 'HEAD'],
            cwd=base_dir, stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()
    except Exception:
        count = None

    # 2. Short commit hash
    try:
        commit_hash = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=base_dir, stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()
    except Exception:
        commit_hash = None

    # 3. Commit date
    try:
        commit_date = subprocess.check_output(
            ['git', 'log', '-1', '--format=%cd', '--date=format:%Y-%m-%d %H:%M'],
            cwd=base_dir, stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()
    except Exception:
        commit_date = None

    # 4. Latest commit subject
    try:
        commit_subject = subprocess.check_output(
            ['git', 'log', '-1', '--format=%s'],
            cwd=base_dir, stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()
    except Exception:
        commit_subject = "Initial commit"

    # 5. Current branch
    try:
        branch = subprocess.check_output(
            ['git', 'branch', '--show-current'],
            cwd=base_dir, stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()
    except Exception:
        branch = 'main'

    return {
        'count': count,
        'hash': commit_hash,
        'date': commit_date,
        'subject': commit_subject,
        'branch': branch or 'main'
    }

def update_version_file():
    """
    Generates and saves version.json based on current git state.
    Calculates semantic version v{BASE_VERSION}.{commit_count} and build v{BASE_VERSION}.{commit_count}-{hash}.
    """
    git_info = get_git_info()
    commit_count = int(git_info['count']) if git_info['count'] and git_info['count'].isdigit() else 1
    short_hash = git_info['hash'] or 'local'
    commit_date = git_info['date'] or datetime.now().strftime('%Y-%m-%d %H:%M')
    branch = git_info['branch'] or 'main'

    version_str = f"v{BASE_VERSION}.{commit_count}"
    build_str = f"{version_str}-{short_hash}"

    version_data = {
        'system_name': SYSTEM_NAME,
        'short_name': SHORT_NAME,
        'version': version_str,
        'build': build_str,
        'commit_count': commit_count,
        'commit_hash': short_hash,
        'branch': branch,
        'commit_subject': git_info.get('subject', ''),
        'updated_at': commit_date,
        'last_pushed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    try:
        with open(VERSION_FILE, 'w', encoding='utf-8') as f:
            json.dump(version_data, f, indent=2)
    except Exception:
        pass

    return version_data

def get_system_version():
    """
    Returns the active system version. Checks if live git state has advanced beyond version.json.
    """
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if live git has a newer commit hash
            git_info = get_git_info()
            if git_info['hash'] and git_info['hash'] != data.get('commit_hash'):
                return update_version_file()
            return data
        except Exception:
            return update_version_file()
    else:
        return update_version_file()

if __name__ == '__main__':
    v = update_version_file()
    print(f"Updated Clarity Retail version: {v['build']} ({v['updated_at']})")
