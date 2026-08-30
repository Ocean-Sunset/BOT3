# Prowl

A multifunctional Discord bot with a web dashboard, built with Python and discord.py.

## Features

- **Moderation** - ban, kick, mute, warn, autoMod, raid protection
- **Leveling & XP** - message XP, voice XP, leaderboard, role rewards
- **AI** - chat, image generation, multi-provider (OpenAI, Groq, OpenRouter)
- **Giveaways** - timed giveaways with role/XP requirements
- **AFK & Reminders** - away status, timed reminders
- **Tickets** - support ticket system with panels
- **Verification** - CAPTCHA-based member verification
- **Global Chat** - cross-server message relay
- **Welcomer** - join/leave messages, auto-roles
- **Invite Tracker** - track who invites whom
- **Social Alerts** - monitor social media links
- **Automation Engine** - custom trigger/action rules

## Tech

- **Bot**: Python 3.9+, discord.py 2.7.x, Turso/libSQL
- **Website**: FastAPI, Vercel, Turso
- **DB**: Turso (libSQL over HTTP)

## Setup

```bash
git clone https://github.com/Ocean-Sunset/BOT3.git
cd BOT3
pip install -r cli/requirements.txt
```

Create `cli/.env.local`:
```env
TOKEN=your_bot_token
DATABASE_URL=libsql://your-turso-url
TURSO_AUTH_TOKEN=your_token
```

Run:
```bash
python cli/start.py
```

## Website Dashboard

The web dashboard lives in `website/` and manages server settings via OAuth2.

```bash
cd website
pip install -r requirements.txt
uvicorn api.index:app --reload
```

## Links

- [Invite Prowl](https://discord.com/oauth2/authorize?client_id=1323734010345689189)
- [Dashboard](https://prowlbot.xyz)
