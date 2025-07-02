# note to self: THIS FILE DOES NOT USE EDISCORD MODULE
# DO NOT MOVE THE def is valid_python OUT OF THIS FILE.
# ----------------------- IMPORTS ---------------------------
import discord
from discord.ext import commands
import os
import json
import re
import difflib
from Ediscord import variables
import ast
from datetime import datetime

# -------------------- DEFINITIONS -------------------------------
def is_valid_python(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False

def log_super_command(flag: str, name: str, args: str, code: str):
    os.makedirs(os.path.dirname(variables.LOG_FILE), exist_ok=True)
    with open(variables.LOG_FILE, "a") as f:
        f.write(f"[{datetime.now().isoformat()}] FLAG: {flag} | NAME: {name} | ARGS: {args} | CODE:\n{code}\n\n")
class SuperCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="super")
    @commands.is_owner()
    async def super_command(self, ctx, flag: str, name: str, args: str = "", *, content: str = ""):
        if flag == "A":
            await self.add_command(ctx, name, args, content)
        elif flag == "EA":
            await self.add_event(ctx, name, args, content)
        elif flag == "E":
            await self.edit_function(ctx, name, args, content, is_event=False)
        elif flag == "EE":
            await self.edit_function(ctx, name, args, content, is_event=True)
        elif flag == "J":
            await self.edit_json(ctx, name, args, content)
        else:
            await ctx.send("❌ Unknown flag.")
            
        # Inline test
        if flag in ("A", "E", "EA", "EE"):
            temp_code = f"async def {name}({args}):\n" + "\n".join(f"    {line}" for line in content.split("\\n"))
            if not is_valid_python(temp_code):
                await ctx.send("❌ Syntax error in provided code. Aborting.")
                return

    async def add_command(self, ctx, name, args, code):
        func = self.format_function("command", name, args, code)
        await self.append_to_cog("super.py", func)
        await ctx.send(f"✅ Command `{name}` added to `super.py`.")

    async def add_event(self, ctx, name, args, code):
        func = self.format_function("event", name, args, code)
        await self.append_to_cog("super.py", func)
        await ctx.send(f"✅ Event `{name}` added to `super.py`.")

    async def edit_function(self, ctx, name, args, code, is_event):
        files = [f for f in os.listdir(variables.COGS_DIR) if f.endswith(".py")]
        target_func = f"async def {name}"
        replacement = self.format_function("event" if is_event else "command", name, args, code)

        matches = []
        for file in files:
            path = os.path.join(variables.COGS_DIR, file)
            with open(path, "r") as f:
                content = f.read()
            if target_func in content:
                pattern = rf"@.*?\nasync def {re.escape(name)}.*?\n((?:    .*\n?)*)"
                new_content = re.sub(pattern, replacement + "\n", content, flags=re.DOTALL)
                with open(path, "w") as f:
                    f.write(new_content)
                await ctx.send(f"✅ Function `{name}` updated in `{file}`.")
                return
            else:
                all_funcs = re.findall(r"async def (\w+)", content)
                matches.extend(all_funcs)

        close_matches = difflib.get_close_matches(name, matches, n=3)
        if close_matches:
            await ctx.send(f"❌ Function `{name}` not found. Did you mean: `{', '.join(close_matches)}`?")
        else:
            await ctx.send("❌ Function not found in any cog.")

    async def edit_json(self, ctx, file, key_path, value):
        file_path = os.path.join(variables.DATA_DIR, f"{file}.json")
        if not os.path.exists(file_path):
            await ctx.send(f"❌ `{file}.json` not found.")
            return

        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            keys = key_path.split(".")
            ref = data
            for k in keys[:-1]:
                ref = ref.setdefault(k, {})
            ref[keys[-1]] = json.loads(value) if value.startswith(('{', '[', '"')) else value

            with open(file_path, "w") as f:
                json.dump(data, f, indent=4)

            await ctx.send(f"✅ JSON `{file}.json` updated.")
        except Exception as e:
            await ctx.send(f"❌ Failed to edit JSON: `{e}`")

    def format_function(self, kind, name, args, code):
        header = "@commands.command()\n" if kind == "command" else "@commands.Cog.listener()\n"
        signature = f"async def {name}({args}):\n"
        body = "\n".join(f"    {line}" for line in code.split("\\n"))
        return f"{header}{signature}{body}\n"

    async def append_to_cog(self, filename, code_block):
        path = os.path.join(variables.COGS_DIR, filename)
        if not os.path.exists(path):
            with open(path, "w") as f:
                f.write("from discord.ext import commands\n\n")
                f.write("class SuperCog(commands.Cog):\n")
                f.write("    def __init__(self, bot):\n        self.bot = bot\n\n")
                f.write(code_block)
                f.write("\n\ndef setup(bot):\n    bot.add_cog(SuperCog(bot))\n")
        else:
            with open(path, "a") as f:
                f.write("\n" + code_block)

async def setup(bot):
    await bot.add_cog(SuperCommands(bot))
