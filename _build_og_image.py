"""Build og-image.png + og-image-ar.png (1200x630) using Pillow.

Produces two social-sharing cards matching the brand palette in the dashboard.
The Arabic variant is RTL: title on the right, English brand mark on the left.

Run: python _build_og_image.py
"""

from PIL import Image, ImageDraw, ImageFont
import os
import arabic_reshaper
from bidi.algorithm import get_display


def ar(text: str) -> str:
    """Shape Arabic text for Pillow rendering: contextual forms + RTL bidi.

    Pillow's text() does not apply Arabic shaping — it draws code-point glyphs
    left-to-right with isolated forms only. We must (1) reshape the string so
    letters take their correct initial/medial/final/isolated contextual form,
    then (2) apply the bidi algorithm to lay the result out right-to-left.
    """
    return get_display(arabic_reshaper.reshape(text))


W, H = 1200, 630

# Palette (matches the dashboard CSS variables)
BG_TOP = (253, 250, 245)        # --bg
BG_BOT = (250, 243, 223)        # --accent-bg
ACCENT = (138, 94, 31)          # --accent-strong (WCAG AA, matches dashboard)
ACCENT_LIGHT = (184, 134, 47)   # --accent (decorative)
ACCENT_2 = (212, 167, 63)       # --accent-2
TEXT = (26, 34, 54)             # --text
TEXT_2 = (74, 82, 102)          # --text-2
TEXT_3 = (95, 98, 117)          # --text-3 (darkened)
BORDER = (228, 221, 208)        # --border

# Fonts
FONTS_DIR = "C:/Windows/Fonts/"


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS_DIR, name), size)


ar_huge = font("Amiri-Bold.ttf", 220)
ar_title = font("Amiri-Bold.ttf", 120)
ar_sub = font("Amiri-Regular.ttf", 44)
ar_med = font("Amiri-Bold.ttf", 40)
ar_label = font("Amiri-Bold.ttf", 22)
en_huge = font("arialbd.ttf", 86)
en_sub = font("arial.ttf", 34)
en_label = font("arialbd.ttf", 16)
en_stat = font("arialbd.ttf", 60)
en_small = font("arial.ttf", 22)
en_tiny = font("arial.ttf", 18)


def gradient_bg(img):
    """Apply vertical gradient: BG_TOP -> BG_BOT."""
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        r = int(BG_TOP[0] * (1 - t) + BG_BOT[0] * t)
        g = int(BG_TOP[1] * (1 - t) + BG_BOT[1] * t)
        b = int(BG_TOP[2] * (1 - t) + BG_BOT[2] * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))


def build_en():
    """English-locale card: title left, Arabic brand mark right."""
    img = Image.new("RGB", (W, H), BG_TOP)
    gradient_bg(img)
    draw = ImageDraw.Draw(img)

    # Top accent stripe
    draw.rectangle([0, 0, W, 8], fill=ACCENT_LIGHT)

    # Arabic brand mark (right side, large)
    ar_text = ar("جُذُور")
    bbox = draw.textbbox((0, 0), ar_text, font=ar_huge)
    ar_w = bbox[2] - bbox[0]
    draw.text((W - 90 - ar_w, 70), ar_text, font=ar_huge, fill=ACCENT)

    # English title (top-left)
    draw.text((100, 130), "Juthoor", font=en_huge, fill=TEXT)

    # Subtitle
    draw.text((100, 230), "The Arabic Tongue", font=en_sub, fill=ACCENT)
    draw.text((100, 275), "meaning from letter to root", font=en_sub, fill=TEXT_2)

    # Divider
    draw.rectangle([100, 335, 180, 338], fill=ACCENT_LIGHT)

    # Stats row
    stats = [
        ("28", "LETTERS"),
        ("453", "BINARY NUCLEI"),
        ("2,285", "TRILATERALS"),
        ("12", "OPERATIVE MODES"),
        ("100%", "NATIVE FIT"),
    ]
    x = 100
    for num, lab in stats:
        draw.text((x, 395), num, font=en_stat, fill=ACCENT)
        draw.text((x, 470), lab, font=en_label, fill=TEXT_2)
        nb = draw.textbbox((0, 0), num, font=en_stat)
        lb = draw.textbbox((0, 0), lab, font=en_label)
        x += max(nb[2] - nb[0], lb[2] - lb[0]) + 50

    # Footer
    draw.rectangle([0, 553, W, 555], fill=BORDER)
    draw.text((100, 580), "arabicjuthoor.com", font=en_small, fill=TEXT_2)
    right = "Conducted under Temessek for Research, Publishing & Training"
    rb = draw.textbbox((0, 0), right, font=en_tiny)
    draw.text((W - 100 - (rb[2] - rb[0]), 585), right, font=en_tiny, fill=TEXT_3)

    img.save("og-image.png", "PNG", optimize=True)
    print(f"og-image.png    -> {os.path.getsize('og-image.png')/1024:.1f} KB")


