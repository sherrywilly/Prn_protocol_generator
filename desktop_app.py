#!/usr/bin/env python3
import os
import shutil
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path
from wsgiref.simple_server import make_server

from platformdirs import user_data_dir


APP_NAME = "PRN Protocol Generator"
APP_AUTHOR = "sherrywilly"
HOST = "127.0.0.1"


def _find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        return sock.getsockname()[1]


def _wait_for_server(url, timeout_seconds=15):
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status < 500:
                    return True
        except Exception:
            time.sleep(0.2)
    return False


def _prepare_persistent_database(base_dir):
    data_dir = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    data_dir.mkdir(parents=True, exist_ok=True)

    desktop_db = data_dir / "db.sqlite3"
    project_db = base_dir / "db.sqlite3"

    if not desktop_db.exists() and project_db.exists():
        shutil.copy2(project_db, desktop_db)

    os.environ["DATABASE_PATH"] = str(desktop_db)
    return desktop_db


def _run_browser_fallback(url):
    print("Desktop GUI backend is unavailable. Falling back to browser mode.")
    print(f"Open URL: {url}")
    print("Press Ctrl+C to stop the app server.")

    try:
        webbrowser.open(url)
    except Exception:
        # Keep running even if auto-open is unavailable in headless environments.
        pass

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


def main():
    base_dir = Path(__file__).resolve().parent
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prn_project.settings")

    db_path = _prepare_persistent_database(base_dir)

    import django

    django.setup()

    from django.core.management import call_command
    from django.core.wsgi import get_wsgi_application

    call_command("migrate", interactive=False, verbosity=0)

    port = _find_free_port()
    application = get_wsgi_application()
    httpd = make_server(HOST, port, application)

    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    url = f"http://{HOST}:{port}/"
    if not _wait_for_server(url):
        httpd.shutdown()
        raise RuntimeError(f"Could not start desktop server at {url}")

    try:
        import webview
    except ImportError as exc:
        httpd.shutdown()
        raise RuntimeError(
            "pywebview is not installed. Run: pip install -r requirements.txt"
        ) from exc

    try:
        window_title = f"{APP_NAME}"
        webview.create_window(window_title, url=url, min_size=(1100, 700))
        webview.start()
    except Exception as exc:
        print(
            (
                "Desktop window could not start (missing Qt/GTK bindings likely). "
                f"Reason: {exc}"
            ),
            file=sys.stderr,
        )
        _run_browser_fallback(url)
    finally:
        httpd.shutdown()
        httpd.server_close()

    print(f"Database in use: {db_path}")


if __name__ == "__main__":
    try:
        main()
    except ModuleNotFoundError as exc:
        missing_module = str(exc).split("No module named ")[-1].strip("'\"")
        print(
            (
                "Desktop launch failed: missing Python module "
                f"'{missing_module}'.\n"
                "Install desktop dependencies with:\n"
                "  pip install -r requirements.txt\n"
                "If the issue persists on Linux, install Qt support with:\n"
                "  pip install qtpy PyQt5"
            ),
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as exc:
        print(f"Desktop launch failed: {exc}", file=sys.stderr)
        sys.exit(1)
