"""AI bot system — realistic bot players that bluff, investigate, and create noise."""

from __future__ import annotations

import asyncio
import random
import time
import uuid
from typing import TYPE_CHECKING

from app.config import CONFIG
from app.game.roles import PlayerStatus, RoleType

if TYPE_CHECKING:
    from app.game.engine import GameRoom


class AIPersonality:
    """Defines behaviour profiles for AI bots."""

    AGGRESSIVE = "aggressive"
    CAUTIOUS = "cautious"
    ERRATIC = "erratic"
    CALCULATED = "calculated"

    ALL = [AGGRESSIVE, CAUTIOUS, ERRATIC, CALCULATED]


AI_NAMES = [
    "Shadow", "Phantom", "Cipher", "Echo", "Specter",
    "Raven", "Onyx", "Viper", "Storm", "Ghost",
    "Nyx", "Blade", "Ember", "Frost", "Nebula",
]


class AIBot:
    """Controls an AI-managed player within a game room."""

    def __init__(self, room: GameRoom, player_id: str):
        self.room = room
        self.player_id = player_id
        self.personality = random.choice(AIPersonality.ALL)
        self.running = False
        self._task: asyncio.Task | None = None

    @property
    def player(self):
        return self.room.players.get(self.player_id)

    def start(self):
        if not self.running:
            self.running = True
            self._task = asyncio.create_task(self._loop())

    def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
            self._task = None

    async def _loop(self):
        """Main AI loop — continuously makes decisions."""
        try:
            # Wait for game to start
            while self.running and self.room.phase.value == "lobby":
                await asyncio.sleep(1)

            while self.running and self.room.phase.value == "playing":
                player = self.player
                if not player or player.status != PlayerStatus.ALIVE:
                    break

                await self._think_and_act()
                await asyncio.sleep(random.uniform(
                    CONFIG.AI_THINK_DELAY_MIN, CONFIG.AI_THINK_DELAY_MAX
                ))
        except asyncio.CancelledError:
            pass

    async def _think_and_act(self):
        player = self.player
        if not player or player.status != PlayerStatus.ALIVE:
            return

        if player.role == RoleType.ASSASSIN:
            await self._act_as_assassin()
        elif player.role == RoleType.DETECTIVE:
            await self._act_as_detective()
        else:
            await self._act_as_victim()

    async def _act_as_assassin(self):
        """AI assassin: look around to bluff, then kill strategically."""
        player = self.player
        alive = self.room.get_alive_players()
        targets = [p for p in alive if p.id != self.player_id and p.role != RoleType.DETECTIVE]

        if not targets:
            return

        # Bluff: look at random players to create noise
        if random.random() < 0.6:
            look_target = random.choice(targets)
            self.room.player_look(self.player_id, look_target.id)
            await self._broadcast_action("look", look_target.id)

        # Decide if it's time to kill
        now = time.time()
        time_since_last = now - player.last_action_time
        kill_threshold = random.uniform(CONFIG.AI_KILL_INTERVAL_MIN, CONFIG.AI_KILL_INTERVAL_MAX)

        if time_since_last >= kill_threshold:
            # Choose target based on personality
            target = self._choose_kill_target(targets)
            if target:
                result = self.room.assassin_kill(self.player_id, target.id)
                if result.get("success"):
                    # Look at other players to divert suspicion
                    decoys = [p for p in targets if p.id != target.id]
                    if decoys:
                        decoy = random.choice(decoys)
                        self.room.player_look(self.player_id, decoy.id)
                        await self._broadcast_action("look", decoy.id)

    def _choose_kill_target(self, targets: list):
        """Choose kill target based on personality."""
        if self.personality == AIPersonality.AGGRESSIVE:
            # Pick a random victim (detective is already excluded from targets)
            return random.choice(targets) if targets else None
        elif self.personality == AIPersonality.CALCULATED:
            # Avoid killing the person you just looked at
            player = self.player
            recent_looks = player.look_targets[-3:] if player else []
            safe_targets = [t for t in targets if t.id not in recent_looks]
            return random.choice(safe_targets) if safe_targets else random.choice(targets)
        elif self.personality == AIPersonality.CAUTIOUS:
            # Kill randomly but slowly
            return random.choice(targets) if random.random() < 0.5 else None
        else:  # ERRATIC
            return random.choice(targets)

    async def _act_as_detective(self):
        """AI detective: investigate suspects, look for patterns."""
        player = self.player
        if not player or not player.has_power:
            # Lost power, just look around
            await self._random_look()
            return

        alive = [p for p in self.room.get_alive_players() if p.id != self.player_id]
        if not alive:
            return

        # Look at suspicious players
        if random.random() < 0.5:
            await self._random_look()

        now = time.time()
        time_since_last = now - player.last_action_time
        investigate_threshold = random.uniform(
            CONFIG.AI_INVESTIGATE_INTERVAL_MIN, CONFIG.AI_INVESTIGATE_INTERVAL_MAX
        )

        if time_since_last >= investigate_threshold:
            # Try to investigate the most suspicious player
            ranking = self.room.suspicion.get_ranking()
            ranking = [r for r in ranking if r["player_id"] != self.player_id
                       and r["player_id"] in {p.id for p in alive}]

            if ranking:
                top_suspect = ranking[0]
                result = self.room.detective_investigate(self.player_id, top_suspect["player_id"])

                if result.get("success"):
                    evidence = result.get("evidence", {})
                    # Decide whether to accuse
                    if (evidence.get("level") == "high"
                            and player.investigations_used >= 2
                            and random.random() < 0.6):
                        accuse_result = self.room.detective_accuse(
                            self.player_id, top_suspect["player_id"]
                        )
                        await self._broadcast_action("accuse", top_suspect["player_id"])
                        if accuse_result.get("success"):
                            return

    async def _act_as_victim(self):
        """AI victim: look around, create social noise."""
        if random.random() < 0.4:
            await self._random_look()

    async def _random_look(self):
        alive = [p for p in self.room.get_alive_players() if p.id != self.player_id]
        if alive:
            target = random.choice(alive)
            self.room.player_look(self.player_id, target.id)
            await self._broadcast_action("look", target.id)

    async def _broadcast_action(self, action_type: str, target_id: str):
        """Notify the room about this AI's action via the broadcast callback."""
        if self.room._broadcast_callback:
            await self.room._broadcast_callback({
                "type": "ai_action",
                "actor_id": self.player_id,
                "action": action_type,
                "target_id": target_id,
            })


