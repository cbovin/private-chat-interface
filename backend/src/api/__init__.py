"""
FastAPI router modules.
"""
from .auth import router as auth
from .user import router as user
from .workspace import router as workspace
from .chat import router as chat
from .health import router as health
from .metric import router as metric
