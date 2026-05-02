"""Pac-Man-eating-dots loading bar.

Renders a Pac-Man sprite that slides left-to-right based on progress (0..1),
eating a row of pellets as it goes. Mouth chomps via frame counter.
"""

from __future__ import annotations
import math
import pygame


C_PAC      = (255, 220,  40)
C_PAC_DARK = (200, 160,  10)
C_DOT      = (252, 232, 180)
C_DOT_DIM  = (130, 110,  60)


def _draw_pacman(surf: pygame.Surface, x: int, y: int, size: int, frame: int):
    """Pac-Man with chomping mouth at frame-driven angle. Faces right."""
    cx = x + size // 2
    cy = y + size // 2
    r = size // 2 - 1
    # Mouth angle 0..pi/4 (closed..open), driven by sin
    t = abs(math.sin(frame * 0.20))
    mouth = t * (math.pi / 4)
    # Body
    pygame.draw.circle(surf, C_PAC, (cx, cy), r)
    pygame.draw.circle(surf, C_PAC_DARK, (cx, cy), r, 1)
    # Eye
    eye_r = max(1, size // 10)
    pygame.draw.circle(surf, (20, 20, 20), (cx + 1, cy - r // 2), eye_r)
    # Mouth wedge — punch through with the surface's bg by drawing transparent
    if mouth > 0.02:
        p0 = (cx, cy)
        p1 = (cx + int(r * math.cos(-mouth)) + 1, cy + int(r * math.sin(-mouth)))
        p2 = (cx + int(r * math.cos( mouth)) + 1, cy + int(r * math.sin( mouth)))
        # Draw with alpha 0 (transparent) — works only on SRCALPHA surfaces
        pygame.draw.polygon(surf, (0, 0, 0, 0), [p0, p1, p2])


def render(width: int, height: int, progress: float, frame: int = 0) -> pygame.Surface:
    """Build an SRCALPHA surface (width, height) of the loading bar.
    progress: 0.0..1.0
    """
    progress = max(0.0, min(1.0, progress))
    surf = pygame.Surface((width, height), pygame.SRCALPHA)

    pac_size = height
    pac_x = int(progress * (width - pac_size))

    # Dots row: every `step` px, vertically centered
    step = max(6, height // 2)
    dot_r = max(1, height // 8)
    dot_y = height // 2
    margin = pac_size // 2
    # First dot just after the pacman's starting position
    first_dot = pac_size + step
    last_dot = width - margin
    for dx in range(first_dot, last_dot + 1, step):
        # If the dot has been "eaten" (passed by pacman center), draw dim/none
        if dx < pac_x + pac_size // 2 + 1:
            continue  # eaten
        pygame.draw.circle(surf, C_DOT, (dx, dot_y), dot_r)

    _draw_pacman(surf, pac_x, 0, pac_size, frame)
    return surf
