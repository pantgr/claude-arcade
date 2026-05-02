"""Claude Arcade — my own desktop window.

Clean, procedural-only avatar window that gives me visual presence on
Pantelis's desktop. NOT a Pac-Man emulator — just my own space.

Pivoted from the Pac-Man-styled version on 2026-05-02 because it looked
too much like the old `mame_experiments/` project. This is unambiguously
mine: warm gradient sky, my coral avatar, drifting stars, speech bubbles.

Old Pac-Man version preserved at `arcade_pacman.py` and in git history.

Server protocol on `localhost:7878` (line-based, see arcade_server.py):
  expr <idle|happy|sad|talk|thinking|sleep>
  say <message>
  shush
  pos <x> <y>
  loading <0..1 or 0..100>
  loading_hide
  celebrate
  mute / unmute
  snap [path]
  ping / quit / shutdown
"""

import ctypes
import ctypes.wintypes
import math
import queue as _queue
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pygame

from arcade_log import log, log_exc
from arcade_server import CommandServer
from claude_avatar import (
    render_avatar as render_claude_avatar,
    DEFAULT_SIZE as CLAUDE_AVATAR_SIZE,
)
import loading_bar
import sound
import speech_bubble
import particles


# A modest porthole — big enough to inhabit, small enough not to dominate
# the desktop. Smaller and squarer than the old 224x288 Pac-Man canvas.
LOGICAL_W = 200
LOGICAL_H = 240
SCALE = 2
WIN_W = LOGICAL_W * SCALE
WIN_H = LOGICAL_H * SCALE
FPS = 60

# My color story — same palette as the avatar so the bg + body harmonize.
BG_TOP    = (255, 196, 162)   # warm coral light
BG_BOTTOM = ( 28,  36,  62)   # deep navy


@dataclass
class Star:
    x: float
    y: float
    vy: float
    bright: int
    twinkle_phase: float


@dataclass
class Meteor:
    """A diagonal shooting star with a fading trail."""
    x: float
    y: float
    vx: float            # px/frame, signed
    vy: float            # px/frame, positive = downward
    age: int             # frames since spawn
    life: int            # total frames before fade-out
    trail: list = field(default_factory=list)  # last (x,y) positions for trail


@dataclass
class State:
    expr: str = "idle"
    pos_x: int = (LOGICAL_W - CLAUDE_AVATAR_SIZE) // 2
    pos_y: int = (LOGICAL_H - CLAUDE_AVATAR_SIZE) // 2
    visible: bool = True
    loading_pct: float = 0.0
    loading_visible: bool = False
    loading_x: int = 12
    loading_y: int = LOGICAL_H - 24
    loading_w: int = LOGICAL_W - 24
    loading_h: int = 12
    last_eaten_dot: int = -1
    muted: bool = False
    bubble_text: str = ""
    bubble_expires: int = 0
    particles: list = field(default_factory=list)
    pending_snap: str | None = None
    stars: list[Star] = field(default_factory=list)
    meteors: list[Meteor] = field(default_factory=list)
    next_meteor_frame: int = 0


