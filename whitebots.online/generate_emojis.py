"""
Prowl emoji generator - Lucide icon font glyphs on semi-transparent rounded-rect backgrounds.
Expanded set: 128 emojis covering moderation, leveling, welcomer, tickets, verification,
invite tracker, global chat, anti-raid, status, and general UI icons.

Usage:  python whitebots.online\generate_emojis.py
Output: whitebots.online/emojis/  (128x128 PNGs named after EMBED_EMOJIS keys)
"""
import os
from PIL import Image, ImageDraw, ImageFont

SIZE      = 128
BG_RX     = 24
BG_ALPHA  = 0.43
FONT_SIZE = 72
FONT_PATH = os.path.join(os.path.dirname(__file__), "lucide.ttf")

# (lucide_char, color_hex)
# All icons are unique Lucide codepoints - no two keys share a glyph.
ICONS = {
    # ═══════ MODERATION ═══════
    "ban":            ("\ue051", "#EF4444"),
    "tempban":        ("\ue601", "#EF4444"),
    "kick":           ("\ue07a", "#EF4444"),
    "mute":           ("\ue1ac", "#F59E0B"),
    "unmute":         ("\ue1ab", "#22C55E"),
    "warn":           ("\ue193", "#F59E0B"),
    "unban":          ("\ue226", "#22C55E"),
    "purge":          ("\ue18e", "#3B82F6"),
    "modlog":         ("\ue45f", "#3B82F6"),
    "dm":             ("\ue10f", "#3B82F6"),
    "timeout":        ("\ue1e0", "#F59E0B"),
    "softban":        ("\ue159", "#EF4444"),
    "case":           ("\ue247", "#3B82F6"),
    "evidence":       ("\ue536", "#3B82F6"),

    # ═══════ LEVELING ═══════
    "level_up":       ("\ue07b", "#22C55E"),
    "rank":           ("\ue373", "#3B82F6"),
    "leaderboard":    ("\ue36f", "#8B5CF6"),
    "xp":             ("\ue1b4", "#F59E0B"),
    "streak":         ("\ue0d2", "#F97316"),
    "milestone":      ("\ue2d2", "#8B5CF6"),
    "reward":         ("\ue0e1", "#22C55E"),

    # ═══════ WELCOMER ═══════
    "welcome":        ("\ue1d7", "#22C55E"),
    "goodbye":        ("\ue3d6", "#EF4444"),
    "auto_role":      ("\ue1ff", "#8B5CF6"),
    "boost":          ("\ue412", "#F472B6"),

    # ═══════ TICKETS ═══════
    "ticket":         ("\ue20f", "#8B5CF6"),
    "ticket_open":    ("\ue20f", "#22C55E"),
    "ticket_close":   ("\ue07c", "#EF4444"),
    "ticket_claim":   ("\ue1a0", "#3B82F6"),
    "ticket_reopen":  ("\ue148", "#F59E0B"),

    # ═══════ VERIFICATION ═══════
    "verify":         ("\ue241", "#22C55E"),
    "verify_fail":    ("\ue200", "#EF4444"),
    "verify_pending": ("\ue109", "#F59E0B"),

    # ═══════ INVITE TRACKER ═══════
    "invite_join":    ("\ue1a2", "#8B5CF6"),
    "invite_stats":   ("\ue2a2", "#8B5CF6"),
    "invite_create":  ("\ue102", "#22C55E"),
    "invite_revoke":  ("\ue18e", "#EF4444"),

    # ═══════ GLOBAL CHAT ═══════
    "global_chat":    ("\ue0e8", "#3B82F6"),
    "global_msg":     ("\ue152", "#22C55E"),
    "global_linked":  ("\ue102", "#22C55E"),

    # ═══════ ANTI-RAID / SECURITY ═══════
    "anti_raid":      ("\ue1fe", "#3B82F6"),
    "raid_detected":  ("\ue2ef", "#EF4444"),
    "raid_blocked":   ("\ue159", "#EF4444"),

    # ═══════ STATUS / FEEDBACK ═══════
    "success":        ("\ue226", "#22C55E"),
    "error":          ("\ue084", "#EF4444"),
    "info":           ("\ue077", "#3B82F6"),
    "warning":        ("\ue193", "#F59E0B"),
    "pending":        ("\ue109", "#F59E0B"),

    # ═══════ UI / GENERAL - neutral gray for purely structural icons ═══════
    "settings":       ("\ue154", "#6B7280"),
    "dashboard":      ("\ue1c1", "#6B7280"),
    "analytics":      ("\ue2a3", "#6B7280"),
    "database":       ("\ue0ad", "#6B7280"),
    "server":         ("\ue153", "#6B7280"),
    "member":         ("\ue19f", "#6B7280"),
    "members":        ("\ue1a4", "#6B7280"),
    "channel":        ("\ue0ef", "#6B7280"),
    "role":           ("\ue158", "#6B7280"),
    "bot":            ("\ue1bb", "#6B7280"),
    "link":           ("\ue0b9", "#6B7280"),
    "copy":           ("\ue09e", "#6B7280"),
    "save":           ("\ue14d", "#6B7280"),
    "search":         ("\ue151", "#6B7280"),
    "refresh":        ("\ue145", "#6B7280"),
    "download":       ("\ue0b2", "#6B7280"),
    "upload":         ("\ue19e", "#6B7280"),
    "lock":           ("\ue10b", "#F59E0B"),
    "unlock":         ("\ue10c", "#22C55E"),
    "key":            ("\ue0fd", "#F59E0B"),
    "star":           ("\ue176", "#F59E0B"),
    "pin":            ("\ue259", "#EF4444"),
    "clock":          ("\ue087", "#6B7280"),
    "calendar":       ("\ue063", "#6B7280"),
    "bell":           ("\ue059", "#F59E0B"),
    "bell_off":       ("\ue05a", "#6B7280"),
    "eye":            ("\ue0ba", "#6B7280"),
    "eye_off":        ("\ue0bb", "#6B7280"),
    "check":          ("\ue06c", "#22C55E"),
    "cross":          ("\ue1b2", "#EF4444"),
    "heart":          ("\ue0f2", "#EF4444"),
    "bolt":           ("\ue1b4", "#F59E0B"),
    "fire":           ("\ue0d2", "#F97316"),
    "code":           ("\ue093", "#6B7280"),
    "terminal":       ("\ue181", "#6B7280"),
    "bug":            ("\ue20c", "#EF4444"),
    "rocket":         ("\ue286", "#8B5CF6"),
    "sparkle":        ("\ue412", "#F472B6"),
    "cloud":          ("\ue088", "#6B7280"),
    "sun":            ("\ue178", "#F59E0B"),
    "moon":           ("\ue11e", "#8B5CF6"),
    "leaf":           ("\ue2de", "#22C55E"),
    "mountain":       ("\ue231", "#6B7280"),
    "flag":           ("\ue0d1", "#EF4444"),
    "compass":        ("\ue09b", "#6B7280"),
    "map":            ("\ue111", "#6B7280"),
    "globe":          ("\ue0e8", "#6B7280"),
    "anchor":         ("\ue03f", "#6B7280"),
    "tag":            ("\ue17f", "#6B7280"),
    "bookmark":       ("\ue060", "#8B5CF6"),
    "folder":         ("\ue0d7", "#6B7280"),
    "file":           ("\ue0c0", "#6B7280"),
    "archive":        ("\ue041", "#6B7280"),
    "package":        ("\ue129", "#6B7280"),
    "cpu":            ("\ue0a9", "#6B7280"),
    "wifi":           ("\ue1ae", "#6B7280"),
    "bluetooth":      ("\ue05c", "#6B7280"),
    "power":          ("\ue140", "#EF4444"),
    "music":          ("\ue122", "#8B5CF6"),
    "image":          ("\ue0f6", "#6B7280"),
    "video":          ("\ue1a5", "#6B7280"),
    "camera":         ("\ue064", "#6B7280"),
    "mic":            ("\ue118", "#6B7280"),
    "phone":          ("\ue133", "#6B7280"),
    "mail":           ("\ue10f", "#6B7280"),
    "message":        ("\ue116", "#6B7280"),
    "send":           ("\ue152", "#22C55E"),
    "inbox":          ("\ue0f7", "#6B7280"),
    "shield":         ("\ue158", "#6B7280"),
    "scan":           ("\ue257", "#6B7280"),
    "atom":           ("\ue3d7", "#8B5CF6"),
    "dna":            ("\ue393", "#22C55E"),
    "flask":          ("\ue0d5", "#6B7280"),
    "award":          ("\ue04f", "#F59E0B"),
    "crown":          ("\ue1d6", "#F59E0B"),
    "gem":            ("\ue242", "#8B5CF6"),
    "coffee":         ("\ue096", "#F59E0B"),
    "cake":           ("\ue344", "#F472B6"),
    "pizza":          ("\ue354", "#F59E0B"),
    "cookie":         ("\ue26b", "#F59E0B"),
    "gift":           ("\ue0e1", "#22C55E"),
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

    draw.rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=BG_RX, fill=bg)

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
