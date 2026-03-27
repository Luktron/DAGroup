"""Game configuration constants."""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class GameConfig:
    """Immutable game configuration."""

    # Room settings
    MIN_PLAYERS: int = 3
    MAX_PLAYERS: int = 12
    DEFAULT_PLAYERS: int = 6

    # Timing (seconds)
    KILL_DELAY_MIN: int = 2
    KILL_DELAY_MAX: int = 8
    ASSASSIN_COOLDOWN: int = 10
    DETECTIVE_COOLDOWN: int = 12
    ROUND_DURATION: int = 120
    LOBBY_COUNTDOWN: int = 10
    NOISE_EVENT_INTERVAL: int = 3

    # Detective investigation
    INVESTIGATION_WINDOW: int = 15  # seconds of logs detective can see
    SUSPICION_DECAY: float = 0.05  # per second
    FALSE_ACCUSATION_PENALTY: str = "lose_power"  # lose_power | die

    # AI settings
    AI_THINK_DELAY_MIN: float = 1.5
    AI_THINK_DELAY_MAX: float = 5.0
    AI_KILL_INTERVAL_MIN: int = 8
    AI_KILL_INTERVAL_MAX: int = 18
    AI_INVESTIGATE_INTERVAL_MIN: int = 10
    AI_INVESTIGATE_INTERVAL_MAX: int = 20
    AI_LOOK_INTERVAL_MIN: int = 3
    AI_LOOK_INTERVAL_MAX: int = 8

    # Events
    BLACKOUT_DURATION: int = 8
    BLACKOUT_CHANCE: float = 0.15
    INTERFERENCE_CHANCE: float = 0.10

    # Balancing targets
    DETECTIVE_WIN_RATE_TARGET: float = 0.35
    ASSASSIN_WIN_RATE_TARGET: float = 0.45

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 5052
    SECRET_KEY: str = field(default_factory=lambda: os.environ.get(
        "SECRET_KEY", os.urandom(32).hex()
    ))

    # Language
    DEFAULT_LANG: str = "pt"


CONFIG = GameConfig()

# Translations
TRANSLATIONS = {
    "pt": {
        "game_title": "Assassino da Piscada",
        "create_room": "Criar Sala",
        "join_room": "Entrar na Sala",
        "your_name": "Seu Nome",
        "room_code": "Código da Sala",
        "players": "Jogadores",
        "start_game": "Iniciar Jogo",
        "waiting": "Aguardando jogadores...",
        "you_are": "Você é",
        "assassin": "Assassino",
        "detective": "Detetive",
        "victim": "Vítima",
        "dead": "Morto",
        "alive": "Vivo",
        "spectator": "Espectador",
        "kill": "Eliminar",
        "investigate": "Investigar",
        "accuse": "Acusar",
        "look_at": "Olhar para",
        "chat": "Chat",
        "send": "Enviar",
        "died": "morreu!",
        "arrested": "Preso em nome da lei!",
        "assassin_wins": "O Assassino venceu!",
        "detective_wins": "O Detetive venceu!",
        "wrong_accusation": "Acusação errada!",
        "cooldown_active": "Aguarde o cooldown...",
        "suspicious_activity": "Atividade suspeita detectada",
        "no_evidence": "Sem evidências claras",
        "high_suspicion": "Alta probabilidade",
        "moderate_suspicion": "Comportamento suspeito",
        "blackout": "⚡ APAGÃO!",
        "interference": "📡 Interferência nos dados!",
        "game_over": "Fim de Jogo",
        "play_again": "Jogar Novamente",
        "ai_player": "Bot",
        "room_full": "Sala cheia",
        "copied": "Copiado!",
        "round": "Rodada",
        "time_left": "Tempo restante",
        "players_alive": "Jogadores vivos",
        "tension_rising": "A tensão aumenta...",
        "someone_died": "Alguém morreu...",
        "look_registered": "Olhar registrado",
        "power_lost": "Você perdeu seus poderes!",
        "fill_with_ai": "Completar com IA",
    },
    "en": {
        "game_title": "Blink Assassin",
        "create_room": "Create Room",
        "join_room": "Join Room",
        "your_name": "Your Name",
        "room_code": "Room Code",
        "players": "Players",
        "start_game": "Start Game",
        "waiting": "Waiting for players...",
        "you_are": "You are",
        "assassin": "Assassin",
        "detective": "Detective",
        "victim": "Victim",
        "dead": "Dead",
        "alive": "Alive",
        "spectator": "Spectator",
        "kill": "Eliminate",
        "investigate": "Investigate",
        "accuse": "Accuse",
        "look_at": "Look at",
        "chat": "Chat",
        "send": "Send",
        "died": "died!",
        "arrested": "Arrested in the name of the law!",
        "assassin_wins": "The Assassin wins!",
        "detective_wins": "The Detective wins!",
        "wrong_accusation": "Wrong accusation!",
        "cooldown_active": "Cooldown active...",
        "suspicious_activity": "Suspicious activity detected",
        "no_evidence": "No clear evidence",
        "high_suspicion": "High probability",
        "moderate_suspicion": "Suspicious behavior",
        "blackout": "⚡ BLACKOUT!",
        "interference": "📡 Data interference!",
        "game_over": "Game Over",
        "play_again": "Play Again",
        "ai_player": "Bot",
        "room_full": "Room full",
        "copied": "Copied!",
        "round": "Round",
        "time_left": "Time left",
        "players_alive": "Players alive",
        "tension_rising": "Tension is rising...",
        "someone_died": "Someone died...",
        "look_registered": "Look registered",
        "power_lost": "You lost your powers!",
        "fill_with_ai": "Fill with AI",
    },
}
