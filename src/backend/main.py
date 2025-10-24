"""ASGI entry-point for the USDT Auction backend."""

from .core.app import create_app

app = create_app()

