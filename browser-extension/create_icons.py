"""
Generate gradient icons for the Bridge browser extension.
Matches the app's purple-to-blue gradient: #7C3AED → #2563EB
Run once: python browser-extension/create_icons.py
Requires: pip install pillow
"""
import os
from PIL import Image, ImageDraw, ImageFont

SIZES = [16, 48, 128]
OUT_DIR = os.path.join(os.path.dirname(__file__), "icons")
os.makedirs(OUT_DIR, exist_ok=True)

# App gradient colours: violet-600 → blue-600
GRAD_START = (124, 58, 237)   # #7C3AED
GRAD_END   = (37, 99, 235)    # #2563EB


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


for size in SIZES:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw horizontal gradient circle pixel-by-pixel
    for x in range(size):
        t = x / max(size - 1, 1)
        col = lerp_color(GRAD_START, GRAD_END, t) + (255,)
        for y in range(size):
            # Only paint pixels inside the circle
            cx, cy = size / 2, size / 2
            if (x - cx) ** 2 + (y - cy) ** 2 <= (size / 2) ** 2:
                img.putpixel((x, y), col)

    draw = ImageDraw.Draw(img)

    # White "B" centred
    font_size = max(int(size * 0.55), 8)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    text = "B"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - tw) // 2 - bbox[0]
    y = (size - th) // 2 - bbox[1]
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)

    path = os.path.join(OUT_DIR, f"icon{size}.png")
    img.save(path)
    print(f"Created {path}")

print("Icons generated successfully.")
