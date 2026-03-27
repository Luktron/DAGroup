"""Suspicion tracking system — Artificial Social Perception (PSA) layer."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from app.config import CONFIG


@dataclass
class SuspicionProfile:
    """Tracks suspicion data for a single player."""

    player_id: str
    base_score: float = 0.0
    temporal_score: float = 0.0       # Proximity to deaths
    activity_score: float = 0.0       # Action frequency anomalies
    look_pattern_score: float = 0.0   # Suspicious looking patterns
    last_updated: float = field(default_factory=time.time)

    @property
    def total(self) -> float:
        raw = (
            self.base_score * 0.1
            + self.temporal_score * 0.4
            + self.activity_score * 0.25
            + self.look_pattern_score * 0.25
        )
        return max(0.0, min(1.0, raw))

    def decay(self):
        """Apply time-based decay to suspicion scores."""
        elapsed = time.time() - self.last_updated
        decay_factor = CONFIG.SUSPICION_DECAY * elapsed
        self.temporal_score = max(0.0, self.temporal_score - decay_factor)
        self.activity_score = max(0.0, self.activity_score - decay_factor * 0.5)
        self.look_pattern_score = max(0.0, self.look_pattern_score - decay_factor * 0.3)
        self.last_updated = time.time()


class SuspicionEngine:
    """Manages suspicion scores for all players in a game."""

    def __init__(self):
        self.profiles: dict[str, SuspicionProfile] = {}

    def register_player(self, player_id: str):
        self.profiles[player_id] = SuspicionProfile(player_id=player_id)

    def remove_player(self, player_id: str):
        self.profiles.pop(player_id, None)

    def on_death(self, victim_id: str, death_time: float, recent_actors: list[str]):
        """Update suspicion when someone dies — actors near the death get flagged."""
        for actor_id in recent_actors:
            if actor_id == victim_id:
                continue
            profile = self.profiles.get(actor_id)
            if profile:
                profile.temporal_score = min(1.0, profile.temporal_score + 0.3)
                profile.last_updated = time.time()

    def on_action(self, player_id: str, action_type: str):
        """Track action frequency — too many actions = suspicious."""
        profile = self.profiles.get(player_id)
        if profile:
            if action_type == "look":
                profile.activity_score = min(1.0, profile.activity_score + 0.05)
            elif action_type == "interact":
                profile.activity_score = min(1.0, profile.activity_score + 0.1)
            elif action_type == "reported":
                profile.activity_score = min(1.0, profile.activity_score + 0.15)
                profile.base_score = min(1.0, profile.base_score + 0.1)
            profile.last_updated = time.time()

    def on_look_pattern(self, looker_id: str, target_id: str, target_died_soon: bool):
        """If someone looked at a player right before they died — very suspicious."""
        profile = self.profiles.get(looker_id)
        if profile and target_died_soon:
            profile.look_pattern_score = min(1.0, profile.look_pattern_score + 0.35)
            profile.last_updated = time.time()

    def decay_all(self):
        for profile in self.profiles.values():
            profile.decay()

    def get_ranking(self) -> list[dict]:
        """Return players ranked by suspicion (for detective view)."""
        self.decay_all()
        ranked = sorted(
            self.profiles.values(),
            key=lambda p: p.total,
            reverse=True,
        )
        return [
            {
                "player_id": p.player_id,
                "suspicion": round(p.total, 2),
                "level": _suspicion_level(p.total),
            }
            for p in ranked
        ]

    def get_score(self, player_id: str) -> float:
        profile = self.profiles.get(player_id)
        if profile:
            profile.decay()
            return profile.total
        return 0.0

    def get_obfuscated_evidence(self, player_id: str) -> dict:
        """Return fuzzy evidence for detective — never 100% clear."""
        score = self.get_score(player_id)
        level = _suspicion_level(score)
        hints = []
        profile = self.profiles.get(player_id)
        if profile:
            if profile.temporal_score > 0.3:
                hints.append("Atividade próxima a mortes recentes")
            if profile.activity_score > 0.3:
                hints.append("Frequência de ações acima do normal")
            if profile.look_pattern_score > 0.3:
                hints.append("Padrão de olhar suspeito")
            if not hints:
                hints.append("Sem evidências significativas")
        return {
            "player_id": player_id,
            "level": level,
            "score": round(score, 2),
            "hints": hints,
        }


def _suspicion_level(score: float) -> str:
    if score >= 0.7:
        return "high"
    elif score >= 0.4:
        return "moderate"
    elif score >= 0.15:
        return "low"
    return "none"
