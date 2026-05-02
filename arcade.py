"""Claude Arcade — Pac-Man styled AI avatar window.

Renders Ms. Pac-Man tiles/sprites onto a 224x288 logical canvas, scaled up.
Accepts TCP commands on localhost:7878 (see arcade_server.py).
"""

import ctypes
import ctypes.wintypes
import math
import queue as _queue
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pygame

from rom_loader import ROMs
from arcade_log import log, log_exc
from arcade_server import CommandServer
from claude_avatar import render_avatar as render_claude_avatar, DEFAULT_SIZE as CLAUDE_AVATAR_SIZE
import loading_bar
import sound
import ghost_sprite
import speech_bubble
import particles


# Pac-Man hardware native: 28 cols x 36 rows of 8x8 tiles = 224 x 288 px
LOGICAL_W = 224
LOGICAL_H = 288
SCALE = 3
WIN_W = LOGICAL_W * SCALE
WIN_H = LOGICAL_H * SCALE
FPS = 60

# Tile/sprite native orientation in ROM is 90 deg off display + mirrored.
# antitranspose = transpose + 180 rotate, aligns ASCII (0x41='A', 0x48='H').
TILE_TRANSFORM = "antitranspose"
SPRITE_TRANSFORM = "antitranspose"



@dataclass
class TextItem:
    tx: int
    ty: int
    color: int
    message: str


GHOST_NAMES = ghost_sprite.COLOR_NAMES   # ('blinky', 'pinky', 'inky', 'clyde')
GHOST_SIZE = 18


@dataclass
class Ghost:
    x: float
    y: int
    vx: float       # px per frame, signed
    color: str      # ghost name in GHOST_NAMES
    spawn_frame: int


@dataclass
class State:
    """Live state mutated by network commands, read by render loop."""
    expr: str = "idle"
    pos_x: int = (LOGICAL_W - CLAUDE_AVATAR_SIZE) // 2
    pos_y: int = (LOGICAL_H - CLAUDE_AVATAR_SIZE) // 2
    visible: bool = True
    bg_idx: int = 0
    texts: list[TextItem] = field(default_factory=list)
    # Loading bar: progress 0..1, off by default
    loading_pct: float = 0.0
    loading_visible: bool = False
    loading_x: int = 16
    loading_y: int = LOGICAL_H - 30
    loading_w: int = LOGICAL_W - 32
    loading_h: int = 14
    last_eaten_dot: int = -1   # index of the last dot we played a blip for
    muted: bool = False
    # Ambient ghosts drifting across the screen at random intervals
    ghosts: list[Ghost] = field(default_factory=list)
    next_ghost_frame: int = 0
    ghosts_enabled: bool = True
    # Speech bubble (auto-clears after expires_frame)
    bubble_text: str = ""
    bubble_expires: int = 0
    # Particles (mood-driven sparkles / tears / wisps)
    particles: list = field(default_factory=list)
    pending_snap: str | None = None  # filled by snap cmd, consumed after render


def make_tile_surface(rgba: np.ndarray) -> pygame.Surface:
    """Convert (H, W, 4) uint8 RGBA array to a pygame Surface with alpha."""
    h, w = rgba.shape[:2]
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    arr = pygame.surfarray.pixels3d(surf)
    arr[:, :, 0] = rgba[:, :, 0].T
    arr[:, :, 1] = rgba[:, :, 1].T
    arr[:, :, 2] = rgba[:, :, 2].T
    del arr
    alpha = pygame.surfarray.pixels_alpha(surf)
    alpha[:, :] = rgba[:, :, 3].T
    del alpha
    return surf


