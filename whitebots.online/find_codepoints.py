"""Parse Lucide CSS to extract icon name → codepoint, then build the expanded EMOJIS dict."""
import re, json, urllib.request

css = urllib.request.urlopen("https://cdn.jsdelivr.net/npm/lucide-static@latest/font/lucide.css").read().decode()

mapping = {}
for m in re.finditer(r'\.icon-([a-z0-9-]+)::before\s*\{\s*content:\s*"\\([0-9a-fA-F]+)"', css):
    name, hex_val = m.group(1), m.group(2)
    char = chr(int(hex_val, 16))
    if name not in mapping:
        mapping[name] = char

print(f"Total unique icons: {len(mapping)}")

# Build expanded emoji set for Prowl bot
# Categories:
EMOJIS = {
    # ═══════ MODERATION ═══════
    "ban":           {"icon": "ban",            "color": "#EF4444"},
    "tempban":       {"icon": "clock-arrow-up", "color": "#EF4444"},
    "kick":          {"icon": "circle-arrow-right", "color": "#EF4444"},
    "mute":          {"icon": "volume-x",       "color": "#F59E0B"},
    "unmute":        {"icon": "volume-2",       "color": "#22C55E"},
    "warn":          {"icon": "triangle-alert",  "color": "#F59E0B"},
    "unban":         {"icon": "circle-check",    "color": "#22C55E"},
    "purge":         {"icon": "trash-2",         "color": "#3B82F6"},
    "modlog":        {"icon": "scroll-text",     "color": "#3B82F6"},
    "dm":            {"icon": "mail",            "color": "#3B82F6"},
    "timeout":       {"icon": "timer",           "color": "#F59E0B"},
    "softban":       {"icon": "shield-ban",      "color": "#EF4444"},
    "case":          {"icon": "folder-open",     "color": "#3B82F6"},
    "evidence":      {"icon": "scan-eye",        "color": "#3B82F6"},

    # ═══════ LEVELING ═══════
    "level_up":      {"icon": "arrow-up-circle", "color": "#22C55E"},
    "rank":          {"icon": "trophy",           "color": "#3B82F6"},
    "leaderboard":   {"icon": "medal",            "color": "#8B5CF6"},
    "xp":            {"icon": "zap",              "color": "#F59E0B"},
    "streak":        {"icon": "flame",            "color": "#F97316"},
    "milestone":     {"icon": "diamond",          "color": "#8B5CF6"},
    "reward":        {"icon": "gift",             "color": "#22C55E"},

    # ═══════ WELCOMER ═══════
    "welcome":       {"icon": "hand",             "color": "#22C55E"},
    "goodbye":       {"icon": "door-open",        "color": "#EF4444"},
    "auto_role":     {"icon": "shield-check",     "color": "#8B5CF6"},
    "boost":         {"icon": "sparkles",         "color": "#F472B6"},

    # ═══════ TICKETS ═══════
    "ticket":        {"icon": "ticket",           "color": "#8B5CF6"},
    "ticket_open":   {"icon": "ticket",           "color": "#22C55E"},
    "ticket_close":  {"icon": "circle-check-big", "color": "#EF4444"},
    "ticket_claim":  {"icon": "user-check",       "color": "#3B82F6"},
    "ticket_reopen": {"icon": "rotate-ccw",       "color": "#F59E0B"},

    # ═══════ VERIFICATION ═══════
    "verify":        {"icon": "shield-check",     "color": "#22C55E"},
    "verify_fail":   {"icon": "shield-x",         "color": "#EF4444"},
    "verify_pending":{"icon": "loader",           "color": "#F59E0B"},

    # ═══════ INVITE TRACKER ═══════
    "invite_join":   {"icon": "user-plus",        "color": "#8B5CF6"},
    "invite_stats":  {"icon": "chart-bar",        "color": "#8B5CF6"},
    "invite_create": {"icon": "link",             "color": "#22C55E"},
    "invite_revoke": {"icon": "link-break",       "color": "#EF4444"},

    # ═══════ GLOBAL CHAT ═══════
    "global_chat":   {"icon": "globe",            "color": "#3B82F6"},
    "global_msg":    {"icon": "send",             "color": "#22C55E"},
    "global_linked": {"icon": "link",             "color": "#22C55E"},

    # ═══════ ANTI-RAID / SECURITY ═══════
    "anti_raid":     {"icon": "shield-alert",     "color": "#3B82F6"},
    "raid_detected": {"icon": "siren",            "color": "#EF4444"},
    "raid_blocked":  {"icon": "shield-ban",       "color": "#EF4444"},

    # ═══════ STATUS / FEEDBACK ═══════
    "success":       {"icon": "circle-check",     "color": "#22C55E"},
    "error":         {"icon": "circle-x",         "color": "#EF4444"},
    "info":          {"icon": "circle-alert",     "color": "#3B82F6"},
    "warning":       {"icon": "triangle-alert",   "color": "#F59E0B"},
    "pending":       {"icon": "loader",           "color": "#F59E0B"},

    # ═══════ UI / GENERAL ═══════
    "settings":      {"icon": "settings",         "color": "#8B5CF6"},
    "dashboard":     {"icon": "layout-dashboard", "color": "#8B5CF6"},
    "analytics":     {"icon": "bar-chart-3",      "color": "#3B82F6"},
    "database":      {"icon": "database",         "color": "#3B82F6"},
    "server":        {"icon": "server",           "color": "#3B82F6"},
    "member":        {"icon": "user",             "color": "#3B82F6"},
    "members":       {"icon": "users",            "color": "#3B82F6"},
    "channel":       {"icon": "hash",             "color": "#3B82F6"},
    "role":          {"icon": "shield",           "color": "#8B5CF6"},
    "bot":           {"icon": "bot",              "color": "#8B5CF6"},
    "link":          {"icon": "external-link",    "color": "#3B82F6"},
    "copy":          {"icon": "copy",             "color": "#3B82F6"},
    "save":          {"icon": "save",             "color": "#22C55E"},
    "search":        {"icon": "search",           "color": "#3B82F6"},
    "refresh":       {"icon": "refresh-cw",       "color": "#3B82F6"},
    "download":      {"icon": "download",         "color": "#3B82F6"},
    "upload":        {"icon": "upload",           "color": "#3B82F6"},
    "lock":          {"icon": "lock",             "color": "#F59E0B"},
    "unlock":        {"icon": "unlock",           "color": "#22C55E"},
    "key":           {"icon": "key",              "color": "#F59E0B"},
    "star":          {"icon": "star",             "color": "#F59E0B"},
    "pin":           {"icon": "pin",              "color": "#EF4444"},
    "clock":         {"icon": "clock",            "color": "#3B82F6"},
    "calendar":      {"icon": "calendar",         "color": "#3B82F6"},
    "bell":          {"icon": "bell",             "color": "#F59E0B"},
    "bell_off":      {"icon": "bell-off",         "color": "#6B7280"},
    "eye":           {"icon": "eye",              "color": "#3B82F6"},
    "eye_off":       {"icon": "eye-off",          "color": "#6B7280"},
    "check":         {"icon": "check",            "color": "#22C55E"},
    "cross":         {"icon": "x",                "color": "#EF4444"},
    "heart":         {"icon": "heart",            "color": "#EF4444"},
    "bolt":          {"icon": "zap",              "color": "#F59E0B"},
    "fire":          {"icon": "flame",            "color": "#F97316"},
    "code":          {"icon": "code",             "color": "#3B82F6"},
    "terminal":      {"icon": "terminal",         "color": "#3B82F6"},
    "bug":           {"icon": "bug",              "color": "#EF4444"},
    "rocket":        {"icon": "rocket",           "color": "#8B5CF6"},
    "sparkle":       {"icon": "sparkles",         "color": "#F472B6"},
    "cloud":         {"icon": "cloud",            "color": "#3B82F6"},
    "sun":           {"icon": "sun",              "color": "#F59E0B"},
    "moon":          {"icon": "moon",             "color": "#8B5CF6"},
    "leaf":          {"icon": "leaf",             "color": "#22C55E"},
    "mountain":      {"icon": "mountain",         "color": "#3B82F6"},
    "flag":          {"icon": "flag",             "color": "#EF4444"},
    "compass":       {"icon": "compass",          "color": "#3B82F6"},
    "map":           {"icon": "map-pin",          "color": "#3B82F6"},
    "globe":         {"icon": "globe",            "color": "#3B82F6"},
    "anchor":        {"icon": "anchor",           "color": "#3B82F6"},
    "tag":           {"icon": "tag",              "color": "#3B82F6"},
    "bookmark":      {"icon": "bookmark",         "color": "#8B5CF6"},
    "folder":        {"icon": "folder",           "color": "#3B82F6"},
    "file":          {"icon": "file",             "color": "#3B82F6"},
    "archive":       {"icon": "archive",          "color": "#3B82F6"},
    "package":       {"icon": "package",          "color": "#8B5CF6"},
    "cpu":           {"icon": "cpu",              "color": "#3B82F6"},
    "wifi":          {"icon": "wifi",             "color": "#3B82F6"},
    "bluetooth":     {"icon": "bluetooth",        "color": "#3B82F6"},
    "power":         {"icon": "power",            "color": "#EF4444"},
    "music":         {"icon": "music",            "color": "#8B5CF6"},
    "image":         {"icon": "image",            "color": "#3B82F6"},
    "video":         {"icon": "video",            "color": "#3B82F6"},
    "camera":        {"icon": "camera",           "color": "#3B82F6"},
    "mic":           {"icon": "mic",              "color": "#3B82F6"},
    "phone":         {"icon": "phone",            "color": "#3B82F6"},
    "mail_":         {"icon": "mail",             "color": "#3B82F6"},
    "message":       {"icon": "message-circle",   "color": "#3B82F6"},
    "send_":         {"icon": "send",             "color": "#3B82F6"},
    "inbox_":        {"icon": "inbox",            "color": "#3B82F6"},
    "shield":        {"icon": "shield",           "color": "#8B5CF6"},
    "scan":          {"icon": "scan",             "color": "#3B82F6"},
    "atom":          {"icon": "atom",             "color": "#8B5CF6"},
    "dna":           {"icon": "dna",              "color": "#22C55E"},
    "flask":         {"icon": "flask-conical",    "color": "#3B82F6"},
    "award":         {"icon": "award",            "color": "#F59E0B"},
    "crown":         {"icon": "crown",            "color": "#F59E0B"},
    "gem":           {"icon": "gem",              "color": "#8B5CF6"},
    "coffee":        {"icon": "coffee",           "color": "#F59E0B"},
    "cake":          {"icon": "cake",             "color": "#F472B6"},
    "pizza":         {"icon": "pizza",            "color": "#F59E0B"},
    "cookie":        {"icon": "cookie",           "color": "#F59E0B"},
    "gift_":         {"icon": "gift",             "color": "#22C55E"},
}

# Now resolve names to codepoints
resolved = {}
missing = []
for key, info in sorted(EMOJIS.items()):
    name = info["icon"]
    if name in mapping:
        resolved[key] = {"char": mapping[name], "color": info["color"]}
    else:
        missing.append(name)

print(f"\nResolved: {len(resolved)}")
if missing:
    print(f"Missing icons: {set(missing)}")

# Print the final set
print("\n=== FINAL EMOJI SET ===")
for key, info in sorted(resolved.items()):
    cp = ord(info["char"])
    print(f'  "{key}": "\\u{cp:04x}",  # {info["color"]}')

# Save as JSON for reference
with open("whitebots.online/expanded_emojis.json", "w") as f:
    json.dump({k: {"codepoint": hex(ord(v["char"])), "color": v["color"]} for k, v in resolved.items()}, f, indent=2)
