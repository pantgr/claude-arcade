"""Decode Pac-Man hardware ROMs into numpy arrays.

Loads:
- 16-color RGB palette from 82s123.7f
- 256-entry palette lookup from 82s126.4a
- 256 char tiles (8x8) from 5e
- 64 sprites (16x16) from 5f
"""

from pathlib import Path
import numpy as np


ROM_DIR = Path(__file__).parent / "roms"


def load_color_prom(path: Path) -> np.ndarray:
    """82s123.7f: 32 bytes, first 16 are 16 distinct RGB colors.

    Bit layout per byte:
      bits 0-2 -> R via resistor weights (0x21, 0x47, 0x97)
      bits 3-5 -> G via same weights
      bits 6-7 -> B via weights (0x51, 0xae)
    Returns (16, 3) uint8 array.
    """
    data = path.read_bytes()
    rgb = np.zeros((16, 3), dtype=np.uint8)
    for i in range(16):
        b = data[i]
        r = 0x21 * ((b >> 0) & 1) + 0x47 * ((b >> 1) & 1) + 0x97 * ((b >> 2) & 1)
        g = 0x21 * ((b >> 3) & 1) + 0x47 * ((b >> 4) & 1) + 0x97 * ((b >> 5) & 1)
        bl = 0x51 * ((b >> 6) & 1) + 0xAE * ((b >> 7) & 1)
        rgb[i] = (r, g, bl)
    return rgb


def load_palette_prom(path: Path) -> np.ndarray:
    """82s126.4a: 256 bytes. Each low nibble = index into 16-color palette.
    Indexed by (color_attr << 2) | pixel_value.
    Returns (64, 4) uint8 of palette indices.
    """
    data = path.read_bytes()
    table = np.frombuffer(data, dtype=np.uint8) & 0x0F
    return table.reshape(64, 4)


def _decode_tile(rom: bytes, base: int) -> np.ndarray:
    """8x8 tile, 2 bitplanes. Pac-Man char ROM layout:
      Each row of pixels is split across two bytes (left half + right half).
      Bytes 0-7 hold pixels x=0..3 of rows 0..7 (one half).
      Bytes 8-15 hold pixels x=4..7 of rows 0..7 (other half).
      Within byte: low nibble = bp0 of 4 pixels, high nibble = bp1.
      Pixel value = bp1*2 + bp0.

    The natural decoded array is in (py, px) where (0,0) is one corner. To
    match the physically-displayed character orientation, the array still
    needs a 90 deg rotation (handled in colorize_tile via 'transform' param).
    """
    tile = np.zeros((8, 8), dtype=np.uint8)
    for py in range(8):
        for px in range(8):
            if px < 4:
                byte_idx = py
                bit = px
            else:
                byte_idx = 8 + py
                bit = px - 4
            byte = rom[base + byte_idx]
            bp0 = (byte >> bit) & 1
            bp1 = (byte >> (bit + 4)) & 1
            tile[py, px] = bp0 | (bp1 << 1)
    return tile


def load_tiles(path: Path) -> np.ndarray:
    """5e: 4096 bytes = 256 tiles x 16 bytes. Returns (256, 8, 8) uint8 with values 0-3."""
    data = path.read_bytes()
    tiles = np.zeros((256, 8, 8), dtype=np.uint8)
    for i in range(256):
        tiles[i] = _decode_tile(data, i * 16)
    return tiles


def _decode_sprite(rom: bytes, base: int) -> np.ndarray:
    """16x16 sprite, 2 bitplanes. MAME spritelayout: 64 bytes split into 8 blocks of 8 bytes:
       block 0 (0..7)   = row 0-7,  px 12-15
       block 1 (8..15)  = row 0-7,  px 0-3
       block 2 (16..23) = row 0-7,  px 4-7
       block 3 (24..31) = row 0-7,  px 8-11
       block 4 (32..39) = row 8-15, px 12-15
       block 5 (40..47) = row 8-15, px 0-3
       block 6 (48..55) = row 8-15, px 4-7
       block 7 (56..63) = row 8-15, px 8-11
    """
    sprite = np.zeros((16, 16), dtype=np.uint8)
    for py in range(16):
        block_y = 0 if py < 8 else 32
        byte_y = py if py < 8 else py - 8
        for px in range(16):
            if px < 4:
                block_x, bit = 8, px
            elif px < 8:
                block_x, bit = 16, px - 4
            elif px < 12:
                block_x, bit = 24, px - 8
            else:
                block_x, bit = 0, px - 12
            byte = rom[base + block_y + block_x + byte_y]
            bp0 = (byte >> bit) & 1
            bp1 = (byte >> (bit + 4)) & 1
            sprite[py, px] = bp0 | (bp1 << 1)
    return sprite


