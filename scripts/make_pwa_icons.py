"""
Draw the home-screen icons for the installable web app (PWA).

A white speech bubble with a euro sign on green: "money coach". Deliberately
not S-Bank's own S logo, so an installed demo can't pass for the real
S-mobiili app. Writes frontend/public/icons/:

- icon-192.png, icon-512.png: rounded square for browsers and Android
- maskable-512.png: full-bleed; Android crops it to its own shape (circle,
  squircle), so the drawing stays inside the central 80 % safe zone
- apple-touch-icon.png (180 x 180): full-bleed; iOS rounds the corners itself

    .venv/bin/python scripts/make_pwa_icons.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

GREEN = "#007841"   # --sp-green-strong in frontend/src/styles/tokens.css
WHITE = "#ffffff"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
OUT = Path(__file__).resolve().parent.parent / "frontend" / "public" / "icons"
SCALE = 4  # draw large, then shrink, for smooth edges


def draw_icon(size, *, rounded, content_scale):
    big = size * SCALE
    image = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    if rounded:
        draw.rounded_rectangle((0, 0, big - 1, big - 1), radius=big * 0.22, fill=GREEN)
    else:
        draw.rectangle((0, 0, big, big), fill=GREEN)

    # Speech bubble, centred, scaled to the safe area.
    c = big / 2
    w = big * 0.62 * content_scale
    h = big * 0.50 * content_scale
    top = c - h / 2 - big * 0.04 * content_scale
    box = (c - w / 2, top, c + w / 2, top + h)
    draw.rounded_rectangle(box, radius=h * 0.32, fill=WHITE)
    # Tail at the bottom left.
    tail_x = c - w * 0.22
    draw.polygon(
        [(tail_x, box[3] - 2), (tail_x + w * 0.20, box[3] - 2), (tail_x - w * 0.06, box[3] + h * 0.26)],
        fill=WHITE,
    )

    # Euro sign in the bubble.
    font = ImageFont.truetype(FONT, int(h * 0.72))
    left, upper, right, lower = draw.textbbox((0, 0), "€", font=font)
    draw.text(
        (c - (left + right) / 2, top + h / 2 - (upper + lower) / 2),
        "€", font=font, fill=GREEN,
    )

    return image.resize((size, size), Image.LANCZOS)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    draw_icon(192, rounded=True, content_scale=1.0).save(OUT / "icon-192.png")
    draw_icon(512, rounded=True, content_scale=1.0).save(OUT / "icon-512.png")
    draw_icon(512, rounded=False, content_scale=0.78).save(OUT / "maskable-512.png")
    draw_icon(180, rounded=False, content_scale=0.9).convert("RGB").save(OUT / "apple-touch-icon.png")
    print(f"Icons written to {OUT}")


if __name__ == "__main__":
    main()
