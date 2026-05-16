"""Build og-image.png at 1200x630 using Pillow + system fonts.

Produces the social-sharing card matching the brand palette in the dashboard.
Run: python _build_og_image.py
"""

from PIL import Image, ImageDraw, ImageFont
import os

W, H = 1200, 630

# Palette (matches the dashboard CSS variables)
BG_TOP = (253, 250, 245)        # --bg
BG_BOT = (250, 243, 223)        # --accent-bg
ACCENT = (184, 134, 47)         # --accent
ACCENT_2 = (212, 167, 63)       # --accent-2
TEXT = (26, 34, 54)             # --text
TEXT_2 = (74, 82, 102)          # --text-2
TEXT_3 = (138, 142, 156)        # --text-3
BORDER = (228, 221, 208)        # --border

# Fonts
FONTS_DIR = "C:/Windows/Fonts/"
def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS_DIR, name), size)

ar_huge = font("Amiri-Bold.ttf", 220)
ar_med = font("Amiri-Bold.ttf", 40)
en_huge = font("arialbd.ttf", 86)
en_sub = font("arial.ttf", 34)
en_label = font("arialbd.ttf", 16)
en_stat = font("arialbd.ttf", 60)
en_small = font("arial.ttf", 22)
en_tiny = font("arial.ttf", 18)

img = Image.new("RGB", (W, H), BG_TOP)
draw = ImageDraw.Draw(img)

# Vertical gradient (top to bottom-right warm)
for y in range(H):
    t = y / H
    r = int(BG_TOP[0] * (1 - t) + BG_BOT[0] * t)
    g = int(BG_TOP[1] * (1 - t) + BG_BOT[1] * t)
    b = int(BG_TOP[2] * (1 - t) + BG_BOT[2] * t)
    draw.line([(0, y), (W, y)], fill=(r, g, b))

# Top accent stripe
draw.rectangle([0, 0, W, 8], fill=ACCENT)

# Arabic brand mark (right side, behind, large)
ar_text = "جُذُور"
bbox = draw.textbbox((0, 0), ar_text, font=ar_huge)
ar_w = bbox[2] - bbox[0]
# Place top-right with breathing room
ar_x = W - 90 - ar_w
ar_y = 70
draw.text((ar_x, ar_y), ar_text, font=ar_huge, fill=ACCENT)

# English title (top-left)
draw.text((100, 130), "Juthoor", font=en_huge, fill=TEXT)

# Subtitle
draw.text((100, 230), "The Arabic Tongue", font=en_sub, fill=ACCENT)
draw.text((100, 275), "meaning from letter to root", font=en_sub, fill=TEXT_2)

# Divider
draw.rectangle([100, 335, 180, 338], fill=ACCENT)

# Stats row
stats = [
    ("28", "LETTERS"),
    ("453", "BINARY NUCLEI"),
    ("2,285", "TRILATERALS"),
    ("12", "OPERATIVE MODES"),
    ("100%", "NATIVE FIT"),
]
x = 100
y_num = 395
y_lab = 470
for num, lab in stats:
    nb = draw.textbbox((0, 0), num, font=en_stat)
    nw = nb[2] - nb[0]
    draw.text((x, y_num), num, font=en_stat, fill=ACCENT)
    draw.text((x, y_lab), lab, font=en_label, fill=TEXT_2)
    # Width to advance: max of number and label
    lb = draw.textbbox((0, 0), lab, font=en_label)
    lw = lb[2] - lb[0]
    x += max(nw, lw) + 50

# Footer divider
draw.rectangle([0, 553, W, 555], fill=BORDER)

# Footer text
draw.text((100, 580), "arabicjuthoor.com", font=en_small, fill=TEXT_2)

# Right footer (smaller, gray)
right_text = "Conducted under Temessek for Research, Publishing & Training"
rb = draw.textbbox((0, 0), right_text, font=en_tiny)
rw = rb[2] - rb[0]
draw.text((W - 100 - rw, 585), right_text, font=en_tiny, fill=TEXT_3)

img.save("og-image.png", "PNG", optimize=True)
print(f"og-image.png written: {os.path.getsize('og-image.png')/1024:.1f} KB at {W}x{H}")