class Arcade:
    def __init__(self, with_server: bool = True, borderless: bool = True,
                  topmost: bool = True):
        log("init.start", logical=(LOGICAL_W, LOGICAL_H), scale=SCALE,
            tile_transform=TILE_TRANSFORM, sprite_transform=SPRITE_TRANSFORM,
            borderless=borderless, topmost=topmost)
        self.roms = ROMs()
        log("rom.loaded", colors=len(self.roms.colors), tiles=len(self.roms.tiles),
            sprites=len(self.roms.sprites))
        pygame.init()
        pygame.display.set_caption("Claude Arcade")
        flags = pygame.NOFRAME if borderless else 0
        self.screen = pygame.display.set_mode((WIN_W, WIN_H), flags)
        self._setup_windows_window(topmost=topmost)
        self._dragging = False
        self._drag_offset = (0, 0)
        # Logical canvas at 1:1, then we scale to window
        self.canvas = pygame.Surface((LOGICAL_W, LOGICAL_H))
        self.clock = pygame.time.Clock()
        self.frame = 0
        # Pre-render tiles/sprites we use frequently
        self._tile_cache: dict[tuple[int, int], pygame.Surface] = {}
        self._sprite_cache: dict[tuple[int, int, bool, bool], pygame.Surface] = {}
        # Live state + command server
        self.state = State()
        self.server = CommandServer() if with_server else None
        if self.server:
            self.server.start()
        # Wake-up greeting: happy + bubble + celebrate burst for first 3s
        self._boot_greet()
        log("init.done", win=(WIN_W, WIN_H), fps=FPS, server=bool(self.server))

    def _on_avatar_click(self):
        """User clicked directly on me — react with happiness + sparkle + blip."""
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

    def _try_eat_ghost(self, mx: int, my: int) -> bool:
        """If the click landed on a ghost, eat it: remove + burst + low blip."""
        for g in list(self.state.ghosts):
            gx = int(g.x) * SCALE
            gy = g.y * SCALE
            gsz = GHOST_SIZE * SCALE
            if gx <= mx <= gx + gsz and gy <= my <= gy + gsz:
                log("ghost.eaten", color=g.color, x=int(g.x), y=g.y)
                self.state.ghosts.remove(g)
                self.state.particles += particles.spawn_for(
                    "celebrate", int(g.x), g.y, GHOST_SIZE, GHOST_SIZE)
                if not self.state.muted:
                    try:
                        sound.play_blip(220, 130, volume=0.5, wave="square")
                    except Exception as e:
                        log_exc("sound.eat_failed", e)
                return True
        return False

    def _boot_greet(self):
        """Brief 'hello' moment when the window first appears."""
        GREET_FRAMES = 180  # 3 seconds at 60fps
        self.state.expr = "happy"
        self.state.bubble_text = "HI"
        self.state.bubble_expires = GREET_FRAMES
        self.state.particles += particles.spawn_for(
            "celebrate",
            self.state.pos_x, self.state.pos_y,
            CLAUDE_AVATAR_SIZE, CLAUDE_AVATAR_SIZE)

    def _setup_windows_window(self, topmost: bool):
        """Set always-on-top via Win32 SetWindowPos. No-op if not on Windows."""
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
        """Move the OS window to absolute screen coordinates."""
        if not getattr(self, "_hwnd", None):
            return
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        ctypes.windll.user32.SetWindowPos(
            self._hwnd, 0, int(screen_x), int(screen_y), 0, 0,
            SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE)

    def _get_window_pos(self) -> tuple[int, int]:
        if not getattr(self, "_hwnd", None):
            return (0, 0)
        rect = ctypes.wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(self._hwnd, ctypes.byref(rect))
        return (rect.left, rect.top)

    def get_tile(self, tile_idx: int, color_attr: int) -> pygame.Surface:
        key = (tile_idx, color_attr)
        if key in self._tile_cache:
            return self._tile_cache[key]
        rgba = self.roms.colorize_tile(tile_idx, color_attr, transform=TILE_TRANSFORM)
        surf = make_tile_surface(rgba)
        self._tile_cache[key] = surf
        return surf

    def get_sprite(self, sprite_idx: int, color_attr: int,
                   flip_x: bool = False, flip_y: bool = False) -> pygame.Surface:
        key = (sprite_idx, color_attr, flip_x, flip_y)
        if key in self._sprite_cache:
            return self._sprite_cache[key]
        rgba = self.roms.colorize_sprite(sprite_idx, color_attr, flip_x, flip_y,
                                          transform=SPRITE_TRANSFORM)
        surf = make_tile_surface(rgba)
        self._sprite_cache[key] = surf
        return surf

    def get_claude_avatar(self, expression: str, blink: bool = False,
                            look_x: float = 0.0, look_y: float = 0.0
                            ) -> pygame.Surface:
        """Procedurally drawn avatar (full RGBA, no Pac-Man palette)."""
        return render_claude_avatar(expression, CLAUDE_AVATAR_SIZE,
                                      blink=blink, look_x=look_x, look_y=look_y)

    def _look_toward_cursor(self) -> tuple[float, float]:
        """Compute (look_x, look_y) in -1..1.
        - If cursor is in-window: gaze toward it.
        - Otherwise: slow idle drift (sin wave) so the eyes wander.
        """
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
        # Idle drift: slow asymmetric sin/cos so motion isn't perfectly cyclic
        lx = math.sin(self.frame / 180.0) * 0.6
        ly = math.cos(self.frame / 230.0) * 0.3
        return lx, ly

    def _is_blink_frame(self) -> bool:
        """Blink ~150ms every ~3.5s. Skipped during talk/sleep modes."""
        if self.state.expr in ("talk", "sleep"):
            return False
        cycle = 210  # 3.5s at 60fps
        phase = self.frame % cycle
        return phase < 9  # ~150ms blink

    def _breathe_offset(self) -> int:
        """Subtle vertical bob (1-2 px) for life. Skipped during sleep."""
        if self.state.expr == "sleep":
            return 0
        return int(round(math.sin(self.frame / 36.0) * 1.6))

    def _maybe_spawn_ghost(self):
        """Auto-spawn an ambient ghost at random intervals (~25-55s)."""
        if not self.state.ghosts_enabled:
            return
        if self.frame < self.state.next_ghost_frame:
            return
        self._force_spawn_ghost()

    def _force_spawn_ghost(self):
        """Unconditional spawn (manual ghost command)."""
        from_left = random.random() < 0.5
        speed = random.uniform(0.45, 0.85) * (1 if from_left else -1)
        x = -GHOST_SIZE if from_left else LOGICAL_W
        avatar_top = self.state.pos_y
        avatar_bot = avatar_top + CLAUDE_AVATAR_SIZE
        bands = [(8, max(8, avatar_top - GHOST_SIZE - 4)),
                  (avatar_bot + 6, LOGICAL_H - GHOST_SIZE - 30)]
        bands = [b for b in bands if b[1] - b[0] > GHOST_SIZE]
        if not bands:
            self.state.next_ghost_frame = self.frame + 60 * 30
            return
        band = random.choice(bands)
        y = random.randint(band[0], band[1])
        color = random.choice(GHOST_NAMES)
        self.state.ghosts.append(Ghost(x=float(x), y=y, vx=speed, color=color,
                                        spawn_frame=self.frame))
        log("ghost.spawned", color=color, from_left=from_left, y=y)
        self.state.next_ghost_frame = self.frame + random.randint(60 * 25, 60 * 55)

    def _update_ghosts(self):
        keep = []
        for g in self.state.ghosts:
            g.x += g.vx
            if -20 <= g.x <= LOGICAL_W + 4:
                keep.append(g)
        self.state.ghosts = keep

    def _draw_ghosts(self):
        for g in self.state.ghosts:
            anim = ((self.frame - g.spawn_frame) // 10) & 1
            facing = "right" if g.vx > 0 else "left"
            surf = ghost_sprite.render(g.color, GHOST_SIZE, facing=facing,
                                         anim_frame=anim)
            self.canvas.blit(surf, (int(g.x), g.y))

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
        # Render text — Pac-Man tile font if ROMs present, else pygame default
        roms_present = self.roms.tiles[0x41].any()  # tile 'A' has any pixel set
        for li, line in enumerate(lines):
            tile_y_px = bubble_rect.y + speech_bubble.TEXT_PAD_Y + li * 8
            tile_x_px = bubble_rect.x + speech_bubble.TEXT_PAD_X
            if roms_present:
                for ci, ch in enumerate(line):
                    code = ord(ch)
                    if code == 0x20:
                        continue
                    if 0x20 <= code < 0x80:
                        surf = self.get_tile(code, 0x01)
                        self.canvas.blit(surf, (tile_x_px + ci * 8, tile_y_px))
            else:
                # Fallback: pygame's built-in monospace font (no ROMs available)
                if not hasattr(self, "_fallback_font"):
                    self._fallback_font = pygame.font.SysFont("consolas", 8, bold=True)
                surf = self._fallback_font.render(line, True, (180, 30, 30))
                self.canvas.blit(surf, (tile_x_px, tile_y_px))

    def _maybe_play_pellets(self, old_pct: float, new_pct: float):
        """Play one chomp blip per dot the pacman has just passed."""
        if self.state.muted or new_pct <= old_pct:
            return
        # Match loading_bar.render geometry: dots at x = pac_size + step*k
        # Approximate dot count = (loading_w - pac_size) / step, where step=h//2
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

    def draw_tile_grid(self, color_attr: int = 0x09):
        """Debug: dump all 256 tiles as a 16x16 grid covering the screen."""
        for i in range(256):
            tx = (i % 16)
            ty = (i // 16)
            surf = self.get_tile(i, color_attr)
            self.canvas.blit(surf, (tx * 8 + 32, ty * 8 + 32))

    def draw_sprite_grid(self, color_attr: int = 0x09):
        """Debug: dump all 64 sprites as 8x8 grid."""
        for i in range(64):
            sx = (i % 8)
            sy = (i // 8)
            surf = self.get_sprite(i, color_attr)
            self.canvas.blit(surf, (sx * 18 + 16, sy * 18 + 16))

    def draw_avatar_centered(self, sprite_idx: int, color_attr: int = 0x09):
        surf = self.get_sprite(sprite_idx, color_attr)
        x = (LOGICAL_W - 16) // 2
        y = (LOGICAL_H - 16) // 2
        self.canvas.blit(surf, (x, y))

    def draw_text(self, text: str, tile_x: int, tile_y: int, color_attr: int = 0x0F):
        """Draw ASCII text using char ROM tiles (tile index = ASCII code).
        Chars assumed in 0x20..0x7F. Unknown -> blank.
        """
        for i, ch in enumerate(text):
            code = ord(ch)
            if code == 0x20:
                continue  # space
            if 0x20 <= code < 0x80:
                surf = self.get_tile(code, color_attr)
                self.canvas.blit(surf, ((tile_x + i) * 8, tile_y * 8))

    def apply_command(self, cmd: dict) -> bool:
        """Apply one queued command to state. Return False to stop the app."""
        op = cmd["op"]
        if op == "ping":
            return True
        if op == "shutdown":
            log("cmd.shutdown")
            return False
        if op == "quit":
            return True  # connection-level only
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
        elif op == "bg":
            self.state.bg_idx = cmd["idx"] & 0x0F
        elif op == "text":
            self.state.texts.append(TextItem(
                tx=cmd["tx"], ty=cmd["ty"],
                color=cmd["color"], message=cmd["message"]))
        elif op == "text_clear":
            self.state.texts.clear()
        elif op == "loading":
            new_pct = max(0.0, min(1.0, cmd["pct"]))
            old_pct = self.state.loading_pct
            self.state.loading_pct = new_pct
            self.state.loading_visible = True
            # Trigger pellet blip(s) for any dot we crossed since last update
            self._maybe_play_pellets(old_pct, new_pct)
        elif op == "loading_hide":
            self.state.loading_visible = False
            self.state.last_eaten_dot = -1
        elif op == "mute":
            self.state.muted = True
        elif op == "unmute":
            self.state.muted = False
        elif op == "ghost":
            self._force_spawn_ghost()
        elif op == "ghosts_off":
            self.state.ghosts_enabled = False
            self.state.ghosts.clear()
        elif op == "ghosts_on":
            self.state.ghosts_enabled = True
            self.state.next_ghost_frame = self.frame + 60
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
            self.state.pending_snap = path  # save after this frame's render
        return True

    def render_state(self):
        """Render the live state (avatar + texts + loading bar + ghosts) onto canvas."""
        # Background
        bg_rgb = tuple(int(c) for c in self.roms.colors[self.state.bg_idx])
        self.canvas.fill(bg_rgb)
        # Ambient ghosts behind everything else
        self._maybe_spawn_ghost()
        self._update_ghosts()
        self._draw_ghosts()
        # Claude avatar (with blink + breathe + cursor-aware gaze)
        if self.state.visible:
            lx, ly = self._look_toward_cursor()
            surf = self.get_claude_avatar(self.state.expr,
                                            blink=self._is_blink_frame(),
                                            look_x=lx, look_y=ly)
            y = self.state.pos_y + self._breathe_offset()
            self.canvas.blit(surf, (self.state.pos_x, y))
        # Text items
        for t in self.state.texts:
            self.draw_text(t.message, t.tx, t.ty, t.color)
        # Loading bar
        if self.state.loading_visible:
            bar = loading_bar.render(self.state.loading_w, self.state.loading_h,
                                       self.state.loading_pct, self.frame)
            self.canvas.blit(bar, (self.state.loading_x, self.state.loading_y))
        # Particles (drawn above avatar so sparkles show on top)
        self.state.particles = particles.step(self.state.particles)
        particles.draw(self.canvas, self.state.particles)
        # Speech bubble
        self._draw_bubble()

    def run(self, mode: str = "live", auto_snapshot: bool = False):
        """mode: 'live' (default, network-driven) | 'tiles' | 'sprites' | 'demo'.
        auto_snapshot: if True, save snapshot at frame 30 then quit.
        """
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
                    if ax <= mx <= ax + asz and ay <= my <= ay + asz and self.state.visible:
                        self._on_avatar_click()
                    elif self._try_eat_ghost(mx, my):
                        pass  # ghost was eaten, no drag
                    else:
                        self._dragging = True
                        self._drag_offset = (mx, my)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self._dragging = False
                elif event.type == pygame.MOUSEMOTION and self._dragging:
                    # Cursor's screen coordinates - offset = new window pos
                    point = ctypes.wintypes.POINT()
                    if sys.platform == "win32":
                        ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
                        new_x = point.x - self._drag_offset[0]
                        new_y = point.y - self._drag_offset[1]
                        self._move_window(new_x, new_y)

            # Drain network commands
            if self.server is not None:
                while True:
                    try:
                        cmd = self.server.queue.get_nowait()
                    except _queue.Empty:
                        break
                    if not self.apply_command(cmd):
                        running = False
                        break

            if mode == "tiles":
                self.canvas.fill((0, 0, 0))
                self.draw_tile_grid(color_attr=0x09)
            elif mode == "sprites":
                self.canvas.fill((0, 0, 0))
                self.draw_sprite_grid(color_attr=0x09)
            elif mode == "demo":
                # Static demo mirroring the old smoke test
                self.canvas.fill((0, 0, 0))
                chomp_frame = 44 + ((self.frame // 8) % 4)
                self.draw_avatar_centered(chomp_frame, color_attr=0x09)
                self.draw_text("HELLO PANTELI", 7, 4, color_attr=0x0F)
                self.draw_text("CLAUDE ARCADE", 7, 28, color_attr=0x09)
            else:  # live: render from State
                self.render_state()

            scaled = pygame.transform.scale(self.canvas, (WIN_W, WIN_H))
            self.screen.blit(scaled, (0, 0))
            pygame.display.flip()
            self.frame += 1

            # Deferred snapshot: must run AFTER render so the snap captures the
            # frame including any state changes from the same command batch.
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
