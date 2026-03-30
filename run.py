"""Start the Assassino da Piscada server."""

import os
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

    # Disable reload on Termux (subprocess loses virtualenv context)
    is_termux = "com.termux" in os.environ.get("PREFIX", "")
    use_reload = not is_termux

    uvicorn.run(
        "app.main:app",
        host=CONFIG.HOST,
        port=port,
        reload=use_reload,
        log_level="info",
    )
