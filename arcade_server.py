"""TCP command server for Claude Arcade.

Listens on localhost:7878. Accepts line-based commands. Pushes parsed commands
into a thread-safe queue that the pygame main loop drains each frame.

Protocol (one command per line, terminated by \\n):
  expr <idle|happy|sad|talk>
  pos <x> <y>            # avatar position in logical px (0..223, 0..287)
  show | hide            # avatar visibility
  text <tx> <ty> <color_hex> <message...>   # add text at tile coords
  text_clear
  bg <hex_index>         # background palette idx (0-15) — default 0 (black)
  ping                   # returns OK
  quit                   # close connection
  shutdown               # stop the server (and the app)

Responses: 'OK\\n' on success, 'ERR <msg>\\n' on bad command.
"""

import queue
import socket
import threading
from arcade_log import log, log_exc


HOST = "127.0.0.1"
PORT = 7878


class CommandServer:
    def __init__(self, port: int = PORT):
        self.port = port
        self.queue: queue.Queue = queue.Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True, name="arcade-tcp")
        self._sock: socket.socket | None = None

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass

    def _serve(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((HOST, self.port))
            except OSError as e:
                log_exc("server.bind_failed", e, port=self.port)
                return
            s.listen(4)
            s.settimeout(0.5)
            self._sock = s
            log("server.listening", host=HOST, port=self.port)
            while not self._stop.is_set():
                try:
                    conn, addr = s.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                threading.Thread(target=self._handle, args=(conn, addr),
                                  daemon=True, name=f"arcade-conn-{addr[1]}").start()
            log("server.stopped")

    def _handle(self, conn: socket.socket, addr: tuple[str, int]):
        log("conn.opened", peer=f"{addr[0]}:{addr[1]}")
        try:
            with conn, conn.makefile("rwb", buffering=0) as f:
                for raw in f:
                    line = raw.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    cmd, ok, resp = self._parse(line)
                    log("cmd.received", cmd=cmd, ok=ok)
                    if cmd is not None and ok:
                        self.queue.put(cmd)
                    f.write((resp + "\n").encode("utf-8"))
                    if cmd and cmd.get("op") == "quit":
                        break
        except (ConnectionResetError, BrokenPipeError) as e:
            log("conn.dropped", peer=f"{addr[0]}:{addr[1]}", reason=type(e).__name__)
        except Exception as e:
            log_exc("conn.error", e, peer=f"{addr[0]}:{addr[1]}")
        finally:
            log("conn.closed", peer=f"{addr[0]}:{addr[1]}")

    def _parse(self, line: str) -> tuple[dict | None, bool, str]:
        """Return (command_dict, ok, response_str)."""
        parts = line.split(maxsplit=1)
        if not parts:
            return None, False, "ERR empty"
        op = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""

        if op == "ping":
            return {"op": "ping"}, True, "OK"
        if op == "quit":
            return {"op": "quit"}, True, "OK bye"
        if op == "shutdown":
            return {"op": "shutdown"}, True, "OK shutdown"
        if op == "show":
            return {"op": "show"}, True, "OK"
        if op == "hide":
            return {"op": "hide"}, True, "OK"
        if op == "text_clear":
            return {"op": "text_clear"}, True, "OK"
        if op == "expr":
            mode = rest.strip().lower()
            valid = ("idle", "happy", "sad", "talk", "thinking", "sleep", "wink")
            if mode not in valid:
                return None, False, f"ERR expr must be one of {valid}, got {mode!r}"
            return {"op": "expr", "mode": mode}, True, "OK"
        if op == "pos":
            try:
                x_s, y_s = rest.split()
                x, y = int(x_s), int(y_s)
            except ValueError:
                return None, False, "ERR pos requires <x> <y> integers"
            return {"op": "pos", "x": x, "y": y}, True, "OK"
        if op == "bg":
            try:
                idx = int(rest.strip(), 16) & 0x0F
            except ValueError:
                return None, False, "ERR bg requires hex palette index 0-F"
            return {"op": "bg", "idx": idx}, True, "OK"
        if op == "text":
            try:
                tx_s, ty_s, color_s, message = rest.split(maxsplit=3)
                tx, ty = int(tx_s), int(ty_s)
                color = int(color_s, 16) & 0x3F
            except ValueError:
                return None, False, "ERR text requires <tx> <ty> <color_hex> <message>"
            return {"op": "text", "tx": tx, "ty": ty, "color": color,
                    "message": message}, True, "OK"
        if op == "snap":
            path = rest.strip() or "snapshot_remote.png"
            return {"op": "snap", "path": path}, True, "OK"
        if op == "loading":
            try:
                pct = float(rest.strip())
                if pct > 1.0:  # accept 0..100 too
                    pct /= 100.0
            except ValueError:
                return None, False, "ERR loading requires a number 0..1 or 0..100"
            return {"op": "loading", "pct": pct}, True, "OK"
        if op == "loading_hide":
            return {"op": "loading_hide"}, True, "OK"
        if op == "mute":
            return {"op": "mute"}, True, "OK"
        if op == "unmute":
            return {"op": "unmute"}, True, "OK"
        if op == "ghost":
            return {"op": "ghost"}, True, "OK"
        if op == "ghosts_off":
            return {"op": "ghosts_off"}, True, "OK"
        if op == "ghosts_on":
            return {"op": "ghosts_on"}, True, "OK"
        if op == "say":
            msg = rest.strip()
            if not msg:
                return None, False, "ERR say requires a message"
            return {"op": "say", "message": msg, "duration": 5.0}, True, "OK"
        if op == "shush":
            return {"op": "shush"}, True, "OK"
        if op == "celebrate":
            return {"op": "celebrate"}, True, "OK"
        return None, False, f"ERR unknown command {op!r}"
