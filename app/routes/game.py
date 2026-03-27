"""Game WebSocket routes — real-time game communication."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.game.engine import GameManager, GamePhase
from app.game.ai import AIManager
from app.sockets.manager import manager as ws_manager

router = APIRouter()

# Shared instances (set from main.py)
game_manager: GameManager | None = None
ai_manager: AIManager | None = None

# Background tasks per room
_game_loops: dict[str, asyncio.Task] = {}


async def _game_tick_loop(room_code: str):
    """Background loop that processes game ticks for a room."""
    try:
        while True:
            room = game_manager.get_room(room_code)
            if not room or room.phase != GamePhase.PLAYING:
                break

            # Process pending kills
            deaths = room.process_pending_kills()
            room.check_blackout()

            if deaths or room.phase == GamePhase.FINISHED:
                await ws_manager.broadcast_state(room_code, room)

                if room.phase == GamePhase.FINISHED:
                    ai_manager.stop_bots(room_code)
                    break

            await asyncio.sleep(0.5)
    except asyncio.CancelledError:
        pass
    finally:
        _game_loops.pop(room_code, None)


def _start_game_loop(room_code: str):
    if room_code not in _game_loops:
        _game_loops[room_code] = asyncio.create_task(_game_tick_loop(room_code))


@router.websocket("/ws/{room_code}/{player_id}")
async def game_websocket(ws: WebSocket, room_code: str, player_id: str):
    room = game_manager.get_room(room_code)
    if not room or player_id not in room.players:
        await ws.close(code=4001)
        return

    await ws_manager.connect(ws, room_code, player_id)

    try:
        # Send initial state
        if room.phase == GamePhase.LOBBY:
            await ws_manager.broadcast_to_room(room_code, {
                "type": "lobby_update",
                "state": room.get_lobby_state(),
            })
        else:
            state = room.get_state_for_player(player_id)
            await ws_manager.send_to_player(player_id, {
                "type": "state_update",
                "state": state,
            })

        # Set up broadcast callback for AI
        async def broadcast_cb(data):
            await ws_manager.broadcast_to_room(room_code, data)

        async def send_to_cb(pid, data):
            await ws_manager.send_to_player(pid, data)

        room.set_callbacks(broadcast_cb, send_to_cb)

        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type", "")

            if msg_type == "start_game":
                await _handle_start_game(room_code, player_id)

            elif msg_type == "fill_ai":
                await _handle_fill_ai(room_code, player_id)

            elif msg_type == "kill":
                await _handle_kill(room_code, player_id, data)

            elif msg_type == "investigate":
                await _handle_investigate(room_code, player_id, data)

            elif msg_type == "accuse":
                await _handle_accuse(room_code, player_id, data)

            elif msg_type == "look":
                await _handle_look(room_code, player_id, data)

            elif msg_type == "chat":
                await _handle_chat(room_code, player_id, data)

            elif msg_type == "play_again":
                await _handle_play_again(room_code, player_id)

            elif msg_type == "ping":
                await ws_manager.send_to_player(player_id, {"type": "pong"})

    except WebSocketDisconnect:
        ws_manager.disconnect(player_id)
        room = game_manager.get_room(room_code)
        if room:
            if room.phase == GamePhase.PLAYING:
                # Replace with AI
                bot_id = ai_manager.replace_player(room, player_id)
                if bot_id:
                    await ws_manager.broadcast_to_room(room_code, {
                        "type": "player_replaced",
                        "old_id": player_id,
                        "new_id": bot_id,
                    })
                await ws_manager.broadcast_state(room_code, room)
            elif room.phase == GamePhase.LOBBY:
                room.remove_player(player_id)
                await ws_manager.broadcast_to_room(room_code, {
                    "type": "lobby_update",
                    "state": room.get_lobby_state(),
                })


async def _handle_start_game(room_code: str, player_id: str):
    room = game_manager.get_room(room_code)
    if not room or room.creator_id != player_id:
        return

    if room.start_game():
        ai_manager.start_bots(room_code)
        _start_game_loop(room_code)

        # Send state to each player (with their role revealed privately)
        await ws_manager.broadcast_to_room(room_code, {
            "type": "game_started",
            "redirect": f"/game/{room_code}",
        })
        await asyncio.sleep(0.3)
        await ws_manager.broadcast_state(room_code, room)


async def _handle_fill_ai(room_code: str, player_id: str):
    room = game_manager.get_room(room_code)
    if not room or room.creator_id != player_id:
        return
    if room.phase != GamePhase.LOBBY:
        return

    ai_manager.fill_room(room)
    await ws_manager.broadcast_to_room(room_code, {
        "type": "lobby_update",
        "state": room.get_lobby_state(),
    })


async def _handle_kill(room_code: str, player_id: str, data: dict):
    room = game_manager.get_room(room_code)
    if not room:
        return

    target_id = data.get("target_id", "")
    result = room.assassin_kill(player_id, target_id)

    await ws_manager.send_to_player(player_id, {
        "type": "kill_result",
        "result": result,
    })

    if result.get("success"):
        # Broadcast noise events to everyone (not the actual kill)
        await ws_manager.broadcast_state(room_code, room)


async def _handle_investigate(room_code: str, player_id: str, data: dict):
    room = game_manager.get_room(room_code)
    if not room:
        return

    suspect_id = data.get("target_id", "")
    result = room.detective_investigate(player_id, suspect_id)

    await ws_manager.send_to_player(player_id, {
        "type": "investigate_result",
        "result": result,
    })


async def _handle_accuse(room_code: str, player_id: str, data: dict):
    room = game_manager.get_room(room_code)
    if not room:
        return

    suspect_id = data.get("target_id", "")
    result = room.detective_accuse(player_id, suspect_id)

    if result.get("success"):
        await ws_manager.broadcast_to_room(room_code, {
            "type": "accusation",
            "detective_id": player_id,
            "suspect_id": suspect_id,
            "correct": result.get("correct", False),
            "message": result.get("message", ""),
        })
        await ws_manager.broadcast_state(room_code, room)

        if room.phase == GamePhase.FINISHED:
            ai_manager.stop_bots(room_code)
    else:
        await ws_manager.send_to_player(player_id, {
            "type": "accuse_error",
            "result": result,
        })


async def _handle_look(room_code: str, player_id: str, data: dict):
    room = game_manager.get_room(room_code)
    if not room:
        return

    target_id = data.get("target_id", "")
    result = room.player_look(player_id, target_id)

    if result.get("success"):
        # Notify all players about the look (social info)
        target = room.players.get(target_id)
        actor = room.players.get(player_id)
        if target and actor:
            await ws_manager.broadcast_to_room(room_code, {
                "type": "look_event",
                "actor_id": player_id,
                "actor_name": actor.name,
                "target_id": target_id,
                "target_name": target.name,
            })


async def _handle_chat(room_code: str, player_id: str, data: dict):
    room = game_manager.get_room(room_code)
    if not room:
        return

    player = room.players.get(player_id)
    if not player or player.status.value == "dead":
        return

    import re
    message = data.get("message", "").strip()[:200]
    message = re.sub(r'[<>]', '', message)
    if not message:
        return

    await ws_manager.broadcast_to_room(room_code, {
        "type": "chat_message",
        "player_id": player_id,
        "player_name": player.name,
        "message": message,
        "avatar_color": player.avatar_color,
    })


async def _handle_play_again(room_code: str, player_id: str):
    room = game_manager.get_room(room_code)
    if not room or room.creator_id != player_id:
        return

    room.reset_for_new_round()
    ai_manager.start_bots(room_code)
    _start_game_loop(room_code)

    await ws_manager.broadcast_to_room(room_code, {
        "type": "game_restarted",
    })
    await asyncio.sleep(0.3)
    await ws_manager.broadcast_state(room_code, room)
