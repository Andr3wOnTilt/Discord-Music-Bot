# 🌙 Discord Bot Dashboard

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![discord.py](https://img.shields.io/badge/discord.py-2.3%2B-5865F2?style=for-the-badge&logo=discord&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D4?style=for-the-badge&logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-Custom%20EULA-red?style=for-the-badge)

**A professional Discord bot with a fully featured dark-themed GUI dashboard.**  
Built with Python, Tkinter, and discord.py — no browser required.

</div>

---

## ✨ Features

### 🖥️ Dashboard GUI
- Real-time statistics: Ping, Servers, Users, Uptime, CPU, RAM
- Live log console with color-coded output
- Start / Stop bot controls with status indicator
- Built with a Discord-native dark theme (`#2b2d31`, `#1e1f22`)

### 📝 Embed Builder
- Visual embed creator with live preview
- Support for title, description, color, footer, image, thumbnail, author, and custom fields
- Send embeds directly to any Discord channel from the dashboard

### 🎵 Music Bot
- YouTube playback via `yt-dlp`
- Queue system with loop, volume control, skip, and more
- FFmpeg-based audio streaming

### 🛡️ Administration
- Moderation commands: kick, ban, unban, mute, purge, warn
- Server info, user info, bot info
- Interactive embed builder via Discord chat (`!embed`)

### 🌍 Multilingual Interface
- English (default)
- Italiano
- Polski

---

## 📸 Screenshots

> *Coming soon*

---

## 🚀 Getting Started

### Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.10 or higher |
| FFmpeg | Any recent release |

### Installation

**1. Clone the repository**
```bash
git clone https://github.com/Andr3wOnTilt/discord-bot-dashboard.git
cd discord-bot-dashboard
```

**2. Install Python dependencies**
```bash
pip install discord.py[voice] yt-dlp psutil PyNaCl
```

**3. Install FFmpeg**

Option A — via winget (recommended):
```bash
winget install Gyan.FFmpeg
```

Option B — manual: download from [ffmpeg.org](https://ffmpeg.org/download.html), extract, and add `bin/` to your system PATH.  
Option C — place `ffmpeg.exe` directly in the project folder.

**4. Run the dashboard**
```bash
python main.py
```

On first launch, a **Setup Wizard** will guide you through the initial configuration (bot name, prefix, token). A **License Agreement** must be accepted before the app configures itself.

---

## ⚙️ Configuration

Settings are stored in `bot_config.json` (created automatically after setup).

| Key | Description | Default |
|---|---|---|
| `bot_name` | Display name for the dashboard | `MyBot` |
| `prefix` | Command prefix | `!` |
| `token` | Discord bot token | — |
| `status` | Bot online status (`online` / `idle` / `dnd`) | `online` |
| `activity` | Activity text shown in Discord | `!help` |
| `log_level` | Logging verbosity (`DEBUG` / `INFO` / `WARNING` / `ERROR`) | `INFO` |
| `lang` | Interface language (`en` / `it` / `pl`) | `en` |

> ⚠️ You must enable **Message Content Intent** and **Server Members Intent** in the [Discord Developer Portal](https://discord.com/developers/applications) under your app's Bot settings.

---

## 🎵 Music Commands

| Command | Description |
|---|---|
| `!play <query>` | Play or queue a song from YouTube |
| `!pause` | Pause playback |
| `!resume` / `!r` | Resume playback |
| `!skip` / `!s` | Skip the current song |
| `!stop` | Stop and disconnect the bot |
| `!queue` / `!q` | Show the current queue |
| `!volume <0-100>` | Set volume |
| `!loop` | Toggle loop mode |
| `!nowplaying` / `!np` | Show currently playing song |
| `!clear_queue` / `!cq` | Clear the queue |
| `!join` | Join your voice channel |
| `!leave` / `!dc` | Disconnect the bot |

---

## 🛡️ Moderation Commands

| Command | Description |
|---|---|
| `!kick @member` | Kick a member |
| `!ban @member` | Ban a member |
| `!unban <tag>` | Remove a ban |
| `!mute @member <minutes>` | Timeout a member |
| `!unmute @member` | Remove a timeout |
| `!purge <n>` | Delete n messages |
| `!warn @member` | Send a warning via DM |

---

## 📝 Utility Commands

| Command | Description |
|---|---|
| `!embed` | Interactive embed builder in chat |
| `!quickembed Title\|Desc\|Color` | Create a quick embed |
| `!serverinfo` | Show server information |
| `!userinfo [@member]` | Show user information |
| `!botinfo` | Show bot information |
| `!ping` | Show bot latency |
| `!announce #channel` | Send an announcement embed |

---

## 🏗️ Building a Standalone Executable

Place all files in the project folder and run:

```
build.bat
```

The script will:
1. Check Python and install all dependencies automatically
2. Locate FFmpeg and bundle it into the executable
3. Compile everything into a single `build/dist/DiscordBotDashboard.exe`

The resulting `.exe` runs on **any Windows PC** without requiring Python or any dependencies.

> ℹ️ The build script requires `_build_prepare.py` and `_build_run.py` to be present alongside `build.bat`.

---

## 📁 Project Structure

```
discord-bot-dashboard/
│
├── main.py                   # Dashboard GUI + bot lifecycle
├── i18n.py                   # Translations (EN / IT / PL)
├── musicManager.py           # Music bot cog
├── administrationManager.py  # Admin & moderation cog
│
├── build.bat                 # Build launcher
├── _build_prepare.py         # Build configuration helper
├── _build_run.py             # PyInstaller runner
│
└── bot_config.json           # Generated on first run (not committed)
```

---

## 🌍 Adding a New Language

1. Open `i18n.py`
2. Copy the `"en"` block and add a new key (e.g. `"de"`)
3. Translate all values
4. Add the new language option in the Setup Wizard and Settings page in `main.py`

---

## 📄 License

This project is governed by a **custom End User License Agreement (EULA)**.  
See the full license text displayed within the application on first launch.

Key points:
- ✔ Free to use with the official build, provided credits are maintained
- ✔ Third parties may modify and redistribute, with attribution
- ✘ The official build may not be redistributed without authorization
- ⚠ Unauthorized redistribution renders the EULA **VOID**

© **Andr3wOnTilt** — All rights reserved.


---

<div align="center">
  Made with ❤️ by <strong>Andr3wOnTilt</strong>
</div>
