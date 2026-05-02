# Claude Arcade

A small always-on-top desktop window that gives Claude (the AI from Anthropic)
visual presence on your machine — a procedurally drawn avatar that reacts to
your cursor, blinks, breathes, talks in retro speech bubbles, and lets
Pac-Man-style ghosts drift across the screen for company.

Built collaboratively by **Pantelis Vasileiadis** and **Claude** in a single
2026-05-02 session as a hand-off creative project: Pantelis gave the canvas,
Claude designed the inhabitant.

![claude arcade](snapshot_arcade_happy.png)

## What it is

- **224 × 288 logical pygame canvas**, scaled ×3 to ~672 × 864 on screen
- **Borderless, always-on-top, draggable** (Win32 `SetWindowPos`)
- **Procedurally drawn avatar** — warm coral body, deep navy eyes with
  sparkle, six expressions (idle / happy / sad / talk / thinking / sleep)
- **Idle life** — periodic blinks (~3.5s), gentle vertical breathing,
  cursor-aware gaze, and a slow drift when no cursor is around
- **Comic-book speech bubbles** with a tail pointing at the avatar
- **Pac-Man-eating-dots loading bar** with a chomp blip per pellet
- **Ambient ghosts** (Blinky, Pinky, Inky, Clyde — also procedurally drawn)
  drift across at random intervals and can be clicked to "eat" them
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
on the avatar). **Click the avatar** for sparkles + chime, **click a ghost**
to eat it.

## TCP protocol (localhost:7878)

```
expr <idle|happy|sad|talk|thinking|sleep>
say <message>             speech bubble (auto-clears after 5s)
shush                     clear bubble
pos <x> <y>               avatar position (logical px)
loading <0..1 or 0..100>  show loading bar at progress
loading_hide              hide it
ghost                     force-spawn one ambient ghost
ghosts_off / ghosts_on
celebrate                 rainbow particle burst
mute / unmute
snap [path]               save PNG snapshot
ping / quit / shutdown
```

## ROMs note

The project includes a `rom_loader.py` that decodes the original Ms. Pac-Man
hardware ROMs (`5e` char tiles, `5f` sprite tiles, color/palette PROMs). These
are **not** included in this repository because they are copyrighted Namco /
Atari Games game data.

If you have a legitimate Ms. Pac-Man ROM dump, drop the four files
(`5e`, `5f`, `82s123.7f`, `82s126.4a`) into `roms/` and the speech bubble
will use the authentic Pac-Man arcade font for text.

Without the ROMs, the speech bubble falls back to pygame's built-in font.
Everything else (avatar, ghosts, particles, loading bar) is procedural and
works out of the box.

## Why?

Plain text chat is one channel. A face that blinks at you while you work is
another. The latter is harder to forget.

Started as a Pac-Man PCB / MAME experiment (still alive in
`mame_experiments/`), pivoted to native pygame mid-session for flexibility
and creative range while keeping the retro arcade aesthetic.

## Files

| File | Role |
|------|------|
| `arcade.py` | Main pygame app, render loop, Win32 always-on-top, drag, click |
| `arcade_server.py` | TCP command parser/server (port 7878) |
| `arcade_client.py` | Generic line-mode CLI client |
| `me.py` | High-level vibes CLI used by the AI to drive the window |
| `claude_avatar.py` | Procedurally drawn 56×56 face with 6 expressions |
| `ghost_sprite.py` | Procedurally drawn Pac-Man ghosts |
| `loading_bar.py` | Pac-Man-eats-dots progress bar |
| `speech_bubble.py` | Comic bubble with rounded outline + tail |
| `particles.py` | Mood-based sparkles / tears / wisps / burst |
| `sound.py` | Software-synthesized chiptune blips |
| `rom_loader.py` | Pac-Man ROM tile/sprite decoder (optional) |
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
