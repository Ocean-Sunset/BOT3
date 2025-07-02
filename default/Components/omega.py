import discord
from discord.ext import commands
import os
import json
from datetime import datetime
import difflib
import shutil

DATA_DIR = "data"
LOG_FILE = "logs/omega_command.log"
BACKUP_DIR = "backups"

class Omega(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        os.makedirs(BACKUP_DIR, exist_ok=True)

    @commands.command(name="omega")
    @commands.is_owner()
    async def omega(self, ctx, flag: str, file: str = "", key_path: str = "", *, value: str = ""):
        if flag.upper() == "S":
            await self.show(ctx, file, key_path)
        elif flag.upper() == "LS":
            await self.list_keys(ctx, file, key_path)
        elif flag.upper() in ["=", "+", "DEL"]:
            await self.edit(ctx, file, key_path, flag, value)
        elif flag.upper() == "UNDO":
            await self.undo(ctx, file)
        elif flag.upper() == "LOG":
            await self.show_log(ctx, int(file) if file and file.isdigit() else 5)
        elif flag.upper() == "BAK":
            await self.list_backups(ctx, file)
        elif flag.upper() == "RESTORE":
            await self.restore_backup(ctx, file)
        else:
            await ctx.send("❌ Unknown omega flag.")

    async def show(self, ctx, file, key_path):
        file_path = os.path.join(DATA_DIR, f"{file}.json")
        if not os.path.exists(file_path):
            await ctx.send(f"❌ File `{file}.json` not found.")
            return

        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            display_data = data
            if key_path:
                keys = key_path.split(".")
                for k in keys:
                    if isinstance(display_data, dict) and k in display_data:
                        display_data = display_data[k]
                    else:
                        all_keys = self._get_all_nested_keys(data)
                        matches = difflib.get_close_matches(key_path, all_keys, n=3)
                        if matches:
                            await ctx.send(f"❌ Key not found. Did you mean: {', '.join(matches)}?")
                        else:
                            await ctx.send(f"❌ Key `{key_path}` not found.")
                        return

            json_output = json.dumps(display_data, indent=4)
            if len(json_output) > 1900:
                await ctx.send(f"```json\n{json_output[:1800]}...\n```")
            else:
                await ctx.send(f"```json\n{json_output}\n```")
        except Exception as e:
            await ctx.send(f"❌ Error reading file: {e}")

    async def list_keys(self, ctx, file, key_path):
        path = os.path.join(DATA_DIR, f"{file}.json")
        if not os.path.exists(path):
            await ctx.send(f"❌ File `{file}.json` not found.")
            return
        try:
            with open(path, "r") as f:
                data = json.load(f)

            target = data
            if key_path:
                for k in key_path.split("."):
                    if isinstance(target, dict) and k in target:
                        target = target[k]
                    else:
                        await ctx.send(f"❌ Invalid key path `{key_path}`.")
                        return

            if isinstance(target, dict):
                keys = ", ".join(target.keys()) or "(empty)"
                await ctx.send(f"🔑 Keys in `{key_path or 'root'}`: `{keys}`")
            else:
                await ctx.send("❌ Target is not a dictionary.")
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    async def edit(self, ctx, file, key_path, op, value):
        path = os.path.join(DATA_DIR, f"{file}.json")
        if not os.path.exists(path):
            await ctx.send(f"❌ File `{file}.json` not found.")
            return

        self._backup_file(path)

        try:
            with open(path, "r") as f:
                data = json.load(f)

            keys = key_path.split(".")
            ref = data
            for k in keys[:-1]:
                ref = ref.setdefault(k, {})

            last_key = keys[-1]
            old_value = ref.get(last_key, None)
            action = ""

            if op == "=":
                ref[last_key] = self._parse_value(value)
                action = f"Set `{key_path}` = `{ref[last_key]}`"
            elif op == "+":
                try:
                    ref[last_key] = float(ref.get(last_key, 0)) + float(value)
                except (ValueError, TypeError):
                    await ctx.send(f"❌ Cannot add `{value}` to `{key_path}` because it's not a number.")
                    return
            elif op.upper() == "DEL":
                if last_key in ref:
                    del ref[last_key]
                    action = f"Deleted `{key_path}`"
                else:
                    await ctx.send(f"⚠️ Key `{key_path}` not found.")
                    return

            with open(path, "w") as f:
                json.dump(data, f, indent=4)

            self._log(ctx.author, file, key_path, op, value, old_value)
            await ctx.send(f"✅ {action}")

        except Exception as e:
            await ctx.send(f"❌ Error editing JSON: {e}")

    async def show_log(self, ctx, count=5):
        if not os.path.exists(LOG_FILE):
            await ctx.send("❌ Log file not found.")
            return
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()[-count:]
            await ctx.send("```\n" + "".join(lines)[-1900:] + "\n```")

    async def list_backups(self, ctx, file):
        backups = [f for f in os.listdir(BACKUP_DIR) if f.startswith(file)]
        if not backups:
            await ctx.send("❌ No backups found.")
            return
        await ctx.send("🗂 Backups:\n```\n" + "\n".join(backups[-10:]) + "\n```")

    async def restore_backup(self, ctx, filename):
        backup_path = os.path.join(BACKUP_DIR, filename)
        if not os.path.exists(backup_path):
            await ctx.send("❌ Backup not found.")
            return
        if not filename.endswith(".bak.json"):
            await ctx.send("❌ Invalid backup file format.")
            return
        try:
            file_name = filename.split(".")[0] + ".json"
            dest = os.path.join(DATA_DIR, file_name)
            shutil.copy2(backup_path, dest)
            await ctx.send(f"✅ Restored `{file_name}` from backup.")
        except Exception as e:
            await ctx.send(f"❌ Failed to restore: {e}")

    async def undo(self, ctx, file):
        # Use latest backup
        backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith(file)], reverse=True)
        if not backups:
            await ctx.send("❌ No backups found for undo.")
            return
        latest = backups[0]
        await self.restore_backup(ctx, latest)

    def _parse_value(self, val):
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            if val.lower() in ("true", "false"):
                return val.lower() == "true"
            elif val.lower() == "null":
                return None
            try:
                return int(val)
            except:
                try:
                    return float(val)
                except:
                    return val

    def _log(self, user, file, key, op, value, old_value=None):
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            timestamp = datetime.utcnow().isoformat()
            f.write(f"[{timestamp}] {user} | {file}.json | {key} {op} {value} (was: {old_value})\n")

    def _get_all_nested_keys(self, data, current_path=""):
        keys = []
        if isinstance(data, dict):
            for k, v in data.items():
                full_key = f"{current_path}.{k}" if current_path else k
                keys.append(full_key)
                if isinstance(v, dict):
                    keys.extend(self._get_all_nested_keys(v, full_key))
        return keys

    def _backup_file(self, path):
        filename = os.path.basename(path).replace(".json", "")
        timestamp = datetime.utcnow().isoformat().replace(":", "-")
        backup_path = os.path.join(BACKUP_DIR, f"{filename}.{timestamp}.bak.json")
        shutil.copy2(path, backup_path)

async def setup(bot):
    await bot.add_cog(Omega(bot))
