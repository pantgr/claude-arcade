"""Claude's own avatar — procedurally drawn with pygame.

No more Pac-Man palette/resolution limits — full RGBA freedom.
Soft rounded form with expressive eyes and a mouth that morphs by mood.
Color story: warm coral body (Anthropic-ish), deep navy eyes with bright
spark, dark outline. Subtle gradient + highlight for depth.
"""

from __future__ import annotations
import math
import pygame


# Default render size in LOGICAL pixels (then upscaled with the rest of the
# canvas). Pick a size that has presence without dominating the 224x288 screen.
DEFAULT_SIZE = 56

# Color palette (sRGB)
C_BODY_HI    = (245, 175, 130)   # body highlight (top)
C_BODY       = (228, 138,  85)   # body main coral
C_BODY_LO    = (178,  92,  48)   # body shadow (bottom)
C_OUTLINE    = ( 38,  20,  10)   # near-black warm outline
C_EYE_WHITE  = (250, 248, 240)
C_EYE_IRIS   = ( 38,  72, 124)
C_EYE_PUPIL  = ( 12,  16,  28)
C_EYE_SPARK  = (255, 255, 240)
C_MOUTH_DARK = ( 80,  35,  20)
C_MOUTH_HI   = (160,  60,  40)
C_BLUSH      = (240, 130, 130)

_CACHE: dict[tuple[str, int], pygame.Surface] = {}


