#!/usr/bin/env python3
"""
Verdict launcher — one command runs the whole app (API + SPA frontend, since
backend/main.py already serves frontend/index.html itself).

    python start.py                 # run it
    python start.py --install       # also pip install -r requirements.txt first
    python start.py --port 9000     # pick a port (default 8000, or $PORT if set)
    python start.py --no-browser    # don't auto-open a browser tab
    python start.py --force-sqlite  # skip the MySQL check, use the local SQLite file

What it does, in order:
  1. Makes sure a .env file exists (copies .env.example if missing) and fills in
     a real random JWT_SECRET if it's still the placeholder — no manual step needed.
  2. Checks whether the pinned dependencies are installed; with --install it
     will `pip install -r requirements.txt` for you first.
  3. Tries to reach the MySQL server described in .env. If it can't (most
     first-time runs — nobody's set up MySQL yet), it transparently falls back
     to a local SQLite file (verdict_dev.db) so the app still runs with zero
     setup. This fallback is dev-only; point DB_* at a real MySQL server in
     .env for production.
  4. Starts the server. backend/main.py mounts frontend/index.html at "/", so
     there is nothing else to run — one process serves both.
"""
import argparse
import os
import secrets
import shutil
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUIRED_MODULES = ["fastapi", "uvicorn", "pydantic", "passlib", "jwt", "mysql.connector", "groq", "dotenv"]


def banner(text):
    print(f"\n{'─' * 60}\n  {text}\n{'─' * 60}")


def ensure_env_file():
    env_path = ROOT / ".env"
    example_path = ROOT / ".env.example"
    if not env_path.exists():
        if example_path.exists():
            shutil.copy(example_path, env_path)
            print(f"[start.py] Created .env from .env.example")
        else:
            env_path.write_text("APP_ENV=development\n")
            print(f"[start.py] Created a minimal .env")

    content = env_path.read_text()
    if "JWT_SECRET=dev-only-insecure-secret-change-me" in content or "JWT_SECRET=" not in content:
        new_secret = secrets.token_hex(32)
        if "JWT_SECRET=" in content:
            lines = [
                f"JWT_SECRET={new_secret}" if line.startswith("JWT_SECRET=") else line
                for line in content.splitlines()
            ]
            content = "\n".join(lines) + "\n"
        else:
            content = content.rstrip("\n") + f"\nJWT_SECRET={new_secret}\n"
        env_path.write_text(content)
        print("[start.py] Generated a random JWT_SECRET and saved it to .env")


def check_dependencies(auto_install: bool) -> bool:
    missing = []
    for mod in REQUIRED_MODULES:
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)

    if not missing:
        return True

    if auto_install:
        print(f"[start.py] Installing dependencies from requirements.txt ...")
        import subprocess
        result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")])
        if result.returncode != 0:
            print("[start.py] pip install failed — see output above.")
            return False
        return True

    banner("Missing dependencies")
    print(f"  Missing: {', '.join(missing)}")
    print(f"  Run:     pip install -r requirements.txt")
    print(f"  Or:      python start.py --install")
    return False


def mysql_reachable(timeout=2) -> bool:
    try:
        import mysql.connector
        from backend.utils.config import settings
        conn = mysql.connector.connect(
            host=settings.DB_HOST, port=settings.DB_PORT, database=settings.DB_NAME,
            user=settings.DB_USER, password=settings.DB_PASSWORD, connection_timeout=timeout,
        )
        conn.close()
        return True
    except Exception as e:
        print(f"[start.py] MySQL not reachable ({e.__class__.__name__}: {e})")
        return False


def use_sqlite_fallback():
    """Patch backend.database.database BEFORE any service module imports from it."""
    import backend.database.database as dbmod
    from backend.database import sqlite_fallback
    sqlite_fallback.init_db()
    dbmod.execute_query = sqlite_fallback.execute_query
    dbmod.execute_many = sqlite_fallback.execute_many
    return sqlite_fallback.DB_PATH


def port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def open_browser_when_ready(url: str, delay: float = 1.5):
    def _open():
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:
            pass
    threading.Thread(target=_open, daemon=True).start()


def main():
    parser = argparse.ArgumentParser(description="Run Verdict (API + frontend) in one process.")
    parser.add_argument("--install", action="store_true", help="pip install -r requirements.txt first")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", 8000)))
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--force-sqlite", action="store_true", help="skip the MySQL check")
    parser.add_argument("--reload", action="store_true", help="auto-reload on code changes (dev only)")
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT))

    ensure_env_file()

    if not check_dependencies(auto_install=args.install):
        sys.exit(1)

    if not port_available(args.port):
        print(f"[start.py] Port {args.port} is already in use — pick another with --port.")
        sys.exit(1)

    banner("Verdict")
    if args.force_sqlite or not mysql_reachable():
        db_path = use_sqlite_fallback()
        print(f"  Database: SQLite (dev fallback) -> {db_path}")
        print(f"            Configure DB_* in .env and point it at a real MySQL")
        print(f"            server for production use.")
    else:
        print(f"  Database: MySQL (from .env)")

    url = f"http://127.0.0.1:{args.port}/"
    print(f"  URL:      {url}")
    print(f"  API docs: {url}docs")
    print(f"  Demo login: demo@verdict.ai / verdict123")
    print(f"{'─' * 60}\n")

    if not args.no_browser:
        open_browser_when_ready(url)

    import uvicorn
    if args.reload:
        uvicorn.run("backend.main:app", host=args.host, port=args.port, reload=True)
    else:
        from backend.main import app
        uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
