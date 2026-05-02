"""Print tile 0x48 ('H') in ASCII for each transform to verify orientation."""
from rom_loader import ROMs, _apply_transform
import numpy as np

roms = ROMs()
transforms = ["none", "rot_cw", "rot_ccw", "rot180", "transpose", "antitranspose"]

for t in transforms:
    arr = _apply_transform(roms.tiles[0x48], t)
    print(f"\n=== {t} ===")
    for row in arr:
        print("  " + "".join("##" if v else ".." for v in row))

# Also try 0x41 'A'
print("\n\n--- Tile 0x41 ('A') ---")
for t in transforms:
    arr = _apply_transform(roms.tiles[0x41], t)
    print(f"\n=== {t} ===")
    for row in arr:
        print("  " + "".join("##" if v else ".." for v in row))
