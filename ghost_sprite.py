"""Procedurally drawn Pac-Man-style ghosts in pygame.

Iconic shape: rounded dome + body + wavy bottom + two eyes with pupils.
The pupils look toward the direction of travel.
"""

from __future__ import annotations
import pygame


# Classic ghost colors (Blinky, Pinky, Inky, Clyde) + neutral white sclerae
COLORS = {
    "blinky": (255,  68,  60),   # red
    "pinky":  (255, 184, 211),   # pink
    "inky":   (110, 220, 240),   # cyan
    "clyde":  (255, 184,  82),   # orange
    "frightened": (40,  60, 220),
}
EYE_WHITE = (252, 252, 252)
EYE_PUPIL = ( 32,  32, 200)   # blue (classic Pac-Man pupil color)
OUTLINE   = ( 18,  10,  10)


_CACHE: dict[tuple[str, int, str, int], pygame.Surface] = {}


def render(color: str = "blinky", size: int = 18, facing: str = "left",
            anim_frame: int = 0) -> pygame.Surface:
    """Build (and cache) a ghost surface.

    color: 'blinky' | 'pinky' | 'inky' | 'clyde' | 'frightened'
    facing: 'left' | 'right' | 'up' | 'down' (controls pupil direction)
    anim_frame: 0 or 1 (toggles bottom waddle)
    """
    key = (color, size, facing, anim_frame & 1)
    if key in _CACHE:
        return _CACHE[key]

    body_color = COLORS.get(color, COLORS["blinky"])
    surf = pygame.Surface((size, size), pygame.SRCALPHA)

    # Body: rounded dome (top half) + rectangle (middle) + wavy bottom
    # Dome
    dome_rect = pygame.Rect(1, 1, size - 2, size - 2)
    pygame.draw.ellipse(surf, body_color, dome_rect)
    # Cut bottom half of the ellipse and replace with a rectangle for the body
    body_top = size // 2
    pygame.draw.rect(surf, body_color, (1, body_top, size - 2, size - body_top - 2))

    # Wavy bottom: 3 humps. anim_frame toggles to "shift" the humps.
    bottom_y = size - 1
    wave_h = max(2, size // 8)
    n_humps = 3
    hump_w = (size - 2) // n_humps
    pts = [(1, bottom_y - wave_h)]
    for i in range(n_humps):
        x0 = 1 + i * hump_w
        x_mid = x0 + hump_w // 2
        x1 = x0 + hump_w
        if (i % 2 == anim_frame % 2):
            pts.append((x_mid, bottom_y))
            pts.append((x1, bottom_y - wave_h))
        else:
            pts.append((x_mid, bottom_y - wave_h * 2))
            pts.append((x1, bottom_y - wave_h))
    pts.append((size - 2, bottom_y))
    pts.append((1, bottom_y))
    # Mask: paint over the bottom strip with body shape
    bottom_strip = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.polygon(bottom_strip, body_color, pts)
    surf.blit(bottom_strip, (0, 0))

    # Eyes (two ovals)
    eye_r = max(2, size // 5)
    eye_y = int(size * 0.40)
    eye_lx = int(size * 0.30)
    eye_rx = int(size * 0.70)
    pygame.draw.circle(surf, EYE_WHITE, (eye_lx, eye_y), eye_r)
    pygame.draw.circle(surf, EYE_WHITE, (eye_rx, eye_y), eye_r)

    # Pupils — offset by facing direction
    px, py = 0, 0
    if facing == "left":  px = -1
    elif facing == "right": px = 1
    elif facing == "up":   py = -1
    elif facing == "down": py = 1
    pup_r = max(1, eye_r // 2)
    off = max(1, eye_r // 2)
    pygame.draw.circle(surf, EYE_PUPIL,
                       (eye_lx + px * off, eye_y + py * off), pup_r)
    pygame.draw.circle(surf, EYE_PUPIL,
                       (eye_rx + px * off, eye_y + py * off), pup_r)

    _CACHE[key] = surf
    return surf


COLOR_NAMES = ("blinky", "pinky", "inky", "clyde")


if __name__ == "__main__":
    pygame.init()
    cell = 64
    pad = 12
    W = pad + len(COLOR_NAMES) * (cell + pad) + pad
    H = pad + 2 * (cell + pad) + 30
    screen = pygame.display.set_mode((W, H))
    screen.fill((20, 20, 26))
    font = pygame.font.SysFont("consolas", 12, bold=True)
    for i, name in enumerate(COLOR_NAMES):
        x = pad + i * (cell + pad)
        screen.blit(render(name, cell, "left", 0), (x, pad))
        screen.blit(render(name, cell, "right", 1), (x, pad + cell + pad))
        screen.blit(font.render(name, True, (220, 220, 220)),
                     (x, pad + 2 * (cell + pad)))
    pygame.display.flip()
    pygame.image.save(screen, "snapshot_ghosts_design.png")
    print("Saved snapshot_ghosts_design.png")
    pygame.quit()