def _draw_body(surf: pygame.Surface, size: int):
    """Soft rounded square body with a vertical gradient highlight + outline."""
    pad = max(2, size // 18)
    body_rect = pygame.Rect(pad, pad, size - 2 * pad, size - 2 * pad)
    radius = body_rect.width // 4

    # Outline ring (drawn slightly larger then body on top)
    out_rect = body_rect.inflate(2, 2)
    pygame.draw.rect(surf, C_OUTLINE, out_rect, border_radius=radius + 1)

    # Body fill
    pygame.draw.rect(surf, C_BODY, body_rect, border_radius=radius)

    # Vertical gradient: blend HI on top, LO on bottom by horizontal scanlines
    h = body_rect.height
    for y in range(h):
        t = y / max(1, h - 1)
        if t < 0.5:
            s = t / 0.5
            r = int(C_BODY_HI[0] * (1 - s) + C_BODY[0] * s)
            g = int(C_BODY_HI[1] * (1 - s) + C_BODY[1] * s)
            b = int(C_BODY_HI[2] * (1 - s) + C_BODY[2] * s)
        else:
            s = (t - 0.5) / 0.5
            r = int(C_BODY[0] * (1 - s) + C_BODY_LO[0] * s)
            g = int(C_BODY[1] * (1 - s) + C_BODY_LO[1] * s)
            b = int(C_BODY[2] * (1 - s) + C_BODY_LO[2] * s)
        # Only draw inside the rounded rect by using a temp mask
        line = pygame.Surface((body_rect.width, 1), pygame.SRCALPHA)
        line.fill((r, g, b, 255))
        # clip via the body rect's rounded shape: we skip pixels outside the
        # rounded corners by computing the corner inset for this row
        corner_inset = 0
        edge_dist_top = y
        edge_dist_bot = h - 1 - y
        edge_dist = min(edge_dist_top, edge_dist_bot)
        if edge_dist < radius:
            # corner cut: x must be at least (radius - sqrt(r^2 - (r-edge_dist)^2))
            dy = radius - edge_dist
            corner_inset = int(round(radius - math.sqrt(max(0, radius * radius - dy * dy))))
        if corner_inset > 0:
            line = line.subsurface((corner_inset, 0,
                                     body_rect.width - 2 * corner_inset, 1)).copy()
            surf.blit(line, (body_rect.x + corner_inset, body_rect.y + y))
        else:
            surf.blit(line, (body_rect.x, body_rect.y + y))

    # Re-stroke the outline (gradient overwrote it slightly)
    pygame.draw.rect(surf, C_OUTLINE, body_rect, width=max(1, size // 36),
                      border_radius=radius)


def _draw_eye(surf: pygame.Surface, cx: int, cy: int, size: int,
              look_dx: float = 0.0, look_dy: float = 0.0,
              closed: bool = False, raised: bool = False):
    """Draw one eye centered at (cx, cy)."""
    r_white = max(3, size // 9)
    if closed:
        # Closed eye: a smiling arc
        rect = pygame.Rect(cx - r_white, cy - r_white // 2,
                            2 * r_white, r_white)
        pygame.draw.arc(surf, C_OUTLINE, rect, math.pi, 2 * math.pi,
                         max(2, size // 36))
        return
    # White
    pygame.draw.circle(surf, C_EYE_WHITE, (cx, cy), r_white)
    pygame.draw.circle(surf, C_OUTLINE, (cx, cy), r_white, max(1, size // 56))
    # Iris (offset by look)
    r_iris = int(r_white * 0.7)
    ix = cx + int(look_dx * (r_white - r_iris))
    iy = cy + int(look_dy * (r_white - r_iris))
    pygame.draw.circle(surf, C_EYE_IRIS, (ix, iy), r_iris)
    # Pupil
    r_pup = max(2, int(r_iris * 0.55))
    pygame.draw.circle(surf, C_EYE_PUPIL, (ix, iy), r_pup)
    # Sparkle (top-left of iris)
    sp = max(1, r_pup // 2)
    pygame.draw.circle(surf, C_EYE_SPARK,
                        (ix - r_iris // 3, iy - r_iris // 3), sp)
    # Raised brow indicator
    if raised:
        bx0 = cx - r_white - 1
        bx1 = cx + r_white + 1
        by  = cy - r_white - max(2, size // 18)
        pygame.draw.line(surf, C_OUTLINE, (bx0, by + 2), (bx1, by - 1),
                          max(2, size // 36))


def _draw_mouth(surf: pygame.Surface, cx: int, cy: int, size: int, expr: str):
    w = size // 3
    h = size // 6
    if expr == "happy":
        rect = pygame.Rect(cx - w, cy - h // 2, 2 * w, h * 2)
        pygame.draw.arc(surf, C_OUTLINE, rect, math.pi, 2 * math.pi,
                         max(2, size // 28))
        # tongue hint
        pygame.draw.arc(surf, C_MOUTH_HI, rect.inflate(-4, -4),
                         math.pi + 0.3, 2 * math.pi - 0.3,
                         max(1, size // 36))
    elif expr == "sad":
        rect = pygame.Rect(cx - w, cy - h, 2 * w, h * 2)
        pygame.draw.arc(surf, C_OUTLINE, rect, 0, math.pi, max(2, size // 28))
    elif expr == "talk":
        # Open oval mouth
        rect = pygame.Rect(cx - w // 2, cy - h, w, h * 2)
        pygame.draw.ellipse(surf, C_MOUTH_DARK, rect)
        pygame.draw.ellipse(surf, C_OUTLINE, rect, max(1, size // 36))
        # tongue
        tongue = rect.inflate(-rect.width // 3, -rect.height // 2)
        tongue.bottom = rect.bottom - 1
        pygame.draw.ellipse(surf, C_MOUTH_HI, tongue)
    elif expr == "thinking":
        # Tiny offset dot mouth
        pygame.draw.circle(surf, C_OUTLINE, (cx + w // 2, cy), max(2, size // 28))
    elif expr == "sleep":
        # Z marks above to show sleeping
        z_x = cx + w
        z_y = cy - size // 3
        s = max(4, size // 12)
        pts = [(z_x, z_y), (z_x + s, z_y), (z_x, z_y + s), (z_x + s, z_y + s)]
        pygame.draw.lines(surf, C_OUTLINE, False, pts, max(2, size // 36))
        # And a calm closed-mouth line
        pygame.draw.line(surf, C_OUTLINE,
                          (cx - w // 2, cy), (cx + w // 2, cy),
                          max(2, size // 36))
    elif expr == "wink":
        # Asymmetric grin shifted slightly toward the open eye side (right)
        rect = pygame.Rect(cx - w + size // 30, cy - h // 2, 2 * w, int(h * 1.6))
        pygame.draw.arc(surf, C_OUTLINE, rect, math.pi + 0.15, 2 * math.pi - 0.05,
                         max(2, size // 28))
    else:  # idle / unknown -> small smile
        rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        pygame.draw.arc(surf, C_OUTLINE, rect, math.pi + 0.4, 2 * math.pi - 0.4,
                         max(2, size // 32))


def _draw_blush(surf: pygame.Surface, size: int, alpha: int = 80):
    """Optional cheek blush for happy."""
    blush = pygame.Surface((size, size), pygame.SRCALPHA)
    r = size // 12
    for cx in (size // 4 + 2, size - size // 4 - 2):
        pygame.draw.circle(blush, (*C_BLUSH, alpha), (cx, int(size * 0.62)), r)
    surf.blit(blush, (0, 0))


def render_avatar(expression: str = "idle", size: int = DEFAULT_SIZE,
                   blink: bool = False, look_x: float = 0.0,
                   look_y: float = 0.0) -> pygame.Surface:
    """Build (and cache) a pygame Surface for the given expression.

    blink=True closes the eyes briefly.
    look_x, look_y in -1..1 nudge the pupils toward that direction (only
    applied for expressions that don't already have a baked look).

    Returns an SRCALPHA surface of (size, size).
    """
    # Quantize look to 5 steps per axis (-2..2) to keep the cache small.
    qx = max(-2, min(2, int(round(look_x * 2))))
    qy = max(-2, min(2, int(round(look_y * 2))))
    key = (expression, size, blink, qx, qy)
    if key in _CACHE:
        return _CACHE[key]
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    _draw_body(surf, size)

    eye_y = int(size * 0.40)
    eye_left_x = int(size * 0.32)
    eye_right_x = int(size * 0.68)
    mouth_cx = size // 2
    mouth_cy = int(size * 0.68)

    closed = blink or expression == "sleep"
    # Continuous look for free-look expressions
    looking = expression in ("idle", "happy", "talk")
    look_dx = qx / 2 if looking else 0.0
    look_dy = qy / 2 if looking else 0.0

    if closed:
        _draw_eye(surf, eye_left_x, eye_y, size, closed=True)
        _draw_eye(surf, eye_right_x, eye_y, size, closed=True)
    elif expression == "wink":
        # Left eye closed (knowing wink), right eye open and meeting yours
        _draw_eye(surf, eye_left_x, eye_y, size, closed=True)
        _draw_eye(surf, eye_right_x, eye_y, size, look_dx=0.0, look_dy=0.0)
    elif expression == "thinking":
        _draw_eye(surf, eye_left_x, eye_y, size, look_dx=0.5, look_dy=-0.3,
                   raised=True)
        _draw_eye(surf, eye_right_x, eye_y, size, look_dx=0.5, look_dy=-0.3)
    elif expression == "sad":
        _draw_eye(surf, eye_left_x, eye_y, size, look_dy=0.3)
        _draw_eye(surf, eye_right_x, eye_y, size, look_dy=0.3)
    else:
        _draw_eye(surf, eye_left_x, eye_y, size, look_dx=look_dx, look_dy=look_dy)
        _draw_eye(surf, eye_right_x, eye_y, size, look_dx=look_dx, look_dy=look_dy)

    if expression == "happy":
        _draw_blush(surf, size)
    _draw_mouth(surf, mouth_cx, mouth_cy, size, expression)

    _CACHE[key] = surf
    return surf


if __name__ == "__main__":
    # Standalone test: render all expressions side-by-side
    pygame.init()
    expressions = ["idle", "happy", "sad", "talk", "thinking", "sleep"]
    pad = 12
    cell = 96
    W = pad + len(expressions) * (cell + pad)
    H = pad + cell + pad + 24
    screen = pygame.display.set_mode((W, H))
    screen.fill((24, 22, 30))
    font = pygame.font.SysFont("consolas", 14, bold=True)
    for i, e in enumerate(expressions):
        surf = render_avatar(e, cell)
        screen.blit(surf, (pad + i * (cell + pad), pad))
        label = font.render(e, True, (220, 220, 220))
        screen.blit(label, (pad + i * (cell + pad), pad + cell + 4))
    pygame.display.flip()
    pygame.image.save(screen, "snapshot_avatar_designs.png")
    print("Saved snapshot_avatar_designs.png")
    pygame.quit()