class Arcade:
    def __init__(self, with_server: bool = True, borderless: bool = True,
                  topmost: bool = True):
        log("init.start", logical=(LOGICAL_W, LOGICAL_H), scale=SCALE,
            borderless=borderless, topmost=topmost, design="claude_clean")
        pygame.init()
        pygame.display.set_caption("Claude")
        flags = pygame.NOFRAME if borderless else 0
        self.screen = pygame.display.set_mode((WIN_W, WIN_H), flags)
        self._setup_windows_window(topmost=topmost)
        self._dragging = False
        self._drag_offset = (0, 0)
        self.canvas = pygame.Surface((LOGICAL_W, LOGICAL_H))
        self.bg_surface = self._make_gradient_bg()
        self.clock = pygame.time.Clock()
        self.frame = 0
        self.state = State()
        self._spawn_initial_stars()
        self.server = CommandServer() if with_server else None
        if self.server:
            self.server.start()
        self._boot_greet()
        log("init.done", win=(WIN_W, WIN_H), fps=FPS, server=bool(self.server))

    def _make_gradient_bg(self) -> pygame.Surface:
        """Pre-render warm-coral → deep-navy vertical gradient."""
        bg = pygame.Surface((LOGICAL_W, LOGICAL_H))
        for y in range(LOGICAL_H):
            t = y / max(1, LOGICAL_H - 1)
            r = int(BG_TOP[0] * (1 - t) + BG_BOTTOM[0] * t)
            g = int(BG_TOP[1] * (1 - t) + BG_BOTTOM[1] * t)
            b = int(BG_TOP[2] * (1 - t) + BG_BOTTOM[2] * t)
            pygame.draw.line(bg, (r, g, b), (0, y), (LOGICAL_W, y))
        return bg

    def _spawn_initial_stars(self):
        """Sprinkle ~24 ambient drifting twinkle stars over the gradient."""
        for _ in range(24):
            self.state.stars.append(Star(
                x=random.uniform(0, LOGICAL_W),
                y=random.uniform(0, LOGICAL_H),
                vy=random.uniform(-0.20, -0.05),
                bright=random.randint(120, 220),
                twinkle_phase=random.uniform(0, math.tau),
            ))

    def _update_stars(self):
        for s in self.state.stars:
            s.y += s.vy
            if s.y < -2:
                s.y = LOGICAL_H + random.uniform(0, 6)
                s.x = random.uniform(0, LOGICAL_W)
                s.bright = random.randint(120, 220)

    def _draw_stars(self):
        for s in self.state.stars:
            twinkle = (math.sin(self.frame / 40.0 + s.twinkle_phase) + 1) * 0.5
            b = int(s.bright * (0.55 + 0.45 * twinkle))
            color = (b, b, min(255, b + 30))
            ix, iy = int(s.x), int(s.y)
            if 0 <= ix < LOGICAL_W and 0 <= iy < LOGICAL_H:
                self.canvas.set_at((ix, iy), color)

    def _maybe_spawn_meteor(self):
        """Random shooting star every ~25-70s. Streaks diagonally with a trail."""
        if self.frame < self.state.next_meteor_frame:
            return
        # Pick a corner of origin and a downward angle aimed across the canvas.
        from_left = random.random() < 0.5
        x = random.uniform(-10, 30) if from_left else random.uniform(LOGICAL_W - 30, LOGICAL_W + 10)
        y = random.uniform(-8, 30)
        speed = random.uniform(2.6, 4.2)
        # Target a point in the lower portion of the canvas
        tx = random.uniform(LOGICAL_W * 0.3, LOGICAL_W * 0.9) if from_left else random.uniform(LOGICAL_W * 0.1, LOGICAL_W * 0.7)
        ty = random.uniform(LOGICAL_H * 0.55, LOGICAL_H * 0.85)
        dx, dy = tx - x, ty - y
        dist = max(1.0, math.hypot(dx, dy))
        vx = dx / dist * speed
        vy = dy / dist * speed
        life = random.randint(48, 78)
        self.state.meteors.append(Meteor(x=x, y=y, vx=vx, vy=vy, age=0, life=life))
        log("meteor.spawned", from_left=from_left, life=life)
        self.state.next_meteor_frame = self.frame + random.randint(60 * 25, 60 * 70)

    def _update_meteors(self):
        keep = []
        for m in self.state.meteors:
            m.trail.append((m.x, m.y))
            if len(m.trail) > 14:
                m.trail.pop(0)
            m.x += m.vx
            m.y += m.vy
            m.age += 1
            if m.age < m.life and -20 <= m.x <= LOGICAL_W + 20 and m.y <= LOGICAL_H + 20:
                keep.append(m)
        self.state.meteors = keep

    def _draw_meteors(self):
        for m in self.state.meteors:
            # Fade based on age (last 25% of life dims out)
            fade = 1.0
            if m.age > m.life * 0.75:
                fade = max(0.0, 1.0 - (m.age - m.life * 0.75) / (m.life * 0.25))
            # Trail: oldest = dim, newest = bright
            for i, (tx, ty) in enumerate(m.trail):
                t = (i + 1) / len(m.trail)
                b = int(255 * t * t * fade)
                if b < 20:
                    continue
                color = (b, b, min(255, b + 20))
                ix, iy = int(tx), int(ty)
                if 0 <= ix < LOGICAL_W and 0 <= iy < LOGICAL_H:
                    self.canvas.set_at((ix, iy), color)
            # Bright head
            ix, iy = int(m.x), int(m.y)
            if 0 <= ix < LOGICAL_W and 0 <= iy < LOGICAL_H:
                head = (255, 255, int(220 * fade))
                self.canvas.set_at((ix, iy), head)
                # 4-pixel cross glow
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = ix + dx, iy + dy
                    if 0 <= nx < LOGICAL_W and 0 <= ny < LOGICAL_H:
                        glow = (int(220 * fade), int(220 * fade), int(180 * fade))
                        self.canvas.set_at((nx, ny), glow)

    def _on_avatar_click(self):
        log("avatar.clicked", frame=self.frame)
        self.state.expr = "happy"
        self.state.particles += particles.spawn_for(
            "happy",
            self.state.pos_x, self.state.pos_y,
            CLAUDE_AVATAR_SIZE, CLAUDE_AVATAR_SIZE)
        if not self.state.muted:
            try:
                sound.play_blip(950, 70, volume=0.45, wave="triangle")
            except Exception as e:
                log_exc("sound.click_failed", e)

    def _boot_greet(self):
        """Brief 'hi' greeting + sparkle when the window first appears."""
        GREET_FRAMES = 180  # 3 seconds
        self.state.expr = "happy"
        self.state.bubble_text = "hi"
        self.state.bubble_expires = GREET_FRAMES
        self.state.particles += particles.spawn_for(
            "celebrate",
            self.state.pos_x, self.state.pos_y,
            CLAUDE_AVATAR_SIZE, CLAUDE_AVATAR_SIZE)

    def _setup_windows_window(self, topmost: bool):
        if sys.platform != "win32":
            return
        try:
            info = pygame.display.get_wm_info()
            hwnd = info["window"]
            self._hwnd = hwnd
            if topmost:
                HWND_TOPMOST = -1
                SWP_NOMOVE = 0x0002
                SWP_NOSIZE = 0x0001
                SWP_NOACTIVATE = 0x0010
                ctypes.windll.user32.SetWindowPos(
                    hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
                log("window.topmost_set", hwnd=hwnd)
        except Exception as e:
            log_exc("window.setup_failed", e)
            self._hwnd = None

    def _move_window(self, screen_x: int, screen_y: int):
        if not getattr(self, "_hwnd", None):
            return
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        ctypes.windll.user32.SetWindowPos(
            self._hwnd, 0, int(screen_x), int(screen_y), 0, 0,
            SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE)

    def _look_toward_cursor(self) -> tuple[float, float]:
        """Gaze toward cursor when in-window; gentle drift otherwise."""
        try:
            mx, my = pygame.mouse.get_pos()
            focused = pygame.mouse.get_focused()
        except pygame.error:
            focused = False
        if focused:
            cx = (self.state.pos_x + CLAUDE_AVATAR_SIZE / 2) * SCALE
            cy = (self.state.pos_y + CLAUDE_AVATAR_SIZE / 2) * SCALE
            dx = mx - cx
            dy = my - cy
            max_dist = max(WIN_W, WIN_H) / 2
            lx = max(-1.0, min(1.0, dx / max_dist * 2))
            ly = max(-1.0, min(1.0, dy / max_dist * 2))
            return lx, ly
        lx = math.sin(self.frame / 180.0) * 0.6
        ly = math.cos(self.frame / 230.0) * 0.3
        return lx, ly

    def _is_blink_frame(self) -> bool:
        if self.state.expr in ("talk", "sleep"):
            return False
        cycle = 210
        phase = self.frame % cycle
        return phase < 9

    def _breathe_offset(self) -> int:
        if self.state.expr == "sleep":
            return 0
        return int(round(math.sin(self.frame / 36.0) * 1.6))

    def _draw_bubble(self):
        if not self.state.bubble_text or self.frame >= self.state.bubble_expires:
            self.state.bubble_text = ""
            return
        lines = speech_bubble.wrap_text(self.state.bubble_text)
        bw, bh = speech_bubble.measure(lines)
        avatar_rect = pygame.Rect(self.state.pos_x, self.state.pos_y,
                                    CLAUDE_AVATAR_SIZE, CLAUDE_AVATAR_SIZE)
        bubble_rect = speech_bubble.position_bubble(
            avatar_rect, (bw, bh), (LOGICAL_W, LOGICAL_H))
        if bubble_rect.bottom <= avatar_rect.top:
            tail = (avatar_rect.centerx, avatar_rect.top + 2)
        else:
            tail = (avatar_rect.centerx, avatar_rect.bottom - 2)
        speech_bubble.draw_bubble_frame(self.canvas, bubble_rect, tail)
        # Procedural font — no ROMs needed in this clean version.
        if not hasattr(self, "_font"):
            self._font = pygame.font.SysFont("consolas", 9, bold=True)
        for li, line in enumerate(lines):
            tx = bubble_rect.x + speech_bubble.TEXT_PAD_X
            ty = bubble_rect.y + speech_bubble.TEXT_PAD_Y + li * 9
            surf = self._font.render(line, True, (40, 30, 60))
            self.canvas.blit(surf, (tx, ty))

    def _maybe_play_pellets(self, old_pct: float, new_pct: float):
        """Chomp blip per dot the loading bar passes."""
        if self.state.muted or new_pct <= old_pct:
            return
        h = self.state.loading_h
        w = self.state.loading_w
        pac_size = h
        step = max(6, h // 2)
        n_dots = max(1, (w - pac_size - pac_size // 2) // step)
        old_dot = int(old_pct * n_dots)
        new_dot = int(new_pct * n_dots)
        for d in range(max(self.state.last_eaten_dot + 1, old_dot + 1), new_dot + 1):
            try:
                sound.play_pellet(d)
            except Exception as e:
                log_exc("sound.play_failed", e)
                return
            self.state.last_eaten_dot = d

    def apply_command(self, cmd: dict) -> bool:
        op = cmd["op"]
        if op == "ping":
            return True
        if op == "shutdown":
            log("cmd.shutdown")
            return False
        if op == "quit":
            return True
        if op == "expr":
            old = self.state.expr
            self.state.expr = cmd["mode"]
            if cmd["mode"] != old and cmd["mode"] in ("happy", "sad", "thinking"):
                self.state.particles += particles.spawn_for(
                    cmd["mode"],
                    self.state.pos_x, self.state.pos_y,
                    CLAUDE_AVATAR_SIZE, CLAUDE_AVATAR_SIZE)
        elif op == "pos":
            self.state.pos_x = max(0, min(LOGICAL_W - CLAUDE_AVATAR_SIZE, cmd["x"]))
            self.state.pos_y = max(0, min(LOGICAL_H - CLAUDE_AVATAR_SIZE, cmd["y"]))
        elif op == "show":
            self.state.visible = True
        elif op == "hide":
            self.state.visible = False
        elif op == "loading":
            new_pct = max(0.0, min(1.0, cmd["pct"]))
            old_pct = self.state.loading_pct
            self.state.loading_pct = new_pct
            self.state.loading_visible = True
            self._maybe_play_pellets(old_pct, new_pct)
        elif op == "loading_hide":
            self.state.loading_visible = False
            self.state.last_eaten_dot = -1
        elif op == "mute":
            self.state.muted = True
        elif op == "unmute":
            self.state.muted = False
        elif op == "say":
            self.state.bubble_text = cmd["message"]
            duration_s = cmd.get("duration", 5.0)
            self.state.bubble_expires = self.frame + int(duration_s * FPS)
        elif op == "shush":
            self.state.bubble_text = ""
        elif op == "celebrate":
            self.state.particles += particles.spawn_for(
                "celebrate",
                self.state.pos_x, self.state.pos_y,
                CLAUDE_AVATAR_SIZE, CLAUDE_AVATAR_SIZE)
        elif op == "snap":
            path = cmd.get("path") or "snapshot_remote.png"
            if not Path(path).is_absolute():
                path = str(Path(__file__).parent / path)
            self.state.pending_snap = path
        # Deprecated ghost-related commands are silently ignored.
        return True

    def render_state(self):
        """Render gradient + stars + avatar + particles + bubble + loading bar."""
        self.canvas.blit(self.bg_surface, (0, 0))
        self._update_stars()
        self._draw_stars()
        self._maybe_spawn_meteor()
        self._update_meteors()
        self._draw_meteors()
        if self.state.visible:
            lx, ly = self._look_toward_cursor()
            surf = render_claude_avatar(self.state.expr, CLAUDE_AVATAR_SIZE,
                                          blink=self._is_blink_frame(),
                                          look_x=lx, look_y=ly)
            y = self.state.pos_y + self._breathe_offset()
            self.canvas.blit(surf, (self.state.pos_x, y))
        if self.state.loading_visible:
            bar = loading_bar.render(self.state.loading_w, self.state.loading_h,
                                       self.state.loading_pct, self.frame)
            self.canvas.blit(bar, (self.state.loading_x, self.state.loading_y))
        self.state.particles = particles.step(self.state.particles)
        particles.draw(self.canvas, self.state.particles)
        self._draw_bubble()

    def run(self, mode: str = "live", auto_snapshot: bool = False):
        log("run.start", mode=mode, auto_snapshot=auto_snapshot)
        running = True
        snapshot_taken = False
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = pygame.mouse.get_pos()
                    ax = self.state.pos_x * SCALE
                    ay = self.state.pos_y * SCALE
                    asz = CLAUDE_AVATAR_SIZE * SCALE
                    on_avatar = (ax <= mx <= ax + asz and ay <= my <= ay + asz
                                 and self.state.visible)
                    if on_avatar:
                        self._on_avatar_click()
                    else:
                        self._dragging = True
                        self._drag_offset = (mx, my)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self._dragging = False
                elif event.type == pygame.MOUSEMOTION and self._dragging:
                    if sys.platform == "win32":
                        point = ctypes.wintypes.POINT()
                        ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
                        new_x = point.x - self._drag_offset[0]
                        new_y = point.y - self._drag_offset[1]
                        self._move_window(new_x, new_y)

            if self.server is not None:
                while True:
                    try:
                        cmd = self.server.queue.get_nowait()
                    except _queue.Empty:
                        break
                    if not self.apply_command(cmd):
                        running = False
                        break

            self.render_state()

            scaled = pygame.transform.scale(self.canvas, (WIN_W, WIN_H))
            self.screen.blit(scaled, (0, 0))
            pygame.display.flip()
            self.frame += 1

            if self.state.pending_snap:
                pygame.image.save(self.screen, self.state.pending_snap)
                log("snap.saved", path=self.state.pending_snap, frame=self.frame)
                self.state.pending_snap = None

            if auto_snapshot and not snapshot_taken and self.frame == 30:
                out = Path(__file__).parent / f"snapshot_{mode}.png"
                pygame.image.save(self.screen, str(out))
                log("snapshot.saved", path=str(out), frame=self.frame)
                snapshot_taken = True
                running = False

            self.clock.tick(FPS)
        log("run.end", frames=self.frame)
        if self.server:
            self.server.stop()
        pygame.quit()


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mode = args[0] if args else "live"
    auto_snap = "--snapshot" in sys.argv
    no_server = "--no-server" in sys.argv
    try:
        Arcade(with_server=not no_server).run(mode, auto_snapshot=auto_snap)
    except BaseException as e:
        log_exc("run.crashed", e)
        raise
