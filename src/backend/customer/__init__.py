"""Customer module providing registration and KYC limit enforcement."""

from .router import router  # noqa: F401
from .service import CustomerRegistry, get_registry  # noqa: F401

