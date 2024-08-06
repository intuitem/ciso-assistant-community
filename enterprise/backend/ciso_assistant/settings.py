import os

from backend.settings import FEATURE_FLAGS

FEATURE_FLAGS["enterprise"] = os.environ.get("FF_ENTERPRISE", "false") == "true"
