from __future__ import annotations

import threading
import time

from flask import Flask

from .sync_service import run_due_syncs


_worker_started = False
_worker_lock = threading.Lock()


def start_sync_scheduler(app: Flask) -> None:
    global _worker_started
    if app.config.get("TESTING"):
        return
    if app.config.get("DISABLE_SYNC_SCHEDULER", False):
        return

    with _worker_lock:
        if _worker_started:
            return
        _worker_started = True

    interval_seconds = int(app.config.get("SYNC_SCHEDULER_POLL_SECONDS", 30))

    def _worker() -> None:
        while True:
            try:
                with app.app_context():
                    run_due_syncs()
            except Exception:
                app.logger.exception("Sync scheduler loop failed.")
            time.sleep(max(5, interval_seconds))

    thread = threading.Thread(target=_worker, name="sync-scheduler", daemon=True)
    thread.start()
