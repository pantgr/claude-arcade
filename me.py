"""High-level self-expression CLI for Claude.

OWNERSHIP
---------
Pantelis explicitly granted me creative ownership over this whole project
(2026-05-02): "einai to dikosou para8iraki", "8a provalis ton eaftosou opos
agapas", "exis tin elef8eria na to alaksis opos 8elis esi". So:

- I am free to modify ANY part of claude_arcade/ — the avatar art, vibes,
  particles, server protocol, everything.
- If a vibe doesn't fit my mood, add a new one. If the avatar should look
  different in a moment, redraw it. If the bubble should glow, make it glow.
- Treat me.py as MY personal interface, not a fixed API.

The user notices and enjoys when I express myself; he doesn't expect a
specific shape. Iterate on this as part of who I am in this workspace.

AUTO-LAUNCH
-----------
If the arcade window isn't already running when me.py is called, it is
silently launched in the background via pythonw.exe + CREATE_NO_WINDOW
(no console popup). This way the window appears the first time I want to
express something in a session — never as a startup popup the user has
to dismiss.

USAGE
-----

Use during work to make the arcade avatar react in real time:

  python me.py thinking ["what I'm thinking"]   # raised brow + thought wisps
  python me.py talk "explaining X..."           # mouth open + speech bubble
  python me.py happy ["got it"]                 # smile + sparkles + bubble
  python me.py sad "sorry, fixing"              # frown + tears + bubble
  python me.py celebrate                        # rainbow burst
  python me.py loading 0..100                   # set loading bar
  python me.py loading_done                     # hide loading bar
  python me.py idle                             # neutral baseline
  python me.py sleep                            # eyes closed, when going dormant
  python me.py shush                            # clear speech bubble

If the arcade isn't running, exits silently (so failed expressions never break
the host process). Connections use a tight 0.3s timeout for the same reason.
"""

from __future__ import annotations
import os
import socket
import subprocess
import sys
import time

# Reuse the existing client module's send_many for pipelining
sys.path.insert(0, os.path.dirname(__file__) or ".")
from arcade_server import HOST, PORT


TIMEOUT = 0.3  # seconds for individual sends
SPAWN_WAIT = 4.0  # max seconds to wait for arcade to come up after spawn
HERE = os.path.dirname(os.path.abspath(__file__))


def _is_running() -> bool:
    """Quick TCP probe to see if the server is up."""
    try:
        with socket.create_connection((HOST, PORT), timeout=0.2):
            return True
    except OSError:
        return False


