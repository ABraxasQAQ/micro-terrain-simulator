"""Runtime helpers for MT-prefixed scripts in the project root."""

from __future__ import annotations

import os
import sys
from pathlib import Path


MT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MT_DIR


def ensure_project_root() -> Path:
    """Run from the teacher project's root so legacy files stay in one place."""
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    if str(MT_DIR) not in sys.path:
        sys.path.insert(0, str(MT_DIR))
    os.chdir(PROJECT_ROOT)
    return PROJECT_ROOT
