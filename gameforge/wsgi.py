"""
WSGI/ASGI application entry point for production deployment.
"""
from gameforge.app import app

# This is the entry point for gunicorn
# Usage: gunicorn gameforge.wsgi:app
application = app