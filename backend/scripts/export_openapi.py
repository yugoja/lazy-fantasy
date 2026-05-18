"""
Export the FastAPI OpenAPI spec to a JSON file without starting a server.

Usage:
    cd /path/to/lazy-fantasy
    backend/venv/bin/python backend/scripts/export_openapi.py

Output:
    frontend/src/types/openapi.json
"""

import json
import sys
from pathlib import Path

# Ensure the backend package is importable
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# Minimal env so config doesn't blow up without a .env file
import os
os.environ.setdefault("SECRET_KEY", "export-script-placeholder")
os.environ.setdefault("DATABASE_URL", "postgresql://placeholder/placeholder")

from app.main import app  # noqa: E402  (import after sys.path manipulation)

OUTPUT_PATH = REPO_ROOT / "frontend" / "src" / "types" / "openapi.json"
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

spec = app.openapi()
OUTPUT_PATH.write_text(json.dumps(spec, indent=2) + "\n")
print(f"OpenAPI spec written to {OUTPUT_PATH}")
