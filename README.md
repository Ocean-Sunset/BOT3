# Eobot — Sovra 🐍

A multifunctional Discord bot built with Python, featuring a deep economy system, automated versioning, and an experimental insider program.

## 🚀 Key Features

- **Multifunctional Utilities**: Commands for server moderation, info gathering, and general utility.
- **Deep Economy System**: Includes XP leveling, coins, gems, a banking system, inventory management, and trophies.
- **Insider Program**: Access to experimental builds (codenamed **Mystralyn**) for early testing of upcoming features.
- **Automated Update Logic**: A custom version-checking system that handles major, medium, and small updates across components.
- **Web Dashboard**: Real-time status monitoring and control via a built-in Flask web portal.
- **Customization**: Support for server-specific prefixes and announcement settings.

## 🛠️ Technical Stack

- **Language**: Python 3.10+
- **Framework**: `discord.py`
- **Web**: `Flask` (for the dashboard)
- **Environment**: `python-dotenv` for configuration

## ⚙️ Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Ocean-Sunset/BOT3.git
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**:
   Create a `.env` file in the root directory (and `cli/`) with your bot token:
   ```env
   DISCORD_TOKEN=your_token_here
   ```

4. **Run the Bot**:
   ```bash
   python cli/brain.py
   ```

## ⚠️ Stability Notice
This bot is actively developed. **Insider builds** contain experimental code that may be unstable. If you encounter bugs, please report them using the `/crashreport` command.

---
*Created with ❤️ by th3_t1sm*
