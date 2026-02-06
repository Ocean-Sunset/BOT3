import json
import time

DATA_FILE = "user_data.json"  # change this to your actual file path
LEVEL_CAP = 20
RESET_LEVEL = 20


def fix_levels():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    modified = False

    for user_id, user_data in data.items():
        level = user_data.get("level")

        if isinstance(level, int) and level > LEVEL_CAP:
            print(f"[FIX] User {user_id}: level {level} → {RESET_LEVEL}")
            user_data["level"] = RESET_LEVEL
            modified = True
        else:
            print(f"[NO FIX] User {user_id}: level {level}, good")

    if modified:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print("✅ Levels fixed and file saved.")
    else:
        print("ℹ️ No levels needed fixing.")


if __name__ == "__main__":
    fix_levels()
