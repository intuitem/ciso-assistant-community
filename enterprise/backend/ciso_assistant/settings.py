import os

from ciso_assistant.settings import *

FEATURE_FLAGS = {
    "enterprise": os.environ.get("FF_ENTERPRISE", "false") == "true",
}
