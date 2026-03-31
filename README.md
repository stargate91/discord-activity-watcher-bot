# 👁️ Watcher Bot - Elite Activity & Engagement Manager

A state-of-the-art Discord bot designed for professional community management. It provides high-precision activity monitoring, automated game role distribution, and a gamified engagement system through a modern, configuration-driven UI.

## ✨ Key Features

### 🏆 Gamification & Rewards
- **Weekly Champions**: Automatically awards unique roles every Monday to the top performers:
  - **GodGamer (Hardcore)**: Most minutes spent in games.
  - **GodGamer (Variety)**: Played the most diverse set of games.
  - **SpotiVibe**: Most active music listener.
  - **Sharing is Caring**: Most time spent streaming to the community.
- **Hall of Fame**: Permanent recognition for users who win 5+ weekly championships.
- **Modern Leaderboards**: Beautiful, icon-mapped `/top` (Weekly, Monthly, All-time) and `/me` profiles.

### 🛡️ Smart Activity Processing
- **ActivityProcessor**: Centralized business logic for point calculation and media detection.
- **Media Factory**: Earn bonus points for sharing YouTube, TikTok, images, or links.
- **Dynamic Multipliers**: Voice points are calculated based on participation tiers (Streaming, Camera on, etc.).
- **Server Veteran System**: Tracks tenure and calculates a **Loyalty Index** based on activity vs. time joined.

### 🔗 Unified Identity (Alt Linking)
- Link multiple Discord accounts to a single primary identity via `config.json`.
- Automatic aggregation of messages, reactions, voice time, and game playtime.
- **Atomic Role Sync**: Inactivity and game roles are automatically synced across ALL linked accounts.

### ⚡ Professional Infrastructure
- **Optimized for Scale**: Lazy-loading for leaderboards and targeted database queries ensure smooth performance for 1000+ member servers.
- **Spam Protection**: Configurable cooldowns on all public slash commands.
- **Localization Engine**: Dynamic support for Hungarian and English, driven by centralized JSON locale files.
- **Persistence**: Real-time session tracking (Voice/Games) that survives bot reboots.

## 🚀 Setup & Installation

### 1. Prerequisites
- Python 3.10+
- SQLite3
- **Privileged Intents**: `Server Members`, `Presence`, `Message Content`, `Voice States`.

### 2. Configuration
The bot is fully driven by a professional configuration system:
- **[.env](file:///.env)**: Store your secret `DISCORD_TOKEN`.
- **[config.json](file:///config.json)**: Manage Role IDs, Channel IDs, Emojis, Tiers, and Activity Thresholds.
- **[locales/](file:///locales/)**: Customize all bot responses in `hu.json` or `en.json`.

### 3. Running the Bot
```bash
pip install -r requirements.txt
python bot.py
```

## 🛠️ Command Suites

### 📊 Public Commands (Stats Channel)
- `/top [timeframe]` - Explore the leaderboard with medals and tiers.
- `/me` - View your comprehensive profile card, social connections, and veteran stats.
- `/server_analysis [type]` - Generate visual heatmaps and charts of server activity.

### 🛡️ Management Commands (Admin Channel)
- `/status_report` - Detailed audit of all members' activity and inactivity status.
- `/game_report` - Detailed analytics on game popularity and trends.
- `/membership_logs` - Export join/leave history to TXT.
- `/stream_history` - Review all recorded community streaming sessions.
- `/add_game` / `/remove_game` - Control the automatic game-role engine.

## ⚙️ Core Architecture
- **`db_manager.py`**: High-performance SQLite interaction with optimized indexing.
- **`core/activity_processor.py`**: The "brain" behind scoring and media detection.
- **`core/ui_utils.py`**: Dynamic icon-mapping and translation bridge.
- **`cogs/events.py`**: Event-driven architecture for real-time tracking and automation.

---
*Built for communities that value engagement and transparency.*