def build_ar():
    """Arabic-locale card: brand mark left, Arabic title right (RTL composition)."""
    img = Image.new("RGB", (W, H), BG_TOP)
    gradient_bg(img)
    draw = ImageDraw.Draw(img)

    # Top accent stripe
    draw.rectangle([0, 0, W, 8], fill=ACCENT_LIGHT)

    # Arabic title (top-right, dominant)
    ar_title_t = ar("جُذُور")
    bb = draw.textbbox((0, 0), ar_title_t, font=ar_huge)
    tw = bb[2] - bb[0]
    draw.text((W - 100 - tw, 100), ar_title_t, font=ar_huge, fill=TEXT)

    # Subtitle (right-aligned, Arabic)
    sub1 = ar("العربيّةُ: من الحرف إلى الجذر")
    bb = draw.textbbox((0, 0), sub1, font=ar_sub)
    sw = bb[2] - bb[0]
    draw.text((W - 100 - sw, 320), sub1, font=ar_sub, fill=ACCENT)

    sub2 = ar("بِنيةُ المعنى في اللسان العربيّ")
    bb = draw.textbbox((0, 0), sub2, font=ar_sub)
    sw = bb[2] - bb[0]
    draw.text((W - 100 - sw, 380), sub2, font=ar_sub, fill=TEXT_2)

    # Divider (right-anchored)
    draw.rectangle([W - 180, 445, W - 100, 448], fill=ACCENT_LIGHT)

    # Stats row (right-to-left layout)
    stats_ar = [
        ("28", ar("حرفًا")),
        ("453", ar("نواةً ثنائيّة")),
        ("2,285", ar("جذرًا ثلاثيًّا")),
        ("12", ar("بابًا تركيبيًّا")),
        ("100%", ar("مُطابقةٌ أصليّة")),
    ]
    x_right = W - 100
    for num, lab in stats_ar:
        nb = draw.textbbox((0, 0), num, font=en_stat)
        nw = nb[2] - nb[0]
        lb = draw.textbbox((0, 0), lab, font=ar_label)
        lw = lb[2] - lb[0]
        cell_w = max(nw, lw)
        # Right-align both number and label inside the cell
        draw.text((x_right - cell_w + (cell_w - nw) // 2, 485), num, font=en_stat, fill=ACCENT)
        draw.text((x_right - cell_w + (cell_w - lw) // 2, 560), lab, font=ar_label, fill=TEXT_2)
        x_right -= cell_w + 40

    # English brand mark (small, bottom-left as anchor)
    draw.text((100, 130), "Juthoor", font=en_huge, fill=ACCENT)
    draw.text((100, 230), "The Arabic Tongue", font=en_sub, fill=TEXT_2)

    # Footer divider higher to clear the AR stats
    draw.rectangle([0, 615, W, 617], fill=BORDER)

    img.save("og-image-ar.png", "PNG", optimize=True)
    print(f"og-image-ar.png -> {os.path.getsize('og-image-ar.png')/1024:.1f} KB")


if __name__ == "__main__":
    build_en()
    build_ar()
