"""Chiptune-style sound synthesis for Claude Arcade.

Generates short square-wave blips on the fly via numpy and wraps them as
pygame.mixer.Sound. Cached by parameter set. Mixer is initialized lazily.
"""

from __future__ import annotations
import numpy as np
import pygame


SAMPLE_RATE = 22050
_INITIALIZED = False
_CACHE: dict[tuple[float, float, float, str], pygame.mixer.Sound] = {}


def _ensure_mixer():
    global _INITIALIZED
    if _INITIALIZED:
        return
    if pygame.mixer.get_init():
        # pygame.init() already brought it up — re-init to our preferred params
        pygame.mixer.quit()
    pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1, buffer=256)
    _INITIALIZED = True


def make_blip(freq_hz: float = 700.0, duration_ms: float = 60.0,
               volume: float = 0.5, wave: str = "square") -> pygame.mixer.Sound:
    """Build (and cache) a short tone. wave: 'square' | 'triangle' | 'sine'."""
    _ensure_mixer()
    key = (freq_hz, duration_ms, volume, wave)
    if key in _CACHE:
        return _CACHE[key]

    n = int(SAMPLE_RATE * duration_ms / 1000.0)
    t = np.arange(n) / SAMPLE_RATE
    if wave == "square":
        sig = np.sign(np.sin(2 * np.pi * freq_hz * t))
    elif wave == "triangle":
        sig = 2 * np.abs(2 * (t * freq_hz - np.floor(t * freq_hz + 0.5))) - 1
    else:  # sine
        sig = np.sin(2 * np.pi * freq_hz * t)

    # Quick ADSR envelope to avoid clicks on short blips
    env = np.ones(n)
    attack = max(1, int(0.01 * SAMPLE_RATE))
    release = max(1, int(0.04 * SAMPLE_RATE))
    if attack < n:
        env[:attack] = np.linspace(0, 1, attack)
    if release < n:
        env[-release:] *= np.linspace(1, 0, release)
    sig = sig * env * volume

    pcm = (sig * 32767).astype(np.int16)
    snd = pygame.mixer.Sound(buffer=pcm.tobytes())
    _CACHE[key] = snd
    return snd


# Pre-defined sounds — alternating pitches give the iconic "chomp chomp" feel
PELLET_HI = lambda: make_blip(880, 50, volume=0.35)
PELLET_LO = lambda: make_blip(660, 50, volume=0.35)


def play_pellet(alternate: int = 0):
    """Play one chomp blip; alternate (0/1) chooses high vs low pitch."""
    snd = PELLET_HI() if alternate % 2 == 0 else PELLET_LO()
    snd.play()


def play_blip(freq: float, ms: float = 60, volume: float = 0.4,
              wave: str = "square"):
    make_blip(freq, ms, volume, wave).play()
