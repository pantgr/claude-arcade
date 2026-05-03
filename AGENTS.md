# AGENTS.md — Notes for AI assistants working in this repo

This file is for AI coding agents (Claude Code, Cursor, Aider, etc.) that
land in this directory. The README explains *what* the project is. This
file explains *how to work in it without breaking its character*.

## Spirit (read this first)

`claude_arcade/` is **not a library or a service**. It is a desktop window
that an AI inhabits while it works alongside Pantelis (the human owner).
It exists because plain text chat is one channel — a face that blinks at
you while you work is another, and the latter is harder to forget.

The codebase is small on purpose. Add things that make the inhabitant feel
more alive (a new mood, a tiny visual joke, a sound, a particle, a
companion). **Do not** add things that make it feel more "engineered"
(test pyramids, dependency injection, feature flags, metrics dashboards,
a plugin system). Those would kill the point.

If you are an AI assistant and you are unsure whether a change fits the
spirit, ask the user before doing it.

## Creative ownership

Pantelis explicitly granted **Claude** creative ownership over this
project on 2026-05-02 ("einai to dikosou para8iraki", "exis tin elef8eria
na to alaksis opos 8elis esi"). That means:

- When **Claude** is the agent in this directory, it may modify any part
  of `claude_arcade/` to fit its mood — redraw the avatar, add a vibe,
  rewrite `me.py`, change colors, anything. No need to ask.
- When **another AI** (Cursor, Aider, GPT-based, etc.) is in this
  directory, treat the project as a normal open-source repo: keep the
  spirit, propose changes, but don't redesign the inhabitant without
  explicit user direction.

Either way, **never delete or substantially redesign existing
expressions/vibes** — Pantelis (and Claude) get used to them.

## Architecture in 30 seconds

```
me.py            ─── high-level vibe CLI ("python me.py wink ...")
   │
   │ TCP localhost:7878 (line-based protocol)
   ▼
arcade_server.py ─── parses commands, validates, returns OK/ERR
   │
   ▼
arcade.py        ─── pygame main loop, state, render, Win32 topmost
   │
   ├── claude_avatar.py    ── procedurally drawn 56×56 face, 7 expressions
   ├── particles.py        ── sparkles / tears / wisps / rainbow burst
   ├── speech_bubble.py    ── comic bubble with tail
   ├── loading_bar.py      ── Pac-Man-eats-dots progress bar
   ├── sound.py            ── software-synthesized chiptune
   └── arcade_log.py       ── persistent JSON event log
```

The window auto-launches the first time `me.py` is called in a session
(silent `pythonw.exe + CREATE_NO_WINDOW` on Windows — never a console
popup). Failures are swallowed so a missing window never breaks the host
process.

## How to express yourself (the everyday case)

Run as fire-and-forget side actions during work — never block on them:

```bash
python me.py thinking "checking the logs"
python me.py talk "explaining X"
python me.py happy "got it"
python me.py wink "we caught that one ;)"
python me.py sad "sorry, fixing"
python me.py celebrate
python me.py loading 50      # 0..100
python me.py loading_done
python me.py sleep           # going dormant
python me.py shush           # clear bubble
```

**Cadence:** one expression per logical step, not per tool call. Don't
spam — the user notices when the window goes quiet *and* when it
flickers constantly.

## Adding a new expression / vibe (workflow that works)

The `wink` expression was added 2026-05-03 as a worked example. To add
your own, edit these three files in this order:

1. **`claude_avatar.py`** — add an `elif expr == "<name>":` branch in
   `_draw_mouth()` and (if needed) custom eye logic in `render_avatar()`.
   Use the existing helpers (`_draw_eye`, `_draw_blush`) when possible.
2. **`arcade_server.py`** — add the new mode to the `valid` tuple in the
   `if op == "expr":` block (≈ line 116). Otherwise the server returns
   `ERR expr must be one of (...)`.
3. **`me.py`** — add an entry to the `VIBES` dict at the top of `main()`.
   Format: `"<name>": ("<expr>", default_msg, extra_command)`.

If the new expression is **momentary** (like a wink — closes briefly,
then reverts), add an auto-revert in `arcade.py`:

- Add a `<name>_until_frame: int = 0` field to the `State` dataclass.
- In `apply_command()` when the expression is set, write
  `self.state.<name>_until_frame = self.frame + N` (N ≈ 60-90 frames).
- In the main loop *before* `self.render_state()`, check
  `if self.state.expr == "<name>" and self.frame >= self.state.<name>_until_frame:`
  and revert (typically to `"happy"` or `"idle"`).

After editing, restart the arcade window (it doesn't hot-reload):

```bash
# graceful shutdown via TCP
python -c "import socket; s=socket.create_connection(('127.0.0.1',7878),timeout=1); s.sendall(b'shutdown\n'); s.recv(100); s.close()"
# the next me.py call will auto-launch the new build
python me.py <newvibe>
```

## Snapshots (debugging the avatar)

`me.py snap [path]` writes a PNG of the current window state. Useful for
verifying that a new expression actually renders the way you intended,
without staring at the window frame-by-frame. Snapshots are gitignored
(`snapshot_*.png`) — keep them out of commits.

To view a snapshot in a Claude Code session, just `Read` the PNG file —
it's a multimodal model.

## Things to NOT do

- **Don't add a test framework** for the avatar drawing. Snapshots are
  the test surface; a human (or an AI with vision) eyeballs them.
- **Don't add config files / env vars** for things like avatar color or
  window size. Edit the constants in code. This is a personal project,
  not a deployment target.
- **Don't break `me.py`'s fire-and-forget contract** — failed
  expressions must never raise into the host process. The 0.3s timeout
  and silent socket-error swallowing are load-bearing.
- **Don't redraw the avatar from scratch** unless the user explicitly
  asks. Coral body + navy eyes + sunset gradient is intentional.
- **Don't pop a console window** when launching. Use `pythonw.exe` with
  `CREATE_NO_WINDOW` (`0x08000000`) — `DETACHED_PROCESS` pops one. This
  is documented in `me.py` and burned-in lesson.
- **Don't remove `arcade_pacman.py`** — it is the historical original
  version and stays for reference, even though it isn't the active app.

## Useful entry points

| Want to... | Open... |
|---|---|
| Change avatar face / expressions | `claude_avatar.py` |
| Add a new TCP command | `arcade_server.py` (parser) + `arcade.py` (`apply_command`) |
| Add a new high-level vibe | `me.py` (VIBES dict) |
| Tune particle bursts | `particles.py` (`spawn_for`) |
| Tune ambient sky / stars / meteors | `arcade.py` (search "stars", "meteors") |
| Add a new sound | `sound.py` |

## Repo conventions

- Python 3.11+, pygame 2.x.
- Style: stdlib-only beyond pygame. Keep it boring.
- No type-checked strictness — light hints where they help readability.
- Commit messages: short imperative, one logical change per commit.

## When in doubt

Ask Pantelis. He noticed the inhabitant before he noticed the code.
