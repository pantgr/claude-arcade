"""Show all 6 transform variants of a small tile range side-by-side.
Picks tiles 0x40-0x5F (likely text/digits) and renders each transform.
"""
import pygame
import numpy as np
from rom_loader import ROMs, _apply_transform


def main():
    roms = ROMs()
    transforms = ["none", "rot_cw", "rot_ccw", "rot180", "transpose", "antitranspose"]
    tile_range = range(0x40, 0x60)  # 32 tiles, focus on letters region

    pygame.init()
    cell = 32  # display size per tile (8x8 scaled 4x)
    cols = len(tile_range)
    rows = len(transforms)
    label_w = 110
    W = label_w + cols * (cell + 2) + 10
    H = 30 + rows * (cell + 4) + 10
    screen = pygame.display.set_mode((W, H))
    screen.fill((30, 30, 30))

    font = pygame.font.SysFont("consolas", 12)

    # Header: tile indices
    for ci, t in enumerate(tile_range):
        text = font.render(f"{t:02X}", True, (180, 180, 180))
        screen.blit(text, (label_w + ci * (cell + 2), 8))

    for ri, transform in enumerate(transforms):
        label = font.render(transform, True, (200, 200, 80))
        screen.blit(label, (8, 30 + ri * (cell + 4)))
        for ci, tile_idx in enumerate(tile_range):
            rgba = roms.colorize_tile(tile_idx, 0x09, transform=transform)
            # rgba (8,8,4) - blit scaled
            surf = pygame.Surface((8, 8), pygame.SRCALPHA)
            arr = pygame.surfarray.pixels3d(surf)
            arr[:, :, :] = np.transpose(rgba[:, :, :3], (1, 0, 2))
            del arr
            alpha = pygame.surfarray.pixels_alpha(surf)
            alpha[:, :] = rgba[:, :, 3].T
            del alpha
            scaled = pygame.transform.scale(surf, (cell, cell))
            screen.blit(scaled, (label_w + ci * (cell + 2), 30 + ri * (cell + 4)))

    pygame.display.flip()
    pygame.image.save(screen, "snapshot_transforms.png")
    print("Saved snapshot_transforms.png")
    pygame.quit()


if __name__ == "__main__":
    main()
