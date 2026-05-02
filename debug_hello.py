"""Render 'HELLO' with each transform to find which is readable."""
import pygame
import numpy as np
from rom_loader import ROMs


def main():
    roms = ROMs()
    transforms = ["none", "rot_cw", "rot_ccw", "rot180", "transpose", "antitranspose"]
    word = "HELLO PANTELI"

    pygame.init()
    cell = 32
    label_w = 130
    W = label_w + len(word) * (cell + 2) + 10
    H = len(transforms) * (cell + 8) + 20
    screen = pygame.display.set_mode((W, H))
    screen.fill((10, 10, 10))

    font = pygame.font.SysFont("consolas", 14, bold=True)

    for ri, t in enumerate(transforms):
        label = font.render(t, True, (255, 255, 100))
        y = 10 + ri * (cell + 8)
        screen.blit(label, (8, y + cell // 4))
        for ci, ch in enumerate(word):
            code = ord(ch)
            if code == 0x20:
                continue
            rgba = roms.colorize_tile(code, 0x0F, transform=t)
            surf = pygame.Surface((8, 8), pygame.SRCALPHA)
            arr = pygame.surfarray.pixels3d(surf)
            arr[:, :, :] = np.transpose(rgba[:, :, :3], (1, 0, 2))
            del arr
            alpha = pygame.surfarray.pixels_alpha(surf)
            alpha[:, :] = rgba[:, :, 3].T
            del alpha
            scaled = pygame.transform.scale(surf, (cell, cell))
            screen.blit(scaled, (label_w + ci * (cell + 2), y))

    pygame.display.flip()
    pygame.image.save(screen, "snapshot_hello.png")
    print("Saved snapshot_hello.png")
    pygame.quit()


if __name__ == "__main__":
    main()
