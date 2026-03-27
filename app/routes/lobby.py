"""Lobby and room management routes."""

from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import CONFIG, TRANSLATIONS
from app.game.engine import GameManager
from app.game.ai import AIManager

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Shared instances (set from main.py)
game_manager: GameManager | None = None
ai_manager: AIManager | None = None


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
    gender: str = Form("m"),
):
    name = _validate_name(player_name)
    max_p = max(CONFIG.MIN_PLAYERS, min(CONFIG.MAX_PLAYERS, max_players))
    g = gender.strip().lower()[:1]
    if g not in ("m", "f"):
        g = "m"
    player_id = f"p_{uuid.uuid4().hex[:10]}"
    room = game_manager.create_room(creator_id=player_id, max_players=max_p, lang=lang)
    room.add_player(player_id, name, gender=g)

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
    gender: str = Form("m"),
):
    name = _validate_name(player_name)
    code = room_code.strip().upper()[:6]
    code = re.sub(r'[^A-Z0-9]', '', code)
    g = gender.strip().lower()[:1]
    if g not in ("m", "f"):
        g = "m"
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

    # Allow mid-game join if there's an AI slot to replace
    if room.phase.value != "lobby":
        # Check for an AI bot that can be replaced by this human
        ai_player = next((p for p in room.players.values() if p.is_ai), None)
        if ai_player:
            player_id = f"p_{uuid.uuid4().hex[:10]}"
            # Replace AI with the human player (keeping role and status)
            old_role = ai_player.role
            old_status = ai_player.status
            old_color = ai_player.avatar_color
            old_ai_id = ai_player.id

            room.remove_player(old_ai_id)

            # Remove from AIManager bot list
            if room.room_code in ai_manager.bots:
                ai_manager.bots[room.room_code] = [
                    b for b in ai_manager.bots[room.room_code]
                    if b.player_id != old_ai_id
                ]

            new_player = room.add_player(player_id, name, is_ai=False, gender=g)
            if new_player:
                new_player.role = old_role
                new_player.status = old_status
                new_player.avatar_color = old_color
                return RedirectResponse(
                    url=f"/game/{room.room_code}?pid={player_id}&lang={lang}",
                    status_code=303,
                )

        t = TRANSLATIONS.get(lang, TRANSLATIONS["pt"])
        return templates.TemplateResponse("index.html", {
            "request": request,
            "t": t,
            "lang": lang,
            "config": CONFIG,
            "error": "Jogo já iniciado / Game already started",
        })

    player_id = f"p_{uuid.uuid4().hex[:10]}"
    player = room.add_player(player_id, name, gender=g)

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

    # Validate player exists in the room
    if pid not in room.players:
        return RedirectResponse(url=f"/?lang={lang}")

    return templates.TemplateResponse("game.html", {
        "request": request,
        "t": t,
        "lang": lang,
        "room_code": room_code,
        "player_id": pid,
        "config": CONFIG,
    })
