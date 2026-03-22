# 👁️ Watcher Bot - Activity & Role Manager

A powerful Discord bot designed to monitor user activity, manage roles for inactive/returning members, and provide a competitive leaderboard system.

## ✨ Features

-   **Activity Tracking**: Logs messages, reactions, and voice channel minutes.
-   **Live Voice Tracking**: Accurately tracks voice session minutes even across channel moves and bot restarts.
-   **Inactivity Management**:
    -   **Stage 1 (Inactive)**: Automatically assigns a role to users who haven't been active for a set period (e.g., 14 days).
    -   **Stage 2 (Returning)**: Automatically assigns a role to returning users who show activity after being in Stage 1.
-   **Leaderboard System**:
    -   **Points**: Messages (10 pts), Reactions (5 pts), Voice (2 pts/minute).
    -   **Timeframes**: Weekly, Monthly, and All-time stats.
    -   **Live Data**: Current voice sessions are included in real-time scores.
-   **Auto Game Roles**: Automatically assigns "Player: {Game}" roles based on user's current activity (e.g., Playing League of Legends).
-   **Admin Tools**:
    -   Detailed status reports in TXT format.
    -   Logging of all game role assignments.
    -   Manual slash command synchronization.

## 🚀 Setup & Installation

### 1. Prerequisites
-   Python 3.8+
-   Discord Bot Token ([Developer Portal](https://discord.com/developers/applications))
-   **Required Intents**: `Server Members`, `Presence`, `Message Content`, `Voice States`.

### 2. Configuration
Create a `.env` file in the root directory:

```env
DISCORD_TOKEN=your_token_here
STAGE_1_ROLE_ID=id_of_inactive_role
STAGE_2_ROLE_ID=id_of_returning_role
ADMIN_CHANNEL_ID=id_of_admin_channel
STAGE_1_DAYS=14
STAGE_2_DAYS=21
CHECK_INTERVAL_HOURS=12
```

### 3. Installation
```bash
pip install -r requirements.txt
```

### 4. Running the Bot
```bash
python bot.py
```

## 🛠️ Commands

### 👤 User Commands (Slash)
-   `/top [timeframe: weekly/monthly/alltime]` - Display the top 10 most active members.

### 🛡️ Admin Commands (Slash - Admin Channel only)
-   `/status_report` - Generates a detailed TXT report of all members' activity and role status.
-   `/game_role_report` - Downloads the full history of game role assignments (`role_log.txt`).

### ⚙️ Utility Commands (Prefix)
-   `!sync` - Immediately synchronizes slash commands to the current server (Bot Owner only).

## 📄 Database & Logs
-   `activity.db`: SQLite database storing all user stats.
-   `role_log.txt`: Text log of all automatic game role assignments.
-   `.gitignore`: Properly configured to protect your data and secrets.
