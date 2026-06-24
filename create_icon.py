"""Generate gfx/icon.ico and gfx/icon.png for Aimer 8."""
from PIL import Image, ImageDraw
import os

BG      = (2,   4,  18, 255)
HULL    = (210, 220, 235, 255)
INNER   = ( 70,  75,  88, 255)
COCKPIT = ( 50, 210, 255, 220)
ENGINE  = ( 40, 130, 255, 200)
FIN     = (255,  65,  65, 220)
STAR    = (255, 255, 255, 160)
GLOW    = ( 60, 220, 255, 160)

# star positions expressed as fractions of icon size
STARS = [(0.13,0.14),(0.78,0.18),(0.85,0.73),(0.18,0.80),(0.70,0.47),(0.25,0.40)]

def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    r   = size // 8

    # rounded dark background
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=BG)

    # stars
    ss = max(1, size // 48)
    for fx, fy in STARS:
        px, py = int(fx * size), int(fy * size)
        d.rectangle([px, py, px + ss - 1, py + ss - 1], fill=STAR)

    # ---------- ship (design space: 64 px, scaled to `size`) ----------
    S  = size / 64
    cx = size / 2
    cy = size / 2

    sw = 38 * S          # total ship width
    sh = 22 * S          # total ship height
    sx = cx - sw * 0.45  # left edge
    sy = cy - sh / 2     # top edge

    tip   = (sx + sw,        cy)
    nose  = (sx + sw - 6*S,  sy + 2*S)
    tail  = (sx,              cy)
    nose2 = (sx + sw - 6*S,  sy + sh - 2*S)

    # outer hull
    d.polygon([tail, nose, tip, nose2], fill=HULL)

    # inner hull shade
    margin = 6 * S
    d.polygon([
        (sx + margin,            cy),
        (sx + sw - 7*S,          sy + 7*S),
        (sx + sw - 3*S,          cy),
        (sx + sw - 7*S,          sy + sh - 7*S),
    ], fill=INNER)

    # top fin
    d.polygon([
        (sx + 8*S,  cy - 1*S),
        (sx + 16*S, sy + 1*S),
        (sx + 16*S, cy - 1*S),
    ], fill=FIN)

    # bottom fin
    d.polygon([
        (sx + 8*S,  cy + 1*S),
        (sx + 16*S, sy + sh - 1*S),
        (sx + 16*S, cy + 1*S),
    ], fill=FIN)

    # cockpit window
    ck_cx = sx + sw * 0.56
    ck_cy = cy
    ck_r  = 4 * S
    d.ellipse([ck_cx - ck_r, ck_cy - ck_r, ck_cx + ck_r, ck_cy + ck_r], fill=COCKPIT)

    # engine glow (left / rear)
    eg_r = 4 * S
    d.ellipse([sx - eg_r * 0.6, cy - eg_r, sx + eg_r * 0.6, cy + eg_r], fill=ENGINE)

    # thruster streak
    for i, alpha in enumerate([60, 40, 20]):
        streak_len = (6 + i * 5) * S
        col = (40, 180, 255, alpha)
        d.rectangle([sx - streak_len, cy - 1.5*S, sx, cy + 1.5*S], fill=col)

    return img


def main():
    os.makedirs("gfx", exist_ok=True)

    sizes = [256, 128, 64, 48, 32, 16]
    images = [draw_icon(s) for s in sizes]

    # Save ICO with all sizes
    images[0].save(
        "gfx/icon.ico",
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )
    print("Created gfx/icon.ico")

    # Save 256-px PNG for reference / debugging
    images[0].save("gfx/icon.png")
    print("Created gfx/icon.png")


if __name__ == "__main__":
    main()