class AIManager:
    """Manages all AI bots across rooms."""

    def __init__(self):
        self.bots: dict[str, list[AIBot]] = {}  # room_code -> list of bots

    def fill_room(self, room: GameRoom) -> list[str]:
        """Fill empty slots in a room with AI bots."""
        added = []
        while len(room.players) < room.max_players:
            bot_id = f"ai_{uuid.uuid4().hex[:8]}"
            name = random.choice([n for n in AI_NAMES if n not in {
                p.name for p in room.players.values()
            }]) if len(room.players) < len(AI_NAMES) else f"Bot-{len(room.players)+1}"

            player = room.add_player(bot_id, name, is_ai=True, gender=random.choice(["m", "f"]))
            if player:
                bot = AIBot(room, bot_id)
                if room.room_code not in self.bots:
                    self.bots[room.room_code] = []
                self.bots[room.room_code].append(bot)
                added.append(bot_id)
        return added

    def replace_player(self, room: GameRoom, leaving_player_id: str) -> str | None:
        """Replace a disconnected player with an AI bot."""
        player = room.players.get(leaving_player_id)
        if not player or player.status == PlayerStatus.DEAD:
            room.remove_player(leaving_player_id)
            return None

        # Create AI with same state
        bot_id = f"ai_{uuid.uuid4().hex[:8]}"
        role = player.role
        status = player.status
        name = f"{player.name} (Bot)"

        room.remove_player(leaving_player_id)
        new_player = room.add_player(bot_id, name, is_ai=True, gender=player.gender)
        if new_player:
            new_player.role = role
            new_player.status = status
            bot = AIBot(room, bot_id)
            if room.room_code not in self.bots:
                self.bots[room.room_code] = []
            self.bots[room.room_code].append(bot)
            if room.phase.value == "playing":
                bot.start()
            return bot_id
        return None

    def start_bots(self, room_code: str):
        for bot in self.bots.get(room_code, []):
            bot.start()

    def stop_bots(self, room_code: str):
        for bot in self.bots.get(room_code, []):
            bot.stop()
        self.bots.pop(room_code, None)
