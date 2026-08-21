r"""
Upload the white/transparent Prowl lucide emojis to the guild hosting them.

Tier-0 guilds have 50 static emoji slots, so this uploads exactly the 50 keys
the codebase actually renders (emoji_title/emoji_for callers + button emojis).
A full colored 129-icon set can still be generated with generate_emojis.py.

Usage:
    python whitebots.online\upload_emojis.py            # upload missing ones
    python whitebots.online\upload_emojis.py --force    # delete + recreate all
Output:
    whitebots.online/new_emoji_ids.json   (key -> new emoji id)
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EMOJI_DIR = os.path.join(HERE, "emojis")
ENV_PATH = os.path.join(ROOT, "cli", ".env.local")
OUT_JSON = os.path.join(HERE, "new_emoji_ids.json")

API = "https://discord.com/api/v10"
GUILD_ID = "1443186371341848713"  # Absolute Testing Server - bot must stay a member!

# The live set (50 = tier-0 slot cap). Keep in sync with EMBED_EMOJIS in cli/Ediscord/builders.py.
UPLOAD_KEYS = [
    # moderation / feedback
    "ban", "tempban", "kick", "mute", "unmute", "warn", "warning", "unban",
    "purge", "error", "info", "success", "shield", "anti_raid", "raid_detected",
    # leveling
    "level_up", "rank", "leaderboard",
    # welcomer / logging
    "welcome", "goodbye", "member", "members", "server", "channel", "role",
    "message", "mic", "bell", "bell_off", "sparkle", "bot",
    # tickets / verification
    "ticket", "ticket_open", "ticket_close", "verify", "verify_fail",
    "lock", "unlock", "check", "cross",
    # invites / social / misc
    "invite_join", "invite_stats", "invite_create", "global_chat",
    "save", "send", "settings", "bolt", "image", "music",
]

assert len(UPLOAD_KEYS) == len(set(UPLOAD_KEYS)), "duplicate keys"
assert len(UPLOAD_KEYS) <= 50, f"{len(UPLOAD_KEYS)} keys exceed tier-0 cap"


def load_token():
    with open(ENV_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("TOKEN") and "=" in line:
                tok = line.split("=", 1)[1].strip()
                return tok if tok.startswith("Bot ") else "Bot " + tok
    raise SystemExit("TOKEN not found in cli/.env.local")


TOKEN = load_token()


def api(method, path, payload=None):
    """Discord API call with 429 backoff. Returns parsed JSON."""
    data = None
    headers = {
        "Authorization": TOKEN,
        "User-Agent": "ProwlEmojiTool (https://prowlbot.xyz, 1)",
    }
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    for attempt in range(8):
        req = urllib.request.Request(API + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req) as r:
                body = r.read().decode()
                return json.loads(body) if body else None
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 1.0
                try:
                    wait = float(json.loads(e.read().decode()).get("retry_after", 1.0))
                except Exception:
                    pass
                print(f"    429 rate limited - sleeping {wait:.2f}s")
                time.sleep(wait + 0.25)
                continue
            raise
        except urllib.error.URLError as e:
            print(f"    network error ({e}) - retrying in 2s")
            time.sleep(2)
    raise SystemExit(f"giving up after retries: {method} {path}")


def main():
    force = "--force" in sys.argv
    existing = {e["name"]: e for e in api("GET", f"/guilds/{GUILD_ID}/emojis")}
    free_slots = max(0, 50 - len(existing))
    todo = [k for k in UPLOAD_KEYS if force or k not in existing]
    print(f"guild has {len(existing)} emojis, {free_slots} free slots -> uploading {len(todo)}")
    if len(todo) > free_slots:
        SystemExit(f"need {len(todo)} slots but only {free_slots} free - delete some first")

    mapping = {}
    if os.path.exists(OUT_JSON) and not force:
        try:
            mapping = json.load(open(OUT_JSON, encoding="utf-8"))
        except Exception:
            mapping = {}

    for i, key in enumerate(todo, 1):
        png = os.path.join(EMOJI_DIR, f"{key}.png")
        if not os.path.exists(png):
            print(f"[{i}/{len(todo)}] {key}: MISSING PNG - skipped")
            continue
        b64 = base64.b64encode(open(png, "rb").read()).decode()

        old = existing.get(key)
        if old and force:
            api("DELETE", f"/guilds/{GUILD_ID}/emojis/{old['id']}")
            print(f"[{i}/{len(todo)}] {key}: deleted old {old['id']}")

        emo = api("POST", f"/guilds/{GUILD_ID}/emojis",
                  {"name": key, "image": f"data:image/png;base64,{b64}"})
        mapping[key] = emo["id"]
        print(f"[{i}/{len(todo)}] {key}: created {emo['id']}")
        time.sleep(0.5)

    json.dump(mapping, open(OUT_JSON, "w", encoding="utf-8"), indent=2, sort_keys=True)
    print(f"\nsaved {len(mapping)} ids -> {OUT_JSON}")


if __name__ == "__main__":
    main()
