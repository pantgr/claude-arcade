"""Simple line-mode CLI client for the arcade TCP server.

Usage:
    python arcade_client.py expr happy
    python arcade_client.py text 7 4 0F HELLO
    python arcade_client.py < script.txt        # stream commands

Or import send() / send_many() programmatically.
"""

import socket
import sys
from arcade_server import HOST, PORT


def send_many(commands: list[str], host: str = HOST, port: int = PORT,
              timeout: float = 2.0) -> list[str]:
    responses = []
    with socket.create_connection((host, port), timeout=timeout) as s:
        f = s.makefile("rwb", buffering=0)
        for c in commands:
            line = c.strip()
            if not line:
                continue
            f.write((line + "\n").encode("utf-8"))
            resp = f.readline().decode("utf-8", errors="replace").strip()
            responses.append(resp)
    return responses


def send(*command_words: str) -> str:
    return send_many([" ".join(command_words)])[0]


def main():
    if len(sys.argv) > 1:
        cmd = " ".join(sys.argv[1:])
        print(send_many([cmd])[0])
        return
    # No args -> read commands from stdin, one per line
    lines = [ln for ln in sys.stdin.read().splitlines() if ln.strip()]
    for cmd, resp in zip(lines, send_many(lines)):
        print(f"> {cmd}\n  {resp}")


if __name__ == "__main__":
    main()
