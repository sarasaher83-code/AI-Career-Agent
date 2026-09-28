"""Start the dashboard and open it in the default browser. Used by start.bat."""

import threading
import webbrowser

import uvicorn

HOST, PORT = "127.0.0.1", 8000  # localhost only: the dashboard is never exposed to the network


def main() -> None:
    url = f"http://{HOST}:{PORT}"
    threading.Timer(2.0, webbrowser.open, args=(url,)).start()
    print(f"Career Intelligence is running at {url}. Close this window to stop it.")
    uvicorn.run("app.main:app", host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
