"""Application configuration."""

import os
from dotenv import load_dotenv

load_dotenv()

# ✅ Database URL from .env or Render
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set.")

# ✅ Use psycopg (v3) driver
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+psycopg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# Schema
CURRENT_SCHEMA = os.getenv("APP_SCHEMA", "prod")

# Math renderer: 'katex' (default, uses node katex_render.js) or 'mathml' (fallback, no node needed)
LATEX_RENDERER = os.getenv("LATEX_RENDERER", "katex")

SECRET_KEY = os.getenv("SECRET_KEY", "devsecret")

# Package data path - use local test directory in development, /data/mont on render
# Auto-detect: check for /data mount point (Render persistent disk), not the subdir
_on_render = os.path.isdir("/data")

# Package data path
if _on_render:
    PACKAGE_DATA_PATH = os.getenv("PACKAGE_DATA_PATH", "/data/mont")
else:
    PACKAGE_DATA_PATH = os.getenv("PACKAGE_DATA_PATH", "./test_data/packages")

# Image storage — /data/qimage on Render (created on first save), OneDrive folder locally
if _on_render:
    QIMAGE_PATH = os.getenv("QIMAGE_PATH", "/data/qimage")
else:
    QIMAGE_PATH = os.getenv("QIMAGE_PATH", r"C:\OneDrive--MEInc\OneDrive\0000 - Montessori Online\qimage")
