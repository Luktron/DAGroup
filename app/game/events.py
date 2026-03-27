"""Event system — noise generation, blackouts, interference, and timeline."""

from __future__ import annotations

import enum
import random
import time
from dataclasses import dataclass, field


class EventType(str, enum.Enum):
    KILL = "kill"
    DEATH = "death"
    LOOK = "look"
    INVESTIGATE = "investigate"
    ACCUSE = "accuse"
    CHAT = "chat"
    NOISE_LOOK = "noise_look"        # Fake "someone looked" event
    NOISE_ACTIVITY = "noise_activity"  # Fake activity blip
    BLACKOUT = "blackout"
    INTERFERENCE = "interference"
    SUSPICION_CHANGE = "suspicion_change"
    PLAYER_JOIN = "player_join"
    PLAYER_LEAVE = "player_leave"
    GAME_START = "game_start"
    GAME_END = "game_end"
    ROUND_TICK = "round_tick"
    TENSION = "tension"


@dataclass
class GameEvent:
    """A single game event in the timeline."""

    type: EventType
    timestamp: float = field(default_factory=time.time)
    actor_id: str | None = None
    target_id: str | None = None
    data: dict = field(default_factory=dict)
    visible_to: list[str] | None = None  # None = visible to all, list = specific player IDs
    is_noise: bool = False  # True if this is a decoy/camouflage event

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "timestamp": self.timestamp,
            "actor_id": self.actor_id,
            "target_id": self.target_id,
            "data": self.data,
            "is_noise": self.is_noise,
        }

    def to_public_dict(self) -> dict:
        """Strip sensitive info for broadcast."""
        d = {
            "type": self.type.value,
            "timestamp": self.timestamp,
            "data": {k: v for k, v in self.data.items() if k != "real_actor"},
        }
        if self.target_id and self.type in (EventType.DEATH, EventType.ACCUSE):
            d["target_id"] = self.target_id
        return d


class EventTimeline:
    """Stores and queries game events."""

    def __init__(self):
        self.events: list[GameEvent] = []

    def add(self, event: GameEvent):
        self.events.append(event)

    def get_recent(self, seconds: float = 15.0) -> list[GameEvent]:
        cutoff = time.time() - seconds
        return [e for e in self.events if e.timestamp >= cutoff]

    def get_around_death(self, death_time: float, window: float = 10.0) -> list[GameEvent]:
        """Get events around a death for detective investigation."""
        start = death_time - window
        end = death_time + 2.0
        return [
            e for e in self.events
            if start <= e.timestamp <= end
            and e.type not in (EventType.KILL,)  # Never show raw kill events
        ]

    def get_player_events(self, player_id: str, seconds: float = 15.0) -> list[GameEvent]:
        cutoff = time.time() - seconds
        return [
            e for e in self.events
            if e.timestamp >= cutoff
            and (e.actor_id == player_id or e.target_id == player_id)
        ]

    def get_visible_to(self, player_id: str, seconds: float = 15.0) -> list[GameEvent]:
        cutoff = time.time() - seconds
        return [
            e for e in self.events
            if e.timestamp >= cutoff
            and (e.visible_to is None or player_id in e.visible_to)
        ]


class NoiseGenerator:
    """Generates camouflage events to hide assassin actions."""

    NOISE_MESSAGES = [
        "movimento detectado",
        "olhar suspeito",
        "atividade incomum",
        "interação registrada",
        "comportamento analisado",
        "sinal captado",
    ]

    @staticmethod
    def generate_noise(player_ids: list[str], count: int = 2) -> list[GameEvent]:
        """Generate fake events to camouflage real actions."""
        events = []
        available = list(player_ids)
        for _ in range(min(count, len(available))):
            actor = random.choice(available)
            target = random.choice([p for p in available if p != actor] or available)
            noise_type = random.choice([EventType.NOISE_LOOK, EventType.NOISE_ACTIVITY])
            events.append(GameEvent(
                type=noise_type,
                actor_id=actor,
                target_id=target,
                data={"message": random.choice(NoiseGenerator.NOISE_MESSAGES)},
                is_noise=True,
                timestamp=time.time() + random.uniform(0.1, 1.5),
            ))
        return events

    @staticmethod
    def should_trigger_blackout() -> bool:
        from app.config import CONFIG
        return random.random() < CONFIG.BLACKOUT_CHANCE

    @staticmethod
    def should_trigger_interference() -> bool:
        from app.config import CONFIG
        return random.random() < CONFIG.INTERFERENCE_CHANCE
