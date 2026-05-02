"""Render alphabet tiles 0x40-0x5F at LARGE scale to verify antitranspose orientation."""
import pygame
import numpy as np
from rom_loader import ROMs


def main():
    roms = ROMs()
    pygame.init()

    cell = 48  # very large
    cols = 16
    rows = 2  # 0x40-0x4F and 0x50-0x5F
    label_h = 16
    W = cols * (cell + 4) + 20
    H = rows * (cell + label_h * 2 + 4) + 30
    screen = pygame.display.set_mode((W, H))
    screen.fill((20, 20, 20))
    font = pygame.font.SysFont("consolas", 14, bold=True)

    # Top label
    title = font.render("rot_ccw (new decoder), expecting 0x41='A'..0x5A='Z'", True, (255, 255, 100))
    screen.blit(title, (10, 4))

    for r in range(rows):
        for c in range(cols):
            tile_idx = 0x40 + r * 16 + c
            rgba = roms.colorize_tile(tile_idx, 0x0F, transform="rot_ccw")
            surf = pygame.Surface((8, 8), pygame.SRCALPHA)
            arr = pygame.surfarray.pixels3d(surf)
            arr[:, :, :] = np.transpose(rgba[:, :, :3], (1, 0, 2))
            del arr
            alpha = pygame.surfarray.pixels_alpha(surf)
            alpha[:, :] = rgba[:, :, 3].T
            del alpha
            scaled = pygame.transform.scale(surf, (cell, cell))
            x = 10 + c * (cell + 4)
            y = 30 + r * (cell + label_h * 2 + 4)
            screen.blit(scaled, (x, y))
            # Label: hex code + expected ASCII char
            ch = chr(tile_idx) if 0x20 <= tile_idx < 0x7F else "?"
            label = font.render(f"{tile_idx:02X}={ch}", True, (200, 200, 200))
            screen.blit(label, (x, y + cell + 2))

    pygame.display.flip()
    pygame.image.save(screen, "snapshot_alphabet.png")
    print("Saved snapshot_alphabet.png")
    pygame.quit()


if __name__ == "__main__":
    main()
