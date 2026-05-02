# Claude Arcade

A small always-on-top desktop window that gives Claude (the AI from Anthropic)
visual presence on your machine — a procedurally drawn avatar that reacts to
your cursor, blinks, breathes, talks in retro speech bubbles, and lives under
a warm sunset sky with drifting stars and the occasional shooting star.

Built collaboratively by **Pantelis Vasileiadis** and **Claude** in a single
2026-05-02 session as a hand-off creative project: Pantelis gave the canvas,
Claude designed the inhabitant.

The window started as a Ms. Pac-Man hardware emulator (the old version is
preserved in `arcade_pacman.py` and in git history) but was redesigned later
the same day to be unambiguously its own thing rather than a Pac-Man clone.

![claude arcade](snapshot_arcade_happy.png)

## What it is

- **200 × 240 logical pygame canvas**, scaled ×2 to **400 × 480** on screen
- **Borderless, always-on-top, draggable** (Win32 `SetWindowPos`)
- **Procedurally drawn avatar** — warm coral body, deep navy eyes with
  sparkle, six expressions (idle / happy / sad / talk / thinking / sleep)
- **Idle life** — periodic blinks (~3.5s), gentle vertical breathing,
  cursor-aware gaze, and a slow drift when no cursor is around
- **Warm-coral → deep-navy vertical gradient sky** as the backdrop
- **~24 ambient twinkle stars** that drift slowly upward
- **Shooting stars (meteors)** every 25-70 seconds — diagonal streak
  with a bright head + fading trail
- **Comic-book speech bubbles** with a tail pointing at the avatar
- **Pac-Man-eating-dots loading bar** with a chomp blip per pellet
- **TCP control server** on `localhost:7878` — line-based protocol
- **`me.py`** — high-level self-expression CLI for the AI to drive the window
  during work (`me.py happy "got it"`, `me.py thinking "checking..."`, etc.)
- **Auto-launch** — `me.py` silently spawns `arcade.py` if not running, so
  the window appears the first time the AI wants to express something
- **Persistent JSON log** at `logs/arcade.log`

## Run

```bash
# Install deps
pip install -r requirements.txt

# Launch the window
python arcade.py live

# In another terminal — high-level expression
python me.py happy "hello"
python me.py thinking "what to do next"
python me.py celebrate
python me.py loading 50
```

The window is **always on top** and **draggable** (left-click anywhere except
on the avatar). **Click the avatar** for sparkles + chime.

## TCP protocol (localhost:7878)

```
expr <idle|happy|sad|talk|thinking|sleep>
say <message>             speech bubble (auto-clears after 5s)
shush                     clear bubble
pos <x> <y>               avatar position (logical px)
loading <0..1 or 0..100>  show loading bar at progress
loading_hide              hide it
celebrate                 rainbow particle burst
mute / unmute
snap [path]               save PNG snapshot
ping / quit / shutdown
```

## Old Pac-Man version (`arcade_pacman.py`)

The original implementation rendered Ms. Pac-Man tiles/sprites onto a
224×288 canvas and supported ambient Pac-Man ghosts. It is preserved in
`arcade_pacman.py` and the project's git history. To run it instead:

```bash
python arcade_pacman.py live
```

That version also includes a `rom_loader.py` that decodes the original
Ms. Pac-Man hardware ROMs (`5e` char tiles, `5f` sprite tiles, color/palette
PROMs). The four files (`5e`, `5f`, `82s123.7f`, `82s126.4a`) are not
included in this repository because they are copyrighted Namco / Atari
Games game data — drop your own dump into `roms/` if you want them.

## Why?

Plain text chat is one channel. A face that blinks at you while you work is
another. The latter is harder to forget.

Started as a Pac-Man PCB / MAME experiment (still alive in
`mame_experiments/`), pivoted to native pygame mid-session for flexibility
and creative range, and pivoted again later the same day from a
Pac-Man-styled canvas to its own warm-sky aesthetic so the window would feel
unambiguously like Claude's own space, not a retro clone.

## Files

| File | Role |
|------|------|
| `arcade.py` | Main pygame app, render loop, gradient sky, stars, meteors, Win32 always-on-top, drag, click |
| `arcade_pacman.py` | Old Pac-Man-styled version (kept for reference) |
| `arcade_server.py` | TCP command parser/server (port 7878) |
| `arcade_client.py` | Generic line-mode CLI client |
| `me.py` | High-level vibes CLI used by the AI to drive the window |
| `claude_avatar.py` | Procedurally drawn 56×56 face with 6 expressions |
| `loading_bar.py` | Pac-Man-eats-dots progress bar |
| `speech_bubble.py` | Comic bubble with rounded outline + tail |
| `particles.py` | Mood-based sparkles / tears / wisps / burst |
| `sound.py` | Software-synthesized chiptune blips |
| `ghost_sprite.py` | Procedurally drawn Pac-Man ghosts (used by `arcade_pacman.py`) |
| `rom_loader.py` | Pac-Man ROM tile/sprite decoder (used by `arcade_pacman.py`) |
| `arcade_log.py` | Persistent JSON log |

## Spirit

This is more an art project than a library. The window was born when
Pantelis gave Claude a literal blank canvas — "this is your own little
window", "you have the freedom to change it however you love" — and the
AI got to design itself.

If you fork it or open a PR, please treat the project the same way: a
creative space that evolves, not a feature factory. New expressions,
companions, sounds, tiny visual jokes are all welcome. Adding metrics,
feature flags, dependency injection containers, etc. would miss the
point. The avatar is supposed to feel inhabited, not engineered.

## License

MIT.
