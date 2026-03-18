"""
Generate AzroksRepublic.ico — a retro Win95-style pixel-art icon.

Palette (Win95 system colours + accent):
  SILVER  #c0c0c0   classic window face
  NAVY    #000080   title-bar blue
  GOLD    #ffcc00   highlight / shield trim
  GOLD_DK #b8860b   shadow side of gold
  WHITE   #ffffff
  GRAY    #808080   shadow
  RED     #800000   gem
  BLACK   #000000
"""

from PIL import Image, ImageDraw
import os, pathlib

# ── Palette ───────────────────────────────────────────────────────────────────
SILVER  = (192, 192, 192)
NAVY    = (  0,   0, 128)
GOLD    = (255, 204,   0)
GOLD_DK = (184, 134,  11)
WHITE   = (255, 255, 255)
GRAY    = (128, 128, 128)
RED     = (128,   0,   0)
BLACK   = (  0,   0,   0)
TRANS   = (  0,   0,   0,   0)   # fully transparent

# ── 32×32 master design (pixel map) ──────────────────────────────────────────
# Each char maps to a colour.  Layout is a heraldic shield with a central dagger.
#
# Legend:
#   .  transparent
#   S  silver       G  gold         g  dark-gold
#   N  navy         W  white        R  red
#   K  black        =  gray

LEGEND = {
    '.': TRANS,
    'S': SILVER,
    'G': GOLD,
    'g': GOLD_DK,
    'N': NAVY,
    'W': WHITE,
    'R': RED,
    'K': BLACK,
    '=': GRAY,
}

# 32-row × 32-col pixel map — drawn by hand for that authentic pixel-art feel
PIXELS_32 = [
    # 0         1         2         3
    # 0123456789012345678901234567890 1
    "................................",  # 00
    "................................",  # 01
    "..GGGGGGGGGGGGGGGGGGGGGGGGGG....",  # 02
    "..GNNNNNNNNNNNNNNNNNNNNNNNgG...",  # 03
    "..GNNNNNNNNNNNNNNNNNNNNNNNNgG..",  # 04  ← left-side shadow starts
    "..GNNNNNGGGGNNNNNGGGGNNNNNNgG..",  # 05  windows in shield
    "..GNNNNNGNNGNNNNGNNGNNNNNNNgG..",  # 06
    "..GNNNNNGGGGNNNNGGGGNNNNNNNgG..",  # 07
    "..GNNNNNNNNNNNNNNNNNNNNNNNNgG..",  # 08
    "..GNNNNNNNNNWWNNNNNNNNNNNNNgG..",  # 09  dagger blade top
    "..GNNNNNNNNWRWNNNNNNNNNNNNNgG..",  # 10  gem at pommel
    "..GNNNNNNNNNWWNNNNNNNNNNNNNgG..",  # 11
    "..GNNNNNNNNNWNNNNNNNNNNNNNNgG..",  # 12  blade
    "..GNNNNNNNNNWNNNNNNNNNNNNNNgG..",  # 13
    "..GNNNNNNNNNWNNNNNNNNNNNNNNgG..",  # 14
    "..GNNNNNNNNNWNNNNNNNNNNNNNNgG..",  # 15
    "..GNNNNNNNNNWNNNNNNNNNNNNNNgG..",  # 16
    "..GNNNNNWWWWWWWWWNNNNNNNNNNgG..",  # 17  cross-guard
    "..GNNNNNNNNNWNNNNNNNNNNNNNNgG..",  # 18
    "..GNNNNNNNNNWNNNNNNNNNNNNNNgG..",  # 19  handle
    "..GNNNNNNNNNGNNNNNNNNNNNNNNgG..",  # 20  gold grip wrap
    "..GNNNNNNNNNWNNNNNNNNNNNNNNgG..",  # 21
    "..GNNNNNNNNNWNNNNNNNNNNNNNNgG..",  # 22
    "..GNNNNNNNNNGNNNNNNNNNNNNNNgG..",  # 23  second gold grip wrap
    "..GGNNNNNNNNNNNNNNNNNNNNNNNgG..",  # 24
    "..=GGNNNNNNNNNNNNNNNNNNNNNgGG..",  # 25  shield begins to taper
    "...=GGGNNNNNNNNNNNNNNNNNNgGG...",  # 26
    "....=GGGGNNNNNNNNNNNNNNgGGG....",  # 27
    ".....=GGGGGGNNNNNNNNGGGGGg.....",  # 28
    "......=GGGGGGGGGGGGGGGGGg......",  # 29  base of shield
    ".......=GGGGGGGGGGGGGGGg.......",  # 30  point
    "........=GGGGGGGGGGGGGg........",  # 31  tip
]

def build_image_32() -> Image.Image:
    img = Image.new("RGBA", (32, 32), TRANS)
    px  = img.load()
    for y, row in enumerate(PIXELS_32):
        for x, ch in enumerate(row):
            c = LEGEND.get(ch, TRANS)
            px[x, y] = c
    return img


def make_ico(path: str):
    master = build_image_32()

    sizes = [
        (48, 48, Image.NEAREST),   # large  — nearest keeps pixel art crisp
        (32, 32, Image.NEAREST),   # medium
        (16, 16, Image.NEAREST),   # small
    ]

    frames = []
    for w, h, resample in sizes:
        frame = master.resize((w, h), resample)
        frames.append(frame)

    # Save as multi-size ICO
    frames[0].save(
        path,
        format="ICO",
        sizes=[(f.width, f.height) for f in frames],
        append_images=frames[1:],
    )
    print(f"Saved {path}  ({os.path.getsize(path):,} bytes)")


if __name__ == "__main__":
    out = pathlib.Path(__file__).parent / "AzroksRepublic.ico"
    make_ico(str(out))
