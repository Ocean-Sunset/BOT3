"""
Prowl emoji generator — Lucide icon font glyphs on semi-transparent rounded-rect backgrounds.

Usage:  python whitebots.online\generate_emojis.py
Output: whitebots.online/emojis/  (128x128 PNGs named after EMBED_EMOJIS keys)
"""
import os
from PIL import Image, ImageDraw, ImageFont

SIZE      = 128
BG_RX     = 24        # rounded-rect corner radius
BG_ALPHA  = 0.43      # background opacity
FONT_SIZE = 72        # icon glyph size inside the 128px canvas
FONT_PATH = os.path.join(os.path.dirname(__file__), "lucide.ttf")

# (lucide_char, color_hex)
ICONS = {
    "ban":           ("\uE051", "#EF4444"),
    "tempban":       ("\uE087", "#EF4444"),
    "kick":          ("\uE10E", "#EF4444"),
    "mute":          ("\uE1AC", "#F59E0B"),
    "unmute":        ("\uE1AB", "#22C55E"),
    "warn":          ("\uE193", "#F59E0B"),
    "unban":         ("\uE1FF", "#22C55E"),
    "purge":         ("\uE18E", "#3B82F6"),
    "modlog":        ("\uE45F", "#3B82F6"),
    "dm":            ("\uE10F", "#3B82F6"),
    "level_up":      ("\uE191", "#22C55E"),
    "rank":          ("\uE04F", "#3B82F6"),
    "leaderboard":   ("\uE373", "#8B5CF6"),
    "welcome":       ("\uE412", "#22C55E"),
    "goodbye":       ("\uE3D6", "#EF4444"),
    "auto_role":     ("\uE158", "#8B5CF6"),
    "ticket":        ("\uE20F", "#8B5CF6"),
    "ticket_open":   ("\uE20F", "#8B5CF6"),
    "ticket_close":  ("\uE531", "#8B5CF6"),
    "verify":        ("\uE241", "#22C55E"),
    "verify_fail":   ("\uE084", "#EF4444"),
    "invite_join":   ("\uE1A2", "#8B5CF6"),
    "invite_stats":  ("\uE152", "#8B5CF6"),
    "global_chat":   ("\uE0E8", "#3B82F6"),
    "anti_raid":     ("\uE1FF", "#3B82F6"),
    "settings":      ("\uE154", "#8B5CF6"),
}

OUT_DIR = os.path.join(os.path.dirname(__file__), "emojis")
os.makedirs(OUT_DIR, exist_ok=True)


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def generate(char, color_hex):
    rgb = hex_to_rgb(color_hex)
    bg = rgb + (int(255 * BG_ALPHA),)
    fg = rgb + (255,)

    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # background
    draw.rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=BG_RX, fill=bg)

    # icon glyph
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    bbox = font.getbbox(char)
    gw = bbox[2] - bbox[0]
    gh = bbox[3] - bbox[1]
    x = (SIZE - gw) / 2 - bbox[0]
    y = (SIZE - gh) / 2 - bbox[1]
    draw.text((x, y), char, font=font, fill=fg)

    return img


def main():
    count = 0
    for key, (char, color) in sorted(ICONS.items()):
        try:
            img = generate(char, color)
            img.save(os.path.join(OUT_DIR, f"{key}.png"), "PNG")
            count += 1
            print(f"  {key}.png")
        except Exception as e:
            print(f"  {key}: ERROR {e}")

    print(f"\n{count}/{len(ICONS)} emojis saved to {OUT_DIR}/")


if __name__ == "__main__":
    main()
