"""Award engine module (Stage 15)."""

from .router import router
from .service import AwardEngine, get_award_engine

__all__ = ["AwardEngine", "get_award_engine", "router"]
