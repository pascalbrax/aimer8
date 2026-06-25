"""Generate gfx/icon.ico and gfx/icon.png for Aimer 8.

Uses the actual player ship sprite from gfx/sprites.png when available,
falling back to a procedurally drawn ship otherwise.
"""
from PIL import Image, ImageDraw
import os

BG   = (2,   4,  18, 255)
STAR = (255, 255, 255, 160)

# star positions as fractions of icon size
STARS = [(0.13, 0.14), (0.78, 0.18), (0.85, 0.73), (0.18, 0.80)]

SHEET_PATH = os.path.join("gfx", "sprites.png")

# Player ship (frame 1) location on the 1254×1254 sprites.png sheet, in
# absolute pixels (must match PLAYER_FRAMES_SRC[0] in main.py).
PLAYER_RECT = (28, 71, 167, 135)   # x, y, w, h


# -----------------------------------------------------------------------
# Sprite extraction helpers
# -----------------------------------------------------------------------

def trim_alpha(img: Image.Image) -> Image.Image:
    """Crop to the non-transparent bounding box."""
    bbox = img.getbbox()
    if bbox:
        return img.crop(bbox)
    return img


def extract_player_sprite() -> Image.Image | None:
    """Return the player ship as a trimmed RGBA image, or None on failure."""
    if not os.path.exists(SHEET_PATH):
        return None
    try:
        sheet = Image.open(SHEET_PATH).convert("RGBA")

        x, y, w, h = PLAYER_RECT
        region = sheet.crop((x, y, x + w, y + h))
        region = trim_alpha(region)
        if region.width < 3 or region.height < 3:
            return None
        return region
    except Exception as e:
        print(f"Could not extract player sprite: {e}")
        return None


# -----------------------------------------------------------------------
# Fallback procedural ship (Pillow version of the original draw_icon)
# -----------------------------------------------------------------------

def draw_fallback_ship(size: int) -> Image.Image:
    """Draw a procedural ship centered on a transparent canvas of `size`×`size`."""
    HULL   = (210, 220, 235, 255)
    INNER  = ( 70,  75,  88, 255)
    COCKPIT= ( 50, 210, 255, 220)
    ENGINE = ( 40, 130, 255, 200)
    FIN    = (255,  65,  65, 220)

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    S   = size / 64
    cx, cy = size / 2, size / 2

    sw = 38 * S
    sh = 22 * S
    sx = cx - sw * 0.45
    sy = cy - sh / 2

    tip   = (sx + sw,       cy)
    nose  = (sx + sw - 6*S, sy + 2*S)
    tail  = (sx,             cy)
    nose2 = (sx + sw - 6*S, sy + sh - 2*S)

    d.polygon([tail, nose, tip, nose2], fill=HULL)

    margin = 6 * S
    d.polygon([
        (sx + margin,      cy),
        (sx + sw - 7*S,    sy + 7*S),
        (sx + sw - 3*S,    cy),
        (sx + sw - 7*S,    sy + sh - 7*S),
    ], fill=INNER)

    d.polygon([(sx+8*S, cy-1*S), (sx+16*S, sy+1*S),      (sx+16*S, cy-1*S)], fill=FIN)
    d.polygon([(sx+8*S, cy+1*S), (sx+16*S, sy+sh-1*S),   (sx+16*S, cy+1*S)], fill=FIN)

    ck_cx, ck_cy, ck_r = sx + sw * 0.56, cy, 4 * S
    d.ellipse([ck_cx-ck_r, ck_cy-ck_r, ck_cx+ck_r, ck_cy+ck_r], fill=COCKPIT)

    eg_r = 4 * S
    d.ellipse([sx - eg_r*0.6, cy-eg_r, sx + eg_r*0.6, cy+eg_r], fill=ENGINE)

    for i, alpha in enumerate([60, 40, 20]):
        streak_len = (6 + i*5) * S
        d.rectangle([sx - streak_len, cy - 1.5*S, sx, cy + 1.5*S], fill=(40, 180, 255, alpha))

    return img


# -----------------------------------------------------------------------
# Icon composer
# -----------------------------------------------------------------------

def make_icon(size: int, sprite: Image.Image | None) -> Image.Image:
    """Compose the icon: dark rounded background + stars + ship."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    r   = size // 8

    # dark rounded background
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=BG)

    # stars
    ss = max(1, size // 48)
    for fx, fy in STARS:
        px, py = int(fx * size), int(fy * size)
        d.rectangle([px, py, px + ss - 1, py + ss - 1], fill=STAR)

    # ship — fit inside with 14% padding on each side
    pad   = int(size * 0.14)
    avail = size - 2 * pad

    if sprite is not None:
        sw, sh = sprite.size
        scale  = min(avail / sw, avail / sh)
        new_w  = max(1, int(sw * scale))
        new_h  = max(1, int(sh * scale))
        resized = sprite.resize((new_w, new_h), Image.LANCZOS)
        ox = (size - new_w) // 2
        oy = (size - new_h) // 2
        img.paste(resized, (ox, oy), resized)
    else:
        ship_layer = draw_fallback_ship(size)
        img.alpha_composite(ship_layer)

    return img


# -----------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------

def main():
    os.makedirs("gfx", exist_ok=True)

    sprite = extract_player_sprite()
    if sprite:
        print(f"Using sprite from {SHEET_PATH} ({sprite.size[0]}×{sprite.size[1]} px)")
    else:
        print("Sprite sheet not found or failed to load — using procedural fallback.")

    sizes  = [256, 128, 64, 48, 32, 16]
    images = [make_icon(s, sprite) for s in sizes]

    images[0].save(
        "gfx/icon.ico",
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )
    print("Created gfx/icon.ico")

    images[0].save("gfx/icon.png")
    print("Created gfx/icon.png")


if __name__ == "__main__":
    main()