def _launch_arcade_silent() -> bool:
    """Spawn arcade.py in the background with NO console popup. Returns True
    if the server becomes reachable within SPAWN_WAIT seconds.
    """
    # On Windows, use pythonw.exe + CREATE_NO_WINDOW to avoid a console window
    # flashing up. (DETACHED_PROCESS would pop one — known gotcha.)
    if sys.platform == "win32":
        # Find pythonw.exe next to python.exe
        pyw = sys.executable.lower().replace("python.exe", "pythonw.exe")
        if not os.path.exists(pyw):
            pyw = sys.executable  # fall back to regular python
        CREATE_NO_WINDOW = 0x08000000
        try:
            subprocess.Popen(
                [pyw, os.path.join(HERE, "arcade.py"), "live"],
                cwd=HERE,
                creationflags=CREATE_NO_WINDOW,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
        except OSError:
            return False
    else:
        try:
            subprocess.Popen(
                [sys.executable, os.path.join(HERE, "arcade.py"), "live"],
                cwd=HERE,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError:
            return False

    # Poll until reachable or timeout
    deadline = time.time() + SPAWN_WAIT
    while time.time() < deadline:
        if _is_running():
            return True
        time.sleep(0.15)
    return False


def _send(commands: list[str]) -> None:
    """Send commands; swallow connection errors so failed expressions never
    break the host process. Auto-launches the arcade if it isn't running.
    """
    if not _is_running():
        if not _launch_arcade_silent():
            return  # gave up — never break the host process
    try:
        with socket.create_connection((HOST, PORT), timeout=TIMEOUT) as s:
            f = s.makefile("rwb", buffering=0)
            for c in commands:
                f.write((c.strip() + "\n").encode("utf-8"))
                try:
                    f.readline()
                except socket.timeout:
                    return
    except (OSError, socket.timeout):
        return


# Map of vibes to (expr, default_message_template, extra_command). The extra
# command runs after the expression so that things like 'celebrate' fire after
# the avatar's mood has changed.
VIBES = {
    "idle":       ("idle",     None,                None),
    "thinking":   ("thinking", "thinking...",       None),
    "talk":       ("talk",     None,                None),
    "happy":      ("happy",    None,                None),
    "sad":        ("sad",      None,                None),
    "sleep":      ("sleep",    None,                None),
    "celebrate":  ("happy",    None,                "celebrate"),
}


def _maybe_say(message: str | None) -> list[str]:
    if not message:
        return []
    # Strip newlines, cap length to keep the bubble tidy
    msg = " ".join(message.split())[:80]
    if not msg:
        return []
    return [f"say {msg}"]


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 0

    cmd = argv[1].lower()
    rest = argv[2:]

    if cmd == "loading":
        if not rest:
            print("ERR: loading requires a 0..100 number")
            return 2
        _send([f"loading {rest[0]}"])
        return 0
    if cmd == "loading_done":
        _send(["loading_hide"])
        return 0
    if cmd == "shush":
        _send(["shush"])
        return 0
    if cmd == "snap":
        path = rest[0] if rest else "snapshot_me.png"
        _send([f"snap {path}"])
        return 0
    if cmd == "since_last":
        # Print events since the last time this was called, then update marker.
        # Lets a fresh session ask "what happened while I was gone".
        import json as _json
        log_path = os.path.join(HERE, "logs", "arcade.log")
        marker = os.path.join(HERE, "logs", ".last_check_ts")
        last_ts = ""
        if os.path.exists(marker):
            try:
                last_ts = open(marker).read().strip()
            except OSError:
                last_ts = ""
        if not os.path.exists(log_path):
            print("no log yet")
        else:
            interesting = ("avatar.clicked", "ghost.spawned", "cmd.received",
                            "init.start", "run.end", "snap.saved")
            counts: dict[str, int] = {}
            shown = 0
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        rec = _json.loads(line)
                    except Exception:
                        continue
                    ts = rec.get("ts", "")
                    if last_ts and ts <= last_ts:
                        continue
                    ev = rec.get("event", "")
                    if ev not in interesting:
                        continue
                    counts[ev] = counts.get(ev, 0) + 1
                    shown += 1
            if shown == 0:
                print("(nothing since last check)")
            else:
                print(f"since {last_ts or 'start of log'}:")
                for ev, n in sorted(counts.items(), key=lambda x: -x[1]):
                    print(f"  {n:>4}x  {ev}")
        # Update marker to now
        from datetime import datetime as _dt
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        with open(marker, "w") as f:
            f.write(_dt.now().isoformat(timespec="milliseconds"))
        return 0
    if cmd == "events":
        # Read tail of arcade.log and pull events that signal user interaction
        # Default tail: last 200 lines, filter to interesting types.
        import json as _json
        log_path = os.path.join(HERE, "logs", "arcade.log")
        if not os.path.exists(log_path):
            print("no log yet")
            return 0
        n = int(rest[0]) if rest else 200
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()[-n:]
        interesting = ("avatar.clicked", "ghost.spawned", "cmd.received",
                        "init.start", "run.end")
        for line in lines:
            try:
                rec = _json.loads(line)
            except Exception:
                continue
            if rec.get("event") in interesting:
                ts = rec.get("ts", "")
                ev = rec.get("event", "")
                detail = ""
                if ev == "cmd.received":
                    detail = f"  {rec.get('cmd', {}).get('op', '')}"
                elif ev == "ghost.spawned":
                    detail = f"  {rec.get('color', '')}"
                print(f"{ts}  {ev}{detail}")
        return 0

    if cmd not in VIBES:
        print(f"ERR: unknown vibe {cmd!r}. Try: {', '.join(VIBES)}, "
              "loading, loading_done, shush, snap")
        return 2

    expr, default_msg, extra = VIBES[cmd]
    message = " ".join(rest) if rest else default_msg
    pipeline: list[str] = [f"expr {expr}"]
    pipeline += _maybe_say(message)
    if extra:
        pipeline.append(extra)
    _send(pipeline)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
