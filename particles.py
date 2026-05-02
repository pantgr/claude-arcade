"""Mood-based particle effects.

Spawn floating particles when the avatar's expression changes:
  happy     -> golden sparkles drifting up
  sad       -> blue teardrops falling
  thinking  -> small gray dots rising (thought wisps)
  celebrate -> rainbow burst (used by 'sparkle' explicit command)
"""

from __future__ import annotations
import math
import random
from dataclasses import dataclass
import pygame


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int           # frames remaining
    life_max: int
    color: tuple[int, int, int]
    size: int
    kind: str           # 'sparkle' | 'tear' | 'wisp'


def spawn_for(mood: str, x: int, y: int, w: int, h: int) -> list[Particle]:
    """Build a fresh set of particles based on mood, positioned around the
    avatar's bounding box (x,y,w,h)."""
    out: list[Particle] = []
    if mood == "happy":
        for _ in range(8):
            out.append(Particle(
                x = x + random.uniform(0, w),
                y = y + h * 0.3 + random.uniform(0, h * 0.6),
                vx = random.uniform(-0.4, 0.4),
                vy = random.uniform(-0.9, -0.4),
                life = random.randint(40, 70),
                life_max = 70,
                color = random.choice([(255, 240, 120), (255, 200, 60),
                                         (255, 250, 220)]),
                size = random.choice([2, 2, 3]),
                kind = "sparkle",
            ))
    elif mood == "sad":
        for _ in range(5):
            out.append(Particle(
                x = x + w * 0.25 + random.uniform(0, w * 0.5),
                y = y + h * 0.55 + random.uniform(0, 4),
                vx = 0,
                vy = random.uniform(0.6, 1.0),
                life = random.randint(40, 60),
                life_max = 60,
                color = (120, 180, 255),
                size = 3,
                kind = "tear",
            ))
    elif mood == "thinking":
        for _ in range(4):
            out.append(Particle(
                x = x + w * 0.6 + random.uniform(-3, 3),
                y = y + h * 0.2 + random.uniform(-3, 3),
                vx = random.uniform(-0.05, 0.05),
                vy = random.uniform(-0.4, -0.2),
                life = random.randint(70, 110),
                life_max = 110,
                color = (200, 200, 210),
                size = random.choice([2, 3, 4]),
                kind = "wisp",
            ))
    elif mood == "celebrate":
        for _ in range(20):
            ang = random.uniform(0, 2 * math.pi)
            spd = random.uniform(0.6, 1.6)
            out.append(Particle(
                x = x + w / 2,
                y = y + h / 2,
                vx = math.cos(ang) * spd,
                vy = math.sin(ang) * spd,
                life = random.randint(40, 70),
                life_max = 70,
                color = random.choice([(255, 80, 80), (255, 220, 80),
                                         (80, 200, 255), (255, 120, 220)]),
                size = random.choice([2, 3]),
                kind = "sparkle",
            ))
    return out


def step(particles: list[Particle]) -> list[Particle]:
    """Advance one frame; returns surviving particles."""
    keep: list[Particle] = []
    for p in particles:
        p.x += p.vx
        p.y += p.vy
        if p.kind == "sparkle":
            p.vy += 0.02     # very slight gravity
        elif p.kind == "tear":
            p.vy += 0.05
        elif p.kind == "wisp":
            p.vx += random.uniform(-0.04, 0.04)
        p.life -= 1
        if p.life > 0:
            keep.append(p)
    return keep


def draw(surface: pygame.Surface, particles: list[Particle]):
    for p in particles:
        # Fade with remaining life
        alpha = int(255 * (p.life / p.life_max))
        col = (*p.color, max(0, min(255, alpha)))
        if p.kind == "sparkle":
            # 4-point star: cross of 2 small lines
            s = p.size
            tmp = pygame.Surface((s * 2 + 1, s * 2 + 1), pygame.SRCALPHA)
            pygame.draw.line(tmp, col, (s, 0), (s, s * 2), 1)
            pygame.draw.line(tmp, col, (0, s), (s * 2, s), 1)
            surface.blit(tmp, (int(p.x) - s, int(p.y) - s))
        elif p.kind == "tear":
            tmp = pygame.Surface((p.size * 2, p.size * 3), pygame.SRCALPHA)
            pygame.draw.ellipse(tmp, col, (0, 0, p.size * 2, p.size * 3))
            surface.blit(tmp, (int(p.x) - p.size, int(p.y) - p.size))
        else:  # wisp
            tmp = pygame.Surface((p.size * 2, p.size * 2), pygame.SRCALPHA)
            pygame.draw.circle(tmp, col, (p.size, p.size), p.size)
            surface.blit(tmp, (int(p.x) - p.size, int(p.y) - p.size))
