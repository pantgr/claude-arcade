"""Dump all 256 tiles as a labeled grid (16x16) at large scale to identify letters."""
import pygame
import numpy as np
from rom_loader import ROMs, _apply_transform


def main():
    roms = ROMs()
    transform = "antitranspose"

    pygame.init()
    cell = 24
    cols = 16
    rows = 16
    label_h = 16
    W = cols * (cell + 2) + 30
    H = label_h + rows * (cell + label_h + 2) + 10
    screen = pygame.display.set_mode((W, H))
    screen.fill((20, 20, 20))

    font = pygame.font.SysFont("consolas", 11)

    # Header columns
    for c in range(cols):
        text = font.render(f"+{c:X}", True, (150, 150, 150))
        screen.blit(text, (30 + c * (cell + 2), 0))

    for r in range(rows):
        # Row label
        rl = font.render(f"{r:X}0", True, (150, 150, 150))
        screen.blit(rl, (4, label_h + r * (cell + label_h + 2) + cell // 2))
        for c in range(cols):
            tile_idx = r * 16 + c
            rgba = roms.colorize_tile(tile_idx, 0x09, transform=transform)
            surf = pygame.Surface((8, 8), pygame.SRCALPHA)
            arr = pygame.surfarray.pixels3d(surf)
            arr[:, :, :] = np.transpose(rgba[:, :, :3], (1, 0, 2))
            del arr
            alpha = pygame.surfarray.pixels_alpha(surf)
            alpha[:, :] = rgba[:, :, 3].T
            del alpha
            scaled = pygame.transform.scale(surf, (cell, cell))
            x = 30 + c * (cell + 2)
            y = label_h + r * (cell + label_h + 2)
            screen.blit(scaled, (x, y))
            # Index below
            idx_text = font.render(f"{tile_idx:02X}", True, (100, 100, 100))
            screen.blit(idx_text, (x, y + cell + 1))

    pygame.display.flip()
    pygame.image.save(screen, "snapshot_all_tiles.png")
    print(f"Saved snapshot_all_tiles.png ({W}x{H})")
    pygame.quit()


if __name__ == "__main__":
    main()
