"""Vercel serverless entrypoint for the FastAPI application."""

from app.main import app

# Export app as handler for Vercel
handler = app
