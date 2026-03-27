"""Role definitions and ability system for the Blink Assassin game."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional


class RoleType(str, enum.Enum):
    ASSASSIN = "assassin"
    DETECTIVE = "detective"
    VICTIM = "victim"


class PlayerStatus(str, enum.Enum):
    ALIVE = "alive"
    DEAD = "dead"
    SPECTATOR = "spectator"


@dataclass
class Player:
    """Represents a player in the game."""

    id: str
    name: str
    role: Optional[RoleType] = None
    status: PlayerStatus = PlayerStatus.ALIVE
    is_ai: bool = False
    avatar_color: str = "#6C63FF"

    # Cooldown tracking (timestamps)
    last_action_time: float = 0.0
    action_count: int = 0

    # Detective-specific
    has_power: bool = True  # Detective loses power on wrong accusation
    investigations_used: int = 0

    # Suspicion score (0.0 to 1.0)
    suspicion_score: float = 0.0

    # Look system tracking
    look_targets: list[str] = field(default_factory=list)
    looked_at_by: list[str] = field(default_factory=list)

    # Stats
    kills: int = 0
    correct_accusations: int = 0
    wrong_accusations: int = 0

    def to_public_dict(self) -> dict:
        """Return public info (no role revealed)."""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "is_ai": self.is_ai,
            "avatar_color": self.avatar_color,
            "suspicion_score": round(self.suspicion_score, 2),
        }

    def to_private_dict(self) -> dict:
        """Return full info for the player themselves."""
        return {
            **self.to_public_dict(),
            "role": self.role.value if self.role else None,
            "has_power": self.has_power,
            "investigations_used": self.investigations_used,
            "kills": self.kills,
        }

    def to_detective_view(self) -> dict:
        """Return info visible to the detective."""
        return {
            **self.to_public_dict(),
            "suspicion_score": round(self.suspicion_score, 2),
            "recent_looks": self.look_targets[-5:],
            "action_count": self.action_count,
        }


AVATAR_COLORS = [
    "#6C63FF", "#FF6584", "#43E97B", "#F7971E",
    "#00C9FF", "#FC5C7D", "#A18CD1", "#FBC2EB",
    "#F093FB", "#4FACFE", "#0BA360", "#FFD54F",
]
