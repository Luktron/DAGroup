"""Lobby and room management routes."""

from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import CONFIG, TRANSLATIONS
from app.game.engine import GameManager

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Shared game manager instance (set from main.py)
game_manager: GameManager | None = None


def _validate_name(name: str) -> str:
    """Sanitize and validate player name."""
    name = name.strip()[:20]
    name = re.sub(r'[<>&"\']', '', name)
    return name if name else "Jogador"


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    lang = request.query_params.get("lang", CONFIG.DEFAULT_LANG)
    t = TRANSLATIONS.get(lang, TRANSLATIONS["pt"])
    return templates.TemplateResponse("index.html", {
        "request": request,
        "t": t,
        "lang": lang,
        "config": CONFIG,
    })


@router.post("/create-room")
async def create_room(
    request: Request,
    player_name: str = Form(...),
    max_players: int = Form(CONFIG.DEFAULT_PLAYERS),
    lang: str = Form(CONFIG.DEFAULT_LANG),
):
    name = _validate_name(player_name)
    max_p = max(CONFIG.MIN_PLAYERS, min(CONFIG.MAX_PLAYERS, max_players))
    player_id = f"p_{uuid.uuid4().hex[:10]}"
    room = game_manager.create_room(creator_id=player_id, max_players=max_p, lang=lang)
    room.add_player(player_id, name)

    return RedirectResponse(
        url=f"/lobby/{room.room_code}?pid={player_id}&lang={lang}",
        status_code=303,
    )


@router.post("/join-room")
async def join_room(
    request: Request,
    player_name: str = Form(...),
    room_code: str = Form(...),
    lang: str = Form(CONFIG.DEFAULT_LANG),
):
    name = _validate_name(player_name)
    code = room_code.strip().upper()[:6]
    code = re.sub(r'[^A-Z0-9]', '', code)
    room = game_manager.get_room(code)

    if not room:
        t = TRANSLATIONS.get(lang, TRANSLATIONS["pt"])
        return templates.TemplateResponse("index.html", {
            "request": request,
            "t": t,
            "lang": lang,
            "config": CONFIG,
            "error": "Sala não encontrada / Room not found",
        })

    if room.phase.value != "lobby":
        t = TRANSLATIONS.get(lang, TRANSLATIONS["pt"])
        return templates.TemplateResponse("index.html", {
            "request": request,
            "t": t,
            "lang": lang,
            "config": CONFIG,
            "error": "Jogo já iniciado / Game already started",
        })

    player_id = f"p_{uuid.uuid4().hex[:10]}"
    player = room.add_player(player_id, name)

    if not player:
        t = TRANSLATIONS.get(lang, TRANSLATIONS["pt"])
        return templates.TemplateResponse("index.html", {
            "request": request,
            "t": t,
            "lang": lang,
            "config": CONFIG,
            "error": t["room_full"],
        })

    return RedirectResponse(
        url=f"/lobby/{room.room_code}?pid={player_id}&lang={lang}",
        status_code=303,
    )


@router.get("/lobby/{room_code}", response_class=HTMLResponse)
async def lobby(request: Request, room_code: str):
    pid = request.query_params.get("pid", "")
    lang = request.query_params.get("lang", CONFIG.DEFAULT_LANG)
    t = TRANSLATIONS.get(lang, TRANSLATIONS["pt"])

    room = game_manager.get_room(room_code)
    if not room:
        return RedirectResponse(url=f"/?lang={lang}")

    return templates.TemplateResponse("lobby.html", {
        "request": request,
        "t": t,
        "lang": lang,
        "room": room.get_lobby_state(),
        "player_id": pid,
        "config": CONFIG,
    })


@router.get("/game/{room_code}", response_class=HTMLResponse)
async def game_view(request: Request, room_code: str):
    pid = request.query_params.get("pid", "")
    lang = request.query_params.get("lang", CONFIG.DEFAULT_LANG)
    t = TRANSLATIONS.get(lang, TRANSLATIONS["pt"])

    room = game_manager.get_room(room_code)
    if not room:
        return RedirectResponse(url=f"/?lang={lang}")

    return templates.TemplateResponse("game.html", {
        "request": request,
        "t": t,
        "lang": lang,
        "room_code": room_code,
        "player_id": pid,
        "config": CONFIG,
    })
