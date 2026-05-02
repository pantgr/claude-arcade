"""Structured persistent logger for claude_arcade.

Writes to logs/arcade.log, one event per line, JSON-formatted.
Survives restarts. Tail with: Get-Content logs/arcade.log -Tail 50
"""

from datetime import datetime
from pathlib import Path
import json
import threading
import sys


_LOG_PATH = Path(__file__).parent / "logs" / "arcade.log"
_LOG_PATH.parent.mkdir(exist_ok=True)
_LOCK = threading.Lock()


def log(event: str, **fields) -> None:
    """Write one structured event line. Always flushes."""
    record = {
        "ts": datetime.now().isoformat(timespec="milliseconds"),
        "event": event,
        **fields,
    }
    line = json.dumps(record, ensure_ascii=False)
    with _LOCK:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
    # Also echo to stderr for live tail-following
    print(line, file=sys.stderr, flush=True)


def log_exc(event: str, exc: BaseException, **fields) -> None:
    """Log an exception with type and message."""
    log(event, exc_type=type(exc).__name__, exc_msg=str(exc), **fields)
