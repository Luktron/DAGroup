"""Start the Assassino da Piscada server."""

import os
import socket
import subprocess
import sys


def install_dependencies():
    """Auto-install missing dependencies."""
    deps = ["uvicorn", "fastapi", "websockets", "python-multipart", "aiofiles", "jinja2"]
    for dep in deps:
        mod = dep.replace("-", "_")
        try:
            __import__(mod)
        except ImportError:
            print(f"  Installing {dep}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep, "-q"])


install_dependencies()

import uvicorn  # noqa: E402
from app.config import CONFIG  # noqa: E402


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
