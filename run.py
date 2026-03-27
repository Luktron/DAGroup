"""Start the Assassino da Piscada server."""

import socket
import uvicorn
from app.config import CONFIG


def get_local_ip():
    """Get the machine's local network IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


if __name__ == "__main__":
    local_ip = get_local_ip()
    port = CONFIG.PORT

    print()
    print(" * Assassino da Piscada - Game Server")
    print(f" * Running on all addresses ({CONFIG.HOST})")
    print(f" * Running on http://127.0.0.1:{port}")
    print(f" * Running on http://{local_ip}:{port}")
    print(" * Press CTRL+C to quit")
    print()

    uvicorn.run(
        "app.main:app",
        host=CONFIG.HOST,
        port=port,
        reload=True,
        log_level="info",
    )
