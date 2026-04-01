# 👁️ Watcher Bot - Elite Activity & Engagement Manager

A state-of-the-art Discord bot designed for professional community management. It provides high-precision activity monitoring, automated game role distribution, and a gamified engagement system through a modern, configuration-driven UI.

## ✨ Key Features

### 🏆 Gamification & Rewards
- **Weekly Champions**: Automatically awards unique roles every Monday to the top performers:
  - **GodGamer (Hardcore)**: Most minutes spent in tracked games.
  - **GodGamer (Variety)**: Played the most diverse set of games.
  - **SpotiViber**: The most active music listener on the server.
  - **Sharing is Caring**: Most time spent streaming to the community.
  - **MemeLord**: Awarded for sharing the most media content (links, images, videos).
- **Hall of Fame**: Permanent recognition for users who win 5+ weekly championships.
- **Champion Log**: Detailed history and Hall of Fame views via `/champion_log`.
- **Modern Leaderboards**: Beautiful, icon-mapped `/top` (Weekly, Monthly, All-time) and `/me` profiles.

### 🛡️ Smart Activity Processing
- **ActivityProcessor**: Centralized business logic for point calculation and media detection.
- **Media Factory**: Earn bonus points for sharing YouTube, TikTok, images, or links.
- **Dynamic Multipliers**: Voice points are calculated based on participation tiers (Streaming, Camera on, etc.).
- **Server Veteran System**: Tracks tenure and calculates a **Loyalty Index** based on activity vs. time joined.
- **Auto Game Roles**: Dynamic role distribution based on what game you are currently playing.

### 🔗 Unified Identity (Alt & Mini Accounts)
- Link multiple Discord accounts to a single primary identity via `/link_alt`.
- Automatic aggregation of messages, reactions, voice time, and game playtime across all accounts.
- **Atomic Role Sync**: Inactivity and game roles are automatically synced across ALL linked identities.

### ⚡ Professional Infrastructure
- **Dynamic Help Menu**: Admin dashboard that automatically discovers all registered prefix and slash commands.
- **Localization Engine**: Full support for Hungarian and English, powered by centralized JSON locale files.
- **Icon Mapping**: Custom Discord application symbols can be mapped in `config.json` without touching the code.
- **Security Decorators**: Standardized role-based access control (`is_admin`, `is_tester`).

## 🚀 Setup & Installation

### 1. Prerequisites
- Python 3.10+
- SQLite3
- **Privileged Intents**: `Server Members`, `Presence`, `Message Content`, `Voice States`.

### 2. Configuration
- **[.env](file:///.env)**: Store your secret `DISCORD_TOKEN`.
- **[config.json](file:///config.json)**: Manage Role IDs, Channel IDs, Emojis, and Activity Thresholds.
- **[locales/](file:///locales/)**: Customize all bot responses in `hu.json` or `en.json`.

### 3. Running the Bot
```bash
pip install -r requirements.txt
python bot.py
```

## 🛠️ Command Suites (Suffix: `_elf`)

### 📊 Public Commands (Stats/Public Channels)
- `/top` - Explore the leaderboard with medals and tiers.
- `/me` - View your comprehensive profile card and veteran stats.
- `/champion_log` - View the weekly Hall of Fame and historical winners.
- `/server_analysis` - Visual heatmaps and charts of server activity.
- `/info` / `!info_elf` - General introduction and bot features.

### 🛡️ Management & Dev (Admin/Tester Channels)
- `/status_report` - Detailed audit of all members' activity and status.
- `/game_details` - Deep dive into statistics for a specific game (Export to TXT).
- `/membership_logs` - Export join/leave history logs.
- `/stream_history` - Review recorded community streaming sessions.
- `/link_alt` - Open the modal to link a secondary account.
- `/info_dev` / `!info_dev_elf` - Dynamic administrator dashboard.
- `!sync_elf` - Force synchronize all slash commands to Discord.

## ⚙️ Core Architecture
- **`db_manager.py`**: High-performance SQLite interaction with optimized indexing.
- **`core/activity_processor.py`**: The logic behind scoring, tiers, and media detection.
- **`core/messages.py`**: Localization and dynamic string formatting engine.
- **`cogs/`**: Modularized features (Admin, Stats, Champions, Games, Events).

---
*Built for communities that value engagement, transparency, and premium UI.*
