"""Comic-book speech bubble for the avatar.

Renders a rounded white box with outline + a tail pointing to the avatar.
Text uses the Pac-Man tile font (the caller passes a tile-rendering function).
"""

from __future__ import annotations
import math
import pygame


BUBBLE_FILL    = (252, 248, 240)
BUBBLE_OUTLINE = ( 32,  20,  18)
TEXT_PAD_X = 4   # px horizontal padding inside bubble
TEXT_PAD_Y = 4
LINE_HEIGHT_TILES = 1   # tiles are 8x8 already
MAX_CHARS_PER_LINE = 18  # wrap soft limit


def wrap_text(text: str, max_chars: int = MAX_CHARS_PER_LINE) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= max_chars:
            cur = (cur + " " + w) if cur else w
        else:
            if cur:
                lines.append(cur)
            # Word longer than max: hard split
            while len(w) > max_chars:
                lines.append(w[:max_chars])
                w = w[max_chars:]
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def measure(lines: list[str]) -> tuple[int, int]:
    longest = max(len(line) for line in lines)
    w_px = longest * 8 + TEXT_PAD_X * 2
    h_px = len(lines) * 8 + TEXT_PAD_Y * 2
    return w_px, h_px


def draw_bubble_frame(surface: pygame.Surface,
                       rect: pygame.Rect,
                       tail_target: tuple[int, int]):
    """Draw the bubble background + tail on the (already-blank) surface."""
    radius = 5
    pygame.draw.rect(surface, BUBBLE_FILL, rect, border_radius=radius)
    pygame.draw.rect(surface, BUBBLE_OUTLINE, rect, width=1, border_radius=radius)

    # Tail: triangle from a point on the bubble's nearest edge to the target.
    # Pick the closest edge midpoint of the rect to the target.
    tx, ty = tail_target
    cx = rect.centerx
    cy = rect.centery
    if abs(tx - cx) > abs(ty - cy):
        # Tail comes out left or right side
        if tx < cx:
            base = (rect.left, cy)
            offsets = ((0, -3), (0, 3))
        else:
            base = (rect.right, cy)
            offsets = ((0, -3), (0, 3))
    else:
        if ty < cy:
            base = (cx, rect.top)
            offsets = ((-3, 0), (3, 0))
        else:
            base = (cx, rect.bottom)
            offsets = ((-3, 0), (3, 0))
    p1 = (base[0] + offsets[0][0], base[1] + offsets[0][1])
    p2 = (base[0] + offsets[1][0], base[1] + offsets[1][1])
    pygame.draw.polygon(surface, BUBBLE_FILL, [p1, p2, tail_target])
    # Outline tail edges (skip the base segment so it merges with the bubble)
    pygame.draw.line(surface, BUBBLE_OUTLINE, p1, tail_target, 1)
    pygame.draw.line(surface, BUBBLE_OUTLINE, p2, tail_target, 1)


def position_bubble(avatar_rect: pygame.Rect, bubble_size: tuple[int, int],
                     canvas_size: tuple[int, int]) -> pygame.Rect:
    """Place the bubble above the avatar by default; if no room, try below."""
    bw, bh = bubble_size
    cw, ch = canvas_size
    # Prefer above-right (offset)
    bx = avatar_rect.centerx - bw // 2 + 8
    by = avatar_rect.top - bh - 6
    if by < 4:
        # Not enough room above -> place below
        by = avatar_rect.bottom + 6
    bx = max(2, min(cw - bw - 2, bx))
    by = max(2, min(ch - bh - 2, by))
    return pygame.Rect(bx, by, bw, bh)
