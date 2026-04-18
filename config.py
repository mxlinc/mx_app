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

SECRET_KEY = os.getenv("SECRET_KEY", "devsecret")

# Package data path - use local test directory in development, /data/mont on render
# Auto-detect: if /data/mont exists (Render), use it; otherwise use local test data
if os.path.exists("/data/mont"):
    PACKAGE_DATA_PATH = os.getenv("PACKAGE_DATA_PATH", "/data/mont")
else:
    PACKAGE_DATA_PATH = os.getenv("PACKAGE_DATA_PATH", "./test_data/packages")
