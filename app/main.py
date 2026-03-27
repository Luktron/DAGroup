"""FastAPI application entry point."""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import CONFIG
from app.game.engine import GameManager
from app.game.ai import AIManager
from app.routes import lobby, game

# Create shared instances
game_mgr = GameManager()
ai_mgr = AIManager()

# Inject into route modules
lobby.game_manager = game_mgr
lobby.ai_manager = ai_mgr
game.game_manager = game_mgr
game.ai_manager = ai_mgr

app = FastAPI(
    title="Assassino da Piscada",
    description="Online multiplayer social deduction game",
    version="1.0.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/images", StaticFiles(directory="app/images"), name="images")

# Include routers
app.include_router(lobby.router)
app.include_router(game.router)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=CONFIG.HOST,
        port=CONFIG.PORT,
        reload=True,
    )