def load_sprites(path: Path) -> np.ndarray:
    """5f: 4096 bytes = 64 sprites x 64 bytes. Returns (64, 16, 16) uint8 values 0-3."""
    data = path.read_bytes()
    sprites = np.zeros((64, 16, 16), dtype=np.uint8)
    for i in range(64):
        sprites[i] = _decode_sprite(data, i * 64)
    return sprites


def _apply_transform(arr: np.ndarray, transform: str) -> np.ndarray:
    if transform == "none":
        return arr
    if transform == "rot_cw":
        return np.rot90(arr, -1)
    if transform == "rot_ccw":
        return np.rot90(arr, 1)
    if transform == "rot180":
        return np.rot90(arr, 2)
    if transform == "transpose":
        return arr.T
    if transform == "antitranspose":
        return np.flipud(np.fliplr(arr.T))
    raise ValueError(f"Unknown transform: {transform}")


class ROMs:
    """Bundle of decoded ROM data ready for rendering."""

    def __init__(self, rom_dir: Path = ROM_DIR):
        self.colors = load_color_prom(rom_dir / "82s123.7f")
        self.palette = load_palette_prom(rom_dir / "82s126.4a")
        self.tiles = load_tiles(rom_dir / "5e")
        self.sprites = load_sprites(rom_dir / "5f")

    def colorize_tile(self, tile_idx: int, color_attr: int,
                       transform: str = "none") -> np.ndarray:
        """transform: 'none' | 'rot_cw' | 'rot_ccw' | 'rot180' | 'transpose' | 'antitranspose'."""
        tile = _apply_transform(self.tiles[tile_idx], transform)
        return self._colorize(tile, color_attr)

    def colorize_sprite(self, sprite_idx: int, color_attr: int,
                         flip_x: bool = False, flip_y: bool = False,
                         transform: str = "none") -> np.ndarray:
        sprite = self.sprites[sprite_idx]
        if flip_x:
            sprite = sprite[:, ::-1]
        if flip_y:
            sprite = sprite[::-1, :]
        sprite = _apply_transform(sprite, transform)
        return self._colorize(sprite, color_attr)

    def _colorize(self, pixels: np.ndarray, color_attr: int) -> np.ndarray:
        """Map pixel values (0-3) -> RGBA via palette PROM + color PROM."""
        h, w = pixels.shape
        out = np.zeros((h, w, 4), dtype=np.uint8)
        pal_row = self.palette[color_attr & 0x3F]  # 4 palette indices
        for v in range(4):
            mask = pixels == v
            if not mask.any():
                continue
            color_idx = pal_row[v]
            rgb = self.colors[color_idx]
            out[mask, 0] = rgb[0]
            out[mask, 1] = rgb[1]
            out[mask, 2] = rgb[2]
            out[mask, 3] = 0 if v == 0 else 255  # value 0 transparent
        return out


if __name__ == "__main__":
    roms = ROMs()
    print(f"Colors loaded: {roms.colors.shape}")
    print(f"  red (idx 1):    {tuple(roms.colors[1])}")
    print(f"  green (idx 12): {tuple(roms.colors[12])}")
    print(f"  yellow (idx 9): {tuple(roms.colors[9])}")
    print(f"Palette table:    {roms.palette.shape}")
    print(f"Tiles loaded:     {roms.tiles.shape}")
    print(f"Sprites loaded:   {roms.sprites.shape}")
    # ASCII alignment smoke check: tile 0x48 should be 'H'
    print("\nTile $48 (should be 'H'):")
    for row in roms.tiles[0x48]:
        print("  " + "".join("##" if v else ".." for v in row))
