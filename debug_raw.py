"""Dump raw bytes of tile 0x48 (H) and try alternate bit orderings."""
from pathlib import Path
import numpy as np

rom = (Path(__file__).parent / "roms" / "5e").read_bytes()

# Tile 0x48 = bytes 0x480..0x48F
base = 0x48 * 16
print(f"Tile 0x48 raw bytes ({base:#x}..{base+15:#x}):")
for i in range(16):
    print(f"  byte[{i:2d}] = {rom[base+i]:#04x} = {rom[base+i]:08b}")

print("\n=== Decode v1: my current (bp0=bit 0..3, bp1=bit 4..7, px = bit) ===")
tile = np.zeros((8, 8), dtype=np.uint8)
for py in range(8):
    for px in range(8):
        if px < 4:
            byte_idx = 8 + py
            bit = px
        else:
            byte_idx = py
            bit = px - 4
        b = rom[base + byte_idx]
        bp0 = (b >> bit) & 1
        bp1 = (b >> (bit + 4)) & 1
        tile[py, px] = bp0 | (bp1 << 1)
for row in tile:
    print("  " + "".join("##" if v else ".." for v in row))

print("\n=== Decode v2: bit reversed (px=0 -> bit 3, px=3 -> bit 0) ===")
tile = np.zeros((8, 8), dtype=np.uint8)
for py in range(8):
    for px in range(8):
        if px < 4:
            byte_idx = 8 + py
            bit = 3 - px  # reversed
        else:
            byte_idx = py
            bit = 3 - (px - 4)  # reversed
        b = rom[base + byte_idx]
        bp0 = (b >> bit) & 1
        bp1 = (b >> (bit + 4)) & 1
        tile[py, px] = bp0 | (bp1 << 1)
for row in tile:
    print("  " + "".join("##" if v else ".." for v in row))

print("\n=== Decode v3: swap left/right halves (bytes 0-7 hold left, 8-15 hold right) ===")
tile = np.zeros((8, 8), dtype=np.uint8)
for py in range(8):
    for px in range(8):
        if px < 4:
            byte_idx = py  # was 8+py
            bit = px
        else:
            byte_idx = 8 + py  # was py
            bit = px - 4
        b = rom[base + byte_idx]
        bp0 = (b >> bit) & 1
        bp1 = (b >> (bit + 4)) & 1
        tile[py, px] = bp0 | (bp1 << 1)
for row in tile:
    print("  " + "".join("##" if v else ".." for v in row))

print("\n=== Decode v4: y reversed (y=0 -> byte 7, y=7 -> byte 0) ===")
tile = np.zeros((8, 8), dtype=np.uint8)
for py in range(8):
    for px in range(8):
        if px < 4:
            byte_idx = 8 + (7 - py)
            bit = px
        else:
            byte_idx = 7 - py
            bit = px - 4
        b = rom[base + byte_idx]
        bp0 = (b >> bit) & 1
        bp1 = (b >> (bit + 4)) & 1
        tile[py, px] = bp0 | (bp1 << 1)
for row in tile:
    print("  " + "".join("##" if v else ".." for v in row))
