# 👁️ Watcher Bot - Activity & Role Manager

A professional Discord bot designed for high-precision activity monitoring, automatic game role management, and incentivizing server engagement through a clean, modern leaderboard system.

## ✨ Features

-   **Unified Identity Tracking (Alt Linking)**:
    -   Link multiple Discord accounts (alts) to a single primary identity via `config.json`.
    -   Messages, reactions, voice time, and game playtime are automatically aggregated to the main account.
    -   Alts are hidden from top lists; `/me` on any linked account shows the unified primary stats.
-   **Atomic Role Synchronization**:
    -   **Inactivity Roles**: "Inactive" and "Returning" roles are automatically synced across all linked accounts of a user.
    -   **Game Roles**: When a user starts a game (e.g., *Player: Minecraft*), the role is assigned to ALL their linked accounts simultaneously.
-   **Persistent Voice & Game Tracking**:
    -   Real-time session tracking that persists across channel moves, game restarts, and bot reboots via SQLite.
    -   Smart voice logic: If multiple linked accounts are in voice, time is only counted once. Continuous tracking if a user switches between accounts.
-   **Configurable Restrictions**:
    -   Dedicated **Stats Channel** for public commands (`/top`, `/me`).
    -   Dedicated **Admin Channel** for reports and system management.
-   **Multilingual Hungarian Support**: All user-facing messages are centralized and localized.

## 🚀 Setup & Installation

### 1. Prerequisites
-   Python 3.10+
-   Discord Bot Token ([Developer Portal](https://discord.com/developers/applications))
-   **Privileged Intents**: `Server Members`, `Presence`, `Message Content`, `Voice States`.

### 2. Configuration
The bot uses a hybrid approach to separate secrets from settings:

1.  **[.env](file:///.env)**:
    ```env
    DISCORD_TOKEN=your_token_here
    ```
2.  **[config.json](file:///config.json)**: Edit this file to manage all your Role IDs, Channel IDs, point values, and inactivity thresholds.
    -   **`primary_accounts`**: Map alt IDs to primary IDs here for unified tracking.

### 3. Running the Bot
```bash
pip install -r requirements.txt
python bot.py
```

## 🛠️ Commands

### 📊 Stats Commands (Stats Channel only)
-   `/top [timeframe]` - Display the top 10 most active members (Weekly, Monthly, All-time).
-   `/me` - Display your personal activity profile, ranking, and **Top 3 Games by Playtime**.

### 🛡️ Admin Commands (Admin Channel only)
-   `/status_report` - Generates a detailed TXT report of all members' activity.
-   `/game_stats_report` - Generates a report on the popularity of different games in the server.
-   `/game_role_report` - Downloads the history of all automatic game role assignments.
-   `/add_game` / `/remove_game` - Manage which game franchises the bot monitors.
-   `/reset_database` - Wipes all activity data while keeping configuration intact.

### ⚙️ System Commands
-   `!sync` / `/sync` - Manually propagate slash commands. Use `!sync copy` for the first run! (Owner only).

## 📄 Data Management
-   **`activity.db`**: SQLite database storing all user stats, active sessions, and history.
-   **`core/messages.py`**: Central repository for all Hungarian text strings.
-   **`cogs/`**: The core logic split into specialized modules (Stats, Events, Admin, Games).
