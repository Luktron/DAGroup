"""Core game engine — manages game state, rounds, and game logic."""

from __future__ import annotations

import asyncio
import random
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from app.config import CONFIG
from app.game.events import EventTimeline, EventType, GameEvent, NoiseGenerator
from app.game.roles import AVATAR_COLORS, Player, PlayerStatus, RoleType
from app.game.suspicion import SuspicionEngine


class GamePhase(str, Enum):
    LOBBY = "lobby"
    PLAYING = "playing"
    FINISHED = "finished"


@dataclass
class PendingKill:
    """A kill scheduled by the assassin with a random delay."""

    assassin_id: str
    target_id: str
    scheduled_at: float
    execute_at: float


class GameRoom:
    """Represents a single game room with full game state."""

    def __init__(self, room_code: str, creator_id: str, max_players: int, lang: str = "pt"):
        self.room_code = room_code
        self.creator_id = creator_id
        self.max_players = max(CONFIG.MIN_PLAYERS, min(CONFIG.MAX_PLAYERS, max_players))
        self.lang = lang
        self.phase = GamePhase.LOBBY
        self.players: dict[str, Player] = {}
        self.player_order: list[str] = []  # For circle display
        self.round_number: int = 0
        self.round_start_time: float = 0.0
        self.timeline = EventTimeline()
        self.suspicion = SuspicionEngine()
        self.pending_kills: list[PendingKill] = []
        self.winner: Optional[str] = None  # "assassin" or "detective"
        self.is_blackout: bool = False
        self.blackout_end: float = 0.0
        self.created_at: float = time.time()

        # Callback for broadcasting messages
        self._broadcast_callback = None
        self._send_to_callback = None

    def set_callbacks(self, broadcast_fn, send_to_fn):
        self._broadcast_callback = broadcast_fn
        self._send_to_callback = send_to_fn

    # ------------------------------------------------------------------
    # Player management
    # ------------------------------------------------------------------

    def add_player(self, player_id: str, name: str, is_ai: bool = False, gender: str = "m") -> Optional[Player]:
        if len(self.players) >= self.max_players:
            return None
        if player_id in self.players:
            return self.players[player_id]

        color = AVATAR_COLORS[len(self.players) % len(AVATAR_COLORS)]
        player = Player(id=player_id, name=name, is_ai=is_ai, avatar_color=color, gender=gender)
        self.players[player_id] = player
        self.player_order.append(player_id)
        self.suspicion.register_player(player_id)

        self.timeline.add(GameEvent(
            type=EventType.PLAYER_JOIN,
            actor_id=player_id,
            data={"name": name, "is_ai": is_ai},
        ))
        return player

    def remove_player(self, player_id: str) -> Optional[Player]:
        player = self.players.pop(player_id, None)
        if player:
            if player_id in self.player_order:
                self.player_order.remove(player_id)
            self.suspicion.remove_player(player_id)
            self.timeline.add(GameEvent(
                type=EventType.PLAYER_LEAVE,
                actor_id=player_id,
                data={"name": player.name},
            ))
        return player

    def get_alive_players(self) -> list[Player]:
        return [p for p in self.players.values() if p.status == PlayerStatus.ALIVE]

    def get_alive_victims(self) -> list[Player]:
        return [
            p for p in self.players.values()
            if p.status == PlayerStatus.ALIVE and p.role == RoleType.VICTIM
        ]

    def get_player_by_role(self, role: RoleType) -> Optional[Player]:
        for p in self.players.values():
            if p.role == role:
                return p
        return None

    # ------------------------------------------------------------------
    # Game lifecycle
    # ------------------------------------------------------------------

    def assign_roles(self):
        """Randomly assign roles to all players."""
        ids = list(self.players.keys())
        random.shuffle(ids)

        # First player → assassin, second → detective, rest → victims
        for i, pid in enumerate(ids):
            if i == 0:
                self.players[pid].role = RoleType.ASSASSIN
            elif i == 1:
                self.players[pid].role = RoleType.DETECTIVE
            else:
                self.players[pid].role = RoleType.VICTIM

        # Shuffle the circle order
        random.shuffle(self.player_order)

    def start_game(self) -> bool:
        """Start the game if enough players."""
        if len(self.players) < CONFIG.MIN_PLAYERS:
            return False
        if self.phase != GamePhase.LOBBY:
            return False

        self.assign_roles()
        self.phase = GamePhase.PLAYING
        self.round_number = 1
        self.round_start_time = time.time()

        self.timeline.add(GameEvent(
            type=EventType.GAME_START,
            data={"players": len(self.players), "round": 1},
        ))
        return True

    def end_game(self, winner: str):
        """End the game with a winner."""
        self.phase = GamePhase.FINISHED
        self.winner = winner
        self.timeline.add(GameEvent(
            type=EventType.GAME_END,
            data={"winner": winner},
        ))

    def reset_for_new_round(self):
        """Reset the game for a new round (reshuffle roles)."""
        for player in self.players.values():
            player.role = None
            player.status = PlayerStatus.ALIVE
            player.has_power = True
            player.last_action_time = 0.0
            player.action_count = 0
            player.investigations_used = 0
            player.suspicion_score = 0.0
            player.look_targets = []
            player.looked_at_by = []

        self.pending_kills = []
        self.winner = None
        self.is_blackout = False
        self.timeline = EventTimeline()
        self.suspicion = SuspicionEngine()
        for pid in self.players:
            self.suspicion.register_player(pid)

        self.assign_roles()
        self.phase = GamePhase.PLAYING
        self.round_number += 1
        self.round_start_time = time.time()

    # ------------------------------------------------------------------
    # Game actions
    # ------------------------------------------------------------------

    def assassin_kill(self, assassin_id: str, target_id: str) -> dict:
        """Assassin initiates a kill with delayed execution."""
        assassin = self.players.get(assassin_id)
        target = self.players.get(target_id)

        if not assassin or assassin.role != RoleType.ASSASSIN:
            return {"success": False, "error": "not_assassin"}
        if assassin.status != PlayerStatus.ALIVE:
            return {"success": False, "error": "dead"}
        if not target or target.status != PlayerStatus.ALIVE:
            return {"success": False, "error": "invalid_target"}
        if target.role == RoleType.ASSASSIN:
            return {"success": False, "error": "self_target"}

        # Rule: assassin cannot kill the detective — detective auto-wins
        if target.role == RoleType.DETECTIVE:
            self.end_game("detective_auto")
            return {"success": True, "detective_auto_win": True}

        now = time.time()
        if now - assassin.last_action_time < CONFIG.ASSASSIN_COOLDOWN:
            remaining = CONFIG.ASSASSIN_COOLDOWN - (now - assassin.last_action_time)
            return {"success": False, "error": "cooldown", "remaining": round(remaining, 1)}

        # Schedule the kill with random delay
        delay = random.uniform(CONFIG.KILL_DELAY_MIN, CONFIG.KILL_DELAY_MAX)
        pending = PendingKill(
            assassin_id=assassin_id,
            target_id=target_id,
            scheduled_at=now,
            execute_at=now + delay,
        )
        self.pending_kills.append(pending)
        assassin.last_action_time = now
        assassin.action_count += 1

        # Record on timeline (hidden event)
        self.timeline.add(GameEvent(
            type=EventType.KILL,
            actor_id=assassin_id,
            target_id=target_id,
            data={"delay": delay},
            visible_to=[assassin_id],  # Only assassin sees this
        ))

        # Generate noise to camouflage
        alive_ids = [p.id for p in self.get_alive_players()]
        noise_events = NoiseGenerator.generate_noise(alive_ids, count=random.randint(2, 4))
        for ne in noise_events:
            self.timeline.add(ne)

        # Track suspicion
        self.suspicion.on_action(assassin_id, "interact")

        return {"success": True, "delay": round(delay, 1)}

    def process_pending_kills(self) -> list[dict]:
        """Check and execute pending kills. Returns list of death events."""
        now = time.time()
        executed = []
        remaining = []

        for pk in self.pending_kills:
            if now >= pk.execute_at:
                target = self.players.get(pk.target_id)
                if target and target.status == PlayerStatus.ALIVE:
                    target.status = PlayerStatus.DEAD
                    assassin = self.players.get(pk.assassin_id)
                    if assassin:
                        assassin.kills += 1

                    # Record death
                    self.timeline.add(GameEvent(
                        type=EventType.DEATH,
                        target_id=pk.target_id,
                        data={"name": target.name},
                    ))

                    # Update suspicion for nearby actors
                    recent = self.timeline.get_recent(10.0)
                    recent_actors = list({
                        e.actor_id for e in recent
                        if e.actor_id and e.actor_id != pk.target_id
                    })
                    self.suspicion.on_death(pk.target_id, now, recent_actors)

                    # Check look patterns
                    for evt in recent:
                        if (evt.type == EventType.LOOK
                                and evt.target_id == pk.target_id
                                and evt.actor_id):
                            self.suspicion.on_look_pattern(
                                evt.actor_id, pk.target_id, target_died_soon=True
                            )

                    executed.append({
                        "target_id": pk.target_id,
                        "target_name": target.name,
                    })

                    # Check win condition — assassin wins when all victims are dead
                    if not self.get_alive_victims():
                        self.end_game("assassin")
            else:
                remaining.append(pk)

        self.pending_kills = remaining

        # Random events
        if executed and NoiseGenerator.should_trigger_blackout():
            self.trigger_blackout()

        return executed

    def detective_investigate(self, detective_id: str, suspect_id: str) -> dict:
        """Detective investigates a suspect — returns obfuscated evidence."""
        detective = self.players.get(detective_id)
        suspect = self.players.get(suspect_id)

        if not detective or detective.role != RoleType.DETECTIVE:
            return {"success": False, "error": "not_detective"}
        if detective.status != PlayerStatus.ALIVE:
            return {"success": False, "error": "dead"}
        if not detective.has_power:
            return {"success": False, "error": "no_power"}
        if not suspect or suspect.status != PlayerStatus.ALIVE:
            return {"success": False, "error": "invalid_target"}
        if suspect_id == detective_id:
            return {"success": False, "error": "self_target"}

        now = time.time()
        if now - detective.last_action_time < CONFIG.DETECTIVE_COOLDOWN:
            remaining = CONFIG.DETECTIVE_COOLDOWN - (now - detective.last_action_time)
            return {"success": False, "error": "cooldown", "remaining": round(remaining, 1)}

        detective.last_action_time = now
        detective.investigations_used += 1
        detective.action_count += 1

        # Get obfuscated evidence
        evidence = self.suspicion.get_obfuscated_evidence(suspect_id)

        # Add timeline context
        recent_events = self.timeline.get_player_events(suspect_id, CONFIG.INVESTIGATION_WINDOW)
        evidence["recent_activity_count"] = len(recent_events)
        evidence["timeline_snippets"] = [
            {
                "type": e.type.value,
                "seconds_ago": round(now - e.timestamp, 1),
                "data": {k: v for k, v in e.data.items() if k not in ("real_actor",)},
            }
            for e in recent_events[-5:]  # Last 5 events
            if not e.is_noise or random.random() < 0.3  # Some noise leaks through
        ]

        # Record investigation
        self.timeline.add(GameEvent(
            type=EventType.INVESTIGATE,
            actor_id=detective_id,
            target_id=suspect_id,
            data={"result": evidence["level"]},
            visible_to=[detective_id],
        ))

        self.suspicion.on_action(detective_id, "interact")

        return {"success": True, "evidence": evidence}

    def detective_accuse(self, detective_id: str, suspect_id: str) -> dict:
        """Detective accuses someone — high risk, high reward."""
        detective = self.players.get(detective_id)
        suspect = self.players.get(suspect_id)

        if not detective or detective.role != RoleType.DETECTIVE:
            return {"success": False, "error": "not_detective"}
        if detective.status != PlayerStatus.ALIVE:
            return {"success": False, "error": "dead"}
        if not detective.has_power:
            return {"success": False, "error": "no_power"}
        if not suspect or suspect.status != PlayerStatus.ALIVE:
            return {"success": False, "error": "invalid_target"}

        # Record accusation
        self.timeline.add(GameEvent(
            type=EventType.ACCUSE,
            actor_id=detective_id,
            target_id=suspect_id,
            data={"name": suspect.name},
        ))

        if suspect.role == RoleType.ASSASSIN:
            # Correct! Detective wins!
            detective.correct_accusations += 1
            self.end_game("detective")
            return {
                "success": True,
                "correct": True,
                "message": "arrested",
                "assassin_name": suspect.name,
            }
        else:
            # Wrong! Assassin wins immediately
            detective.wrong_accusations += 1
            detective.status = PlayerStatus.DEAD
            self.end_game("assassin_accuse")

            # Find the real assassin name
            assassin = next(
                (p for p in self.players.values() if p.role == RoleType.ASSASSIN),
                None,
            )

            return {
                "success": True,
                "correct": False,
                "message": "died",
                "accused_name": suspect.name,
                "assassin_name": assassin.name if assassin else "?",
            }

    def player_look(self, looker_id: str, target_id: str) -> dict:
        """Register a 'look' action — part of the social perception system."""
        looker = self.players.get(looker_id)
        target = self.players.get(target_id)

        if not looker or looker.status != PlayerStatus.ALIVE:
            return {"success": False}
        if not target or target.status != PlayerStatus.ALIVE:
            return {"success": False}
        if looker_id == target_id:
            return {"success": False}

        looker.look_targets.append(target_id)
        target.looked_at_by.append(looker_id)

        self.timeline.add(GameEvent(
            type=EventType.LOOK,
            actor_id=looker_id,
            target_id=target_id,
            data={"name": target.name},
        ))

        self.suspicion.on_action(looker_id, "look")

        return {"success": True}

    # ------------------------------------------------------------------
    # Special events
    # ------------------------------------------------------------------

    def trigger_blackout(self):
        """Trigger a blackout — logs become confused."""
        self.is_blackout = True
        self.blackout_end = time.time() + CONFIG.BLACKOUT_DURATION
        self.timeline.add(GameEvent(
            type=EventType.BLACKOUT,
            data={"duration": CONFIG.BLACKOUT_DURATION},
        ))

    def check_blackout(self):
        if self.is_blackout and time.time() >= self.blackout_end:
            self.is_blackout = False

    def get_tension_level(self) -> float:
        """Calculate tension based on deaths and time elapsed."""
        total = len(self.players)
        alive = len(self.get_alive_players())
        if total <= 0:
            return 0.0
        death_ratio = 1.0 - (alive / total)
        time_factor = min(1.0, (time.time() - self.round_start_time) / CONFIG.ROUND_DURATION)
        return min(1.0, death_ratio * 0.6 + time_factor * 0.4)

    # ------------------------------------------------------------------
    # State serialization
    # ------------------------------------------------------------------

    def get_state_for_player(self, player_id: str) -> dict:
        """Get the full game state from a specific player's perspective."""
        player = self.players.get(player_id)
        if not player:
            return {}

        state = {
            "room_code": self.room_code,
            "phase": self.phase.value,
            "round": self.round_number,
            "max_players": self.max_players,
            "player_count": len(self.players),
            "alive_count": len(self.get_alive_players()),
            "tension": round(self.get_tension_level(), 2),
            "is_blackout": self.is_blackout,
            "me": player.to_private_dict(),
            "players": [],
            "winner": self.winner,
            "is_creator": player_id == self.creator_id,
            "time_elapsed": round(time.time() - self.round_start_time, 0) if self.round_start_time else 0,
            "lang": self.lang,
        }

        # Add player list (what this player can see)
        for pid in self.player_order:
            p = self.players.get(pid)
            if p:
                if self.phase == GamePhase.FINISHED:
                    # Game over: reveal all roles and role icons
                    pdata = p.to_private_dict()
                    pdata["icon"] = p.get_icon()
                elif pid == player_id:
                    pdata = p.to_private_dict()
                    pdata["icon"] = p.get_icon()
                elif player.role == RoleType.DETECTIVE and player.has_power:
                    pdata = p.to_detective_view()
                    pdata["icon"] = p.get_public_icon()
                else:
                    pdata = p.to_public_dict()
                    pdata["icon"] = p.get_public_icon()
                state["players"].append(pdata)

        # Add suspicion ranking for detective
        if player.role == RoleType.DETECTIVE and player.has_power:
            state["suspicion_ranking"] = self.suspicion.get_ranking()

        # Recent events visible to this player
        visible_events = self.timeline.get_visible_to(player_id, seconds=30.0)
        state["recent_events"] = [e.to_public_dict() for e in visible_events[-15:]]

        return state

    def get_lobby_state(self) -> dict:
        return {
            "room_code": self.room_code,
            "phase": self.phase.value,
            "max_players": self.max_players,
            "creator_id": self.creator_id,
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "is_ai": p.is_ai,
                    "avatar_color": p.avatar_color,
                    "gender": p.gender,
                    "icon": p.get_public_icon(),
                }
                for p in self.players.values()
            ],
            "player_count": len(self.players),
            "can_start": len(self.players) >= CONFIG.MIN_PLAYERS,
            "lang": self.lang,
        }


class GameManager:
    """Manages all active game rooms."""

    def __init__(self):
        self.rooms: dict[str, GameRoom] = {}

    def create_room(self, creator_id: str, max_players: int = 6, lang: str = "pt") -> GameRoom:
        code = self._generate_code()
        room = GameRoom(room_code=code, creator_id=creator_id, max_players=max_players, lang=lang)
        self.rooms[code] = room
        return room

    def get_room(self, code: str) -> Optional[GameRoom]:
        return self.rooms.get(code.upper())

    def remove_room(self, code: str):
        self.rooms.pop(code, None)

    def _generate_code(self) -> str:
        while True:
            code = secrets.token_hex(3).upper()[:6]
            if code not in self.rooms:
                return code
