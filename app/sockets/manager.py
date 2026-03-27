"""WebSocket connection manager for real-time game communication."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections grouped by room."""

    def __init__(self):
        # room_code -> {player_id: WebSocket}
        self.rooms: dict[str, dict[str, WebSocket]] = {}
        # player_id -> room_code (reverse lookup)
        self.player_rooms: dict[str, str] = {}
        # player_id -> WebSocket
        self.connections: dict[str, WebSocket] = {}

    async def connect(self, ws: WebSocket, room_code: str, player_id: str):
        await ws.accept()
        if room_code not in self.rooms:
            self.rooms[room_code] = {}
        self.rooms[room_code][player_id] = ws
        self.player_rooms[player_id] = room_code
        self.connections[player_id] = ws

    def disconnect(self, player_id: str):
        room_code = self.player_rooms.pop(player_id, None)
        self.connections.pop(player_id, None)
        if room_code and room_code in self.rooms:
            self.rooms[room_code].pop(player_id, None)
            if not self.rooms[room_code]:
                del self.rooms[room_code]
        return room_code

    async def send_to_player(self, player_id: str, data: dict):
        ws = self.connections.get(player_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(player_id)

    async def broadcast_to_room(self, room_code: str, data: dict, exclude: str | None = None):
        connections = self.rooms.get(room_code, {})
        disconnected = []
        for pid, ws in connections.items():
            if pid == exclude:
                continue
            try:
                await ws.send_json(data)
            except Exception:
                disconnected.append(pid)
        for pid in disconnected:
            self.disconnect(pid)

    async def broadcast_state(self, room_code: str, game_room):
        """Send personalized game state to each player in the room."""
        connections = self.rooms.get(room_code, {})
        disconnected = []
        for pid, ws in connections.items():
            try:
                state = game_room.get_state_for_player(pid)
                await ws.send_json({"type": "state_update", "state": state})
            except Exception:
                disconnected.append(pid)
        for pid in disconnected:
            self.disconnect(pid)

    def get_room_player_ids(self, room_code: str) -> list[str]:
        return list(self.rooms.get(room_code, {}).keys())

    def is_connected(self, player_id: str) -> bool:
        return player_id in self.connections


manager = ConnectionManager()
