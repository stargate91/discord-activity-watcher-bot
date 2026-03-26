class Messages:
    # These are the lists of words for different languages (HU is Hungarian, EN is English)
    _HU = {
        "LB_TITLE_WEEKLY": "Heti Top 10",
        "LB_TITLE_MONTHLY": "Havi Top 10",
        "LB_TITLE_ALLTIME": "Összesített Top 10",
        "LB_TITLE_DEFAULT": "Top 10",
        "LB_SHARED_BY": "📊 **{user}** megosztotta ezt a ranglistát:",
        "LB_EMPTY": "*Nincs elég adat az időszakhoz... Legyél te az első!* 🚀",
        "LB_UNKNOWN_USER": "Ismeretlen ({id})",
        "LB_POINTS": "pont",
        "LB_FOOTER_POINTS": "### Üzenet 10 | Reakció 5 | Voice 2/perc",
        "BTN_WEEKLY": "Heti",
        "BTN_MONTHLY": "Havi",
        "BTN_ALLTIME": "Összesített",
        "BTN_MY_RANK": "Saját helyezésem",
        "BTN_SHARE": "Megosztás",
        "DESC_ME": "Saját statisztikáid megtekintése.",
        "PROFILE_SHARED_BY": "📊 **{user}** megosztotta a profilját:",
        "PROFILE_RANK": "Helyezés",
        "PROFILE_SUBTITLE": "Összesített profilod a szerveren.",
        "SECTION_ACTIVITY": "### 📊 Aktivitás",
        "SECTION_STATS": "### 📈 Statisztikák",
        "SECTION_COMMUNITY": "### 🤝 Közösség (30 nap)",
        "SECTION_GAMES": "### 🎮 Legutóbbi játékok",
        "STAT_TOTAL_SCORE": "**Összpontszám:** ### **{points}**",
        "STAT_DETAILS": "**Üzenetek:** `{msg}` | **Reakciók:** `{reac}` | **Voice:** `{voice}p`",
        "STAT_LAST_ACTIVE": "**Utoljára aktív:** `{time}`",
        "STAT_DAILY_AVG": "**Napi átlag (30 nap):** `{avg:.2f} üzenet/nap`",
        "SOCIAL_FAV_ROOM": "**Kedvenc szoba:** <#{id}>",
        "SOCIAL_FAV_EMOJI": "**Kedvenc emoji:** {emoji}",
        "SOCIAL_MAIN_TARGET": "**Fő célpont:** <@{id}>",
        "SOCIAL_BEST_FRIEND": "**Best Friend (Voice):** <@{id}>",
        "SOCIAL_FAV_ROOM_STATIC": "**Kedvenc szoba:** {name}",
        "SOCIAL_MAIN_TARGET_STATIC": "**Fő célpont:** {name}",
        "SOCIAL_BEST_FRIEND_STATIC": "**Best Friend (Voice):** {name}",
        "ERR_NO_DATA": "Még nincs adatod az adatbázisban. Írj pár üzenetet előbb!",
        "ERR_NO_DATA_PERIOD": "Sajnos ebben az időszakban még nincs rögzített adatod.",
        "ERR_STATS_CHANNEL": "Ezt a parancsot csak a <#{id}> szobában használhatod!",
        "ERR_ADMIN_ONLY": "Ez a parancs csak az admin csatornában használható: <#{id}>",
        "SUCCESS_SHARED": "Sikeresen megosztva a csatornán! ✅",
        "REPORT_GEN_STATUS": "Status report generálása...",
        "REPORT_GEN_ROLE": "Játékos-rang napló generálása...",
        "REPORT_EMPTY_HISTORY": "Még nincs bejegyzés a naplóban.",
        "GAME_ADDED": "✅ Hozzáadva: Ha a névben szerepel: `{name}`, a rang ez lesz: `Player: {suffix}`",
        "GAME_REMOVED": "🗑️ `{name}` eltávolítva a figyelési listából.",
        "GAME_LIST_EMPTY": "Nincsenek figyelt játékok.",
        "GAME_LIST_TITLE": "🎮 Figyelt játékok listája",
        "GAME_REPORT_GEN": "Riport generálása...",
        "GAME_REPORT_EMPTY": "Nincsenek adatok a választott időszakhoz.",
        "GAME_REPORT_DONE": "📊 Elkészült a(z) `{tf}` játék riport ({count} különböző játék).",
        "DB_RESET_SUCCESS": "✅ Az adatbázis sikeresen kiürítve! Minden aktivitási adat törölve lett.",
        "DB_RESET_ERROR": "❌ Hiba történt a törlés során: {e}",
        "REPORT_TITLE_HEADER": "--- REPORT: {guild} ---\nGen: {now}\nUser                      | Stat         | M    | R    | V    | Details",
        "REPORT_STAGE_1": "Stage 1",
        "REPORT_STAGE_2": "Stage 2",
        "REPORT_STAGE_NORMAL": "Normal",
        "REPORT_INACTIVE": "Inaktív",
        "REPORT_S2_RETURN": "S2-ből: {days} nap",
        "REPORT_S1_LIMIT": "S1-ig: {days} nap",
        "ROLE_LOG_TITLE": "--- JÁTÉKOS-RANG NAPLÓ: {guild} ---\nGen: {now}\nTimestamp            | User                      | Státusz    | Role",
        "ROLE_LOG_REMOVED": "ELVÉVE",
        "ROLE_LOG_ADDED": "ADVA",
        "GAME_POP_TITLE": "--- JÁTÉK NÉPSZERŰSÉGI RIPORT ({tf}) ---",
        "GAME_POP_MONTHLY": "HAVI",
        "GAME_POP_ALLTIME": "ÖSSZESÍTETT",
        "GAME_POP_GEN": "Generálva: {now}",
        "GAME_POP_HEADER": "Játék neve                          | Jótekosok | Össz. perc",
        "PRESENCE_WATCHING": "Figyelem a lazsálókat... 🤫",
        
        "CMD_TOP_DESC": "[#{stats_id}] Mutatja a heti, havi vagy összesített toplistát.",
        "CMD_TOP_TF_DESC": "Válassz időszakot (weekly, monthly, alltime)",
        "CMD_ME_MEMBER_DESC": "[#{stats_id}] Saját statisztikáid megtekintése.",
        "CMD_ADD_GAME_DESC": "[#{admin_id}] Új játék hozzáadása az automata rangosztáshoz.",
        "CMD_ADD_GAME_NAME_DESC": "A játék nevének egy része (pl: Minecraft)",
        "CMD_ADD_GAME_SUFFIX_DESC": "A rang vége (példa: 'Minecraft' -> 'Player: Minecraft')",
        "CMD_REMOVE_GAME_DESC": "[#{admin_id} + @&{role_id}] Játék eltávolítása a listából.",
        "CMD_REMOVE_GAME_NAME_DESC": "A pontos keresési kulcsszó (pl: Minecraft)",
        "CMD_LIST_GAMES_DESC": "[#{admin_id}] Az összes figyelt játék listázása.",
        "CMD_GAME_REPORT_DESC": "[#{admin_id}] Játék népszerűségi riport generálása .txt-ben.",
        "CMD_GAME_REPORT_TF_DESC": "Válasz: alltime (összes) vagy monthly (e havi)",
        "CMD_STATUS_REPORT_DESC": "[#{admin_id}] Generál egy részletes TXT jelentést.",
        "CMD_GAME_ROLE_REPORT_DESC": "[#{admin_id}] Letölti a játékos-rang kiosztások naplóját.",
        "CMD_RESET_DB_DESC": "[#{admin_id} + @&{role_id}] MINDEN aktivitási adat végleges törlése.",
        "CMD_SYNC_DESC": "[#{admin_id} + @&{role_id}] Slash parancsok manuális szinkronizálása.",
        "CMD_SYNC_MODE_DESC": "Válassz: guild (ebbe a szerverbe), global (mindenhova), copy (globális másolása ide)",
        "ERR_STATS_LOAD": "❌ Hiba történt a statisztikák betöltésekor: {e}",
        "ERR_OWNER_ONLY": "Csak a bot tulajdonosa használhatja ezt.",
        "CMD_CLEAR_DONE": "✅ Minden regisztrált parancs (globális és szerver) törölve lett. Most már használhatod a {cmd} parancsot a frissítéshez.",
        "INFO_TITLE": "{bot_name} - Ismertető",
        "INFO_DESC": "Szia! Én egy aktivitásfigyelő bot vagyok. Követem a szerveren az üzeneteidet, reakcióidat és a voice csatornákban töltött idődet, amikből pontokat gyűjthetsz!",
        "INFO_FEATURES_TITLE": "### 🚀 Funkciók & Parancsok",
        "INFO_FEATURES_DESC": "• `/top` - Nézd meg a szerver legaktívabb tagjait.\n• `/me` - Nézd meg a saját részletes statisztikáidat.\n• **Automata rangok** - Egyedi rangok a kedvenc játékaidhoz!\n• **Inaktivitás** - Maradj aktív, hogy elkerüld a {role} rangot!",
        "INFO_FOOTER": "Használd a parancsokat a {channel} csatornán!",
        "INFO_DEV_TITLE": "🛠️ Adminisztrátori Parancslista",
        "INFO_DEV_PREFIX": "### ⌨️ Prefix parancsok (Suffix: `{suffix}`)\n",
        "INFO_DEV_SLASH": "\n### ⚡ Slash parancsok\n",
        "CMD_INFO_DEV_DESC": "[#{admin_id}] Kilistázza az összes parancsot az adminoknak.",
        "CMD_INFO_DESC": "[#{stats_id}] Általános ismertető a botról.",
        "TECH_SYNC": "A `bot.tree.sync()` hívását végzi. Frissíti a / parancsok metaadatait a Discord szerverein.",
        "TECH_RESET": "Véglegesen törli a `stats`, `role_history` és `game_stats` táblákat. Nem visszavonható.",
        "TECH_ADD_GAME": "Új regex mintát ment a `tracked_games` táblába, majd frissíti a tracker gyorsítótárát.",
        "TECH_STATUS": "Lekéri az összesített adatokat a DB-ből, Voice-offsetet számol, és .txt fájlt generál.",
        "TECH_GAME_REPORT": "Összegzi a `game_stats` és `tracked_games` táblákat a megadott időszakra.",
        "ERR_STATS_NOT_FOUND": "❌ A statisztika csatorna nem található a konfigurációban! (stats_id)"
    }

    _EN = {
        "LB_TITLE_WEEKLY": "Weekly Top 10",
        "LB_TITLE_MONTHLY": "Monthly Top 10",
        "LB_TITLE_ALLTIME": "All-time Top 10",
        "LB_TITLE_DEFAULT": "Top 10",
        "LB_SHARED_BY": "📊 **{user}** shared this leaderboard:",
        "LB_EMPTY": "*Not enough data for this period... Be the first!* 🚀",
        "LB_UNKNOWN_USER": "Unknown ({id})",
        "LB_POINTS": "points",
        "LB_FOOTER_POINTS": "### Message 10 | Reaction 5 | Voice 2/min",
        "BTN_WEEKLY": "Weekly",
        "BTN_MONTHLY": "Monthly",
        "BTN_ALLTIME": "All-time",
        "BTN_MY_RANK": "My Rank",
        "BTN_SHARE": "Share",
        "DESC_ME": "View your own statistics.",
        "PROFILE_SHARED_BY": "📊 **{user}** shared their profile:",
        "PROFILE_RANK": "Rank",
        "PROFILE_SUBTITLE": "Your total profile on the server.",
        "SECTION_ACTIVITY": "### 📊 Activity",
        "SECTION_STATS": "### 📈 Stats",
        "SECTION_COMMUNITY": "### 🤝 Community (30 days)",
        "SECTION_GAMES": "### 🎮 Recent games",
        "STAT_TOTAL_SCORE": "**Total score:** ### **{points}**",
        "STAT_DETAILS": "**Messages:** `{msg}` | **Reactions:** `{reac}` | **Voice:** `{voice}m`",
        "STAT_LAST_ACTIVE": "**Last active:** `{time}`",
        "STAT_DAILY_AVG": "**Daily average (30 days):** `{avg:.2f} messages/day`",
        "SOCIAL_FAV_ROOM": "**Favorite room:** <#{id}>",
        "SOCIAL_FAV_EMOJI": "**Favorite emoji:** {emoji}",
        "SOCIAL_MAIN_TARGET": "**Main target:** <@{id}>",
        "SOCIAL_BEST_FRIEND": "**Best Friend (Voice):** <@{id}>",
        "SOCIAL_FAV_ROOM_STATIC": "**Favorite room:** {name}",
        "SOCIAL_MAIN_TARGET_STATIC": "**Main target:** {name}",
        "SOCIAL_BEST_FRIEND_STATIC": "**Best Friend (Voice):** {name}",
        "ERR_NO_DATA": "You don't have data in the database yet. Write a few messages first!",
        "ERR_NO_DATA_PERIOD": "Unfortunately, you have no recorded data for this period.",
        "ERR_STATS_CHANNEL": "You can only use this command in the <#{id}> channel!",
        "ERR_ADMIN_ONLY": "This command can only be used in the admin channel: <#{id}>",
        "SUCCESS_SHARED": "Successfully shared in the channel! ✅",
        "REPORT_GEN_STATUS": "Generating status report...",
        "REPORT_GEN_ROLE": "Generating player-rank log...",
        "REPORT_EMPTY_HISTORY": "No entries in the log yet.",
        "GAME_ADDED": "✅ Added: If name contains `{name}`, rank will be: `Player: {suffix}`",
        "GAME_REMOVED": "🗑️ `{name}` removed from watch list.",
        "GAME_LIST_EMPTY": "No watched games.",
        "GAME_LIST_TITLE": "🎮 Watched games list",
        "GAME_REPORT_GEN": "Generating report...",
        "GAME_REPORT_EMPTY": "No data for the selected period.",
        "GAME_REPORT_DONE": "📊 Finished `{tf}` game report ({count} different games).",
        "DB_RESET_SUCCESS": "✅ Database successfully cleared! All activity data removed.",
        "DB_RESET_ERROR": "❌ Error occurred during deletion: {e}",
        "REPORT_TITLE_HEADER": "--- REPORT: {guild} ---\nGen: {now}\nUser                      | Stat         | M    | R    | V    | Details",
        "REPORT_STAGE_1": "Stage 1",
        "REPORT_STAGE_2": "Stage 2",
        "REPORT_STAGE_NORMAL": "Normal",
        "REPORT_INACTIVE": "Inactive",
        "REPORT_S2_RETURN": "From S2: {days} days",
        "REPORT_S1_LIMIT": "Until S1: {days} days",
        "ROLE_LOG_TITLE": "--- PLAYER-RANK LOG: {guild} ---\nGen: {now}\nTimestamp            | User                      | Status    | Role",
        "ROLE_LOG_REMOVED": "REMOVED",
        "ROLE_LOG_ADDED": "ADDED",
        "GAME_POP_TITLE": "--- GAME POPULARITY REPORT ({tf}) ---",
        "GAME_POP_MONTHLY": "MONTHLY",
        "GAME_POP_ALLTIME": "ALL-TIME",
        "GAME_POP_GEN": "Generated: {now}",
        "GAME_POP_HEADER": "Game name                           | Players   | Total min",
        "PRESENCE_WATCHING": "Watching the slackers... 🤫",
        
        "CMD_TOP_DESC": "[#{stats_id}] Shows the weekly, monthly or all-time leaderboard.",
        "CMD_TOP_TF_DESC": "Choose a timeframe (weekly, monthly, alltime)",
        "CMD_ME_MEMBER_DESC": "[#{stats_id}] View your own statistics.",
        "CMD_ADD_GAME_DESC": "[#{admin_id}] Add a new game to automatic rank distribution.",
        "CMD_ADD_GAME_NAME_DESC": "Part of the game's name (e.g., Minecraft)",
        "CMD_ADD_GAME_SUFFIX_DESC": "End of the rank (example: 'Minecraft' -> 'Player: Minecraft')",
        "CMD_REMOVE_GAME_DESC": "[#{admin_id} + @&{role_id}] Remove a game from the list.",
        "CMD_REMOVE_GAME_NAME_DESC": "The exact search keyword (e.g., Minecraft)",
        "CMD_LIST_GAMES_DESC": "[#{admin_id}] List all watched games.",
        "CMD_GAME_REPORT_DESC": "[#{admin_id}] Generate a game popularity report in .txt.",
        "CMD_GAME_REPORT_TF_DESC": "Choice: alltime (all) or monthly (this month)",
        "CMD_STATUS_REPORT_DESC": "[#{admin_id}] Generate a detailed TXT report.",
        "CMD_GAME_ROLE_REPORT_DESC": "[#{admin_id}] Download the player-rank assignment log.",
        "CMD_RESET_DB_DESC": "[#{admin_id} + @&{role_id}] Permanently delete ALL activity data.",
        "CMD_SYNC_DESC": "[#{admin_id} + @&{role_id}] Manually sync slash commands.",
        "CMD_SYNC_MODE_DESC": "Choice: guild (to this server), global (everywhere), copy (copy global here)",
        "ERR_STATS_LOAD": "❌ Error occurred while loading stats: {e}",
        "ERR_OWNER_ONLY": "Only the bot owner can use this.",
        "CMD_CLEAR_DONE": "✅ All registered commands (global and server) have been cleared. You can now use {cmd} to refresh them.",
        "INFO_TITLE": "{bot_name} - Introduction",
        "INFO_DESC": "Hi! I'm an activity tracker bot. I monitor your messages, reactions, and time spent in voice channels to help you earn points!",
        "INFO_FEATURES_TITLE": "### 🚀 Features & Commands",
        "INFO_FEATURES_DESC": "• `/top` - View the server's most active members.\n• `/me` - View your own detailed stats.\n• **Auto Roles** - Get unique roles for the games you play most!\n• **Inactivity** - Stay active to avoid the {role} role!",
        "INFO_FOOTER": "Use the commands in the {channel} channel!",
        "INFO_DEV_TITLE": "🛠️ Administrative Command List",
        "INFO_DEV_PREFIX": "### ⌨️ Prefix Commands (Suffix: `{suffix}`)\n",
        "INFO_DEV_SLASH": "\n### ⚡ Slash Commands\n",
        "CMD_INFO_DEV_DESC": "[#{admin_id}] Lists all commands for administrators.",
        "CMD_INFO_DESC": "[#{stats_id}] General introduction to the bot.",
        "TECH_SYNC": "Calls `bot.tree.sync()`. Updates / command metadata on Discord's servers.",
        "TECH_RESET": "Permanently clears `stats`, `role_history`, and `game_stats` tables. Irreversible.",
        "TECH_ADD_GAME": "Saves a new regex pattern to `tracked_games` and refreshes the tracker cache.",
        "TECH_STATUS": "Fetches aggregated data from DB, calculates Voice offsets, and generates a .txt file.",
        "TECH_GAME_REPORT": "Summarizes `game_stats` and `tracked_games` tables for the selected period.",
        "ERR_STATS_NOT_FOUND": "❌ Stats channel not found in config! (stats_id)"
    }

    # These are empty 'placeholders' that will be filled with the words from above
    LB_TITLE_WEEKLY = ""
    LB_TITLE_MONTHLY = ""
    LB_TITLE_ALLTIME = ""
    LB_TITLE_DEFAULT = ""
    LB_SHARED_BY = ""
    LB_EMPTY = ""
    LB_UNKNOWN_USER = ""
    LB_POINTS = ""
    LB_FOOTER_POINTS = ""
    BTN_WEEKLY = ""
    BTN_MONTHLY = ""
    BTN_ALLTIME = ""
    BTN_MY_RANK = ""
    BTN_SHARE = ""
    DESC_ME = ""
    PROFILE_SHARED_BY = ""
    PROFILE_RANK = ""
    PROFILE_SUBTITLE = ""
    SECTION_ACTIVITY = ""
    SECTION_STATS = ""
    SECTION_COMMUNITY = ""
    SECTION_GAMES = ""
    STAT_TOTAL_SCORE = ""
    STAT_DETAILS = ""
    STAT_LAST_ACTIVE = ""
    STAT_DAILY_AVG = ""
    SOCIAL_FAV_ROOM = ""
    SOCIAL_FAV_EMOJI = ""
    SOCIAL_MAIN_TARGET = ""
    SOCIAL_BEST_FRIEND = ""
    SOCIAL_FAV_ROOM_STATIC = ""
    SOCIAL_MAIN_TARGET_STATIC = ""
    SOCIAL_BEST_FRIEND_STATIC = ""
    ERR_NO_DATA = ""
    ERR_NO_DATA_PERIOD = ""
    ERR_STATS_CHANNEL = ""
    ERR_ADMIN_ONLY = ""
    SUCCESS_SHARED = ""
    REPORT_GEN_STATUS = ""
    REPORT_GEN_ROLE = ""
    REPORT_EMPTY_HISTORY = ""
    GAME_ADDED = ""
    GAME_REMOVED = ""
    GAME_LIST_EMPTY = ""
    GAME_LIST_TITLE = ""
    GAME_REPORT_GEN = ""
    GAME_REPORT_EMPTY = ""
    GAME_REPORT_DONE = ""
    DB_RESET_SUCCESS = ""
    DB_RESET_ERROR = ""
    REPORT_TITLE_HEADER = ""
    REPORT_STAGE_1 = ""
    REPORT_STAGE_2 = ""
    REPORT_STAGE_NORMAL = ""
    REPORT_INACTIVE = ""
    REPORT_S2_RETURN = ""
    REPORT_S1_LIMIT = ""
    ROLE_LOG_TITLE = ""
    ROLE_LOG_REMOVED = ""
    ROLE_LOG_ADDED = ""
    GAME_POP_TITLE = ""
    GAME_POP_MONTHLY = ""
    GAME_POP_ALLTIME = ""
    GAME_POP_GEN = ""
    GAME_POP_HEADER = ""
    PRESENCE_WATCHING = ""
    
    CMD_TOP_DESC = ""
    CMD_TOP_TF_DESC = ""
    CMD_ME_MEMBER_DESC = ""
    CMD_ADD_GAME_DESC = ""
    CMD_ADD_GAME_NAME_DESC = ""
    CMD_ADD_GAME_SUFFIX_DESC = ""
    CMD_REMOVE_GAME_DESC = ""
    CMD_REMOVE_GAME_NAME_DESC = ""
    CMD_LIST_GAMES_DESC = ""
    CMD_GAME_REPORT_DESC = ""
    CMD_INFO_DEV_DESC = ""
    CMD_INFO_DESC = ""
    TECH_SYNC = ""
    TECH_RESET = ""
    TECH_ADD_GAME = ""
    TECH_STATUS = ""
    TECH_GAME_REPORT = ""
    INFO_DEV_TITLE = ""
    INFO_DEV_PREFIX = ""
    INFO_DEV_SLASH = ""
    CMD_GAME_REPORT_TF_DESC = ""
    CMD_STATUS_REPORT_DESC = ""
    CMD_GAME_ROLE_REPORT_DESC = ""
    CMD_RESET_DB_DESC = ""
    CMD_SYNC_DESC = ""
    CMD_SYNC_MODE_DESC = ""
    ERR_STATS_LOAD = ""
    ERR_OWNER_ONLY = ""
    CMD_CLEAR_DONE = ""
    INFO_TITLE = ""
    INFO_DESC = ""
    INFO_FEATURES_TITLE = ""
    INFO_FEATURES_DESC = ""
    INFO_FOOTER = ""
    ERR_STATS_NOT_FOUND = ""

    @classmethod
    def load_language(cls, lang_code):
        # This part picks the right language for the bot to use (like a light switch)
        translations = cls._EN if lang_code.lower() == "en" else cls._HU
        for key, value in translations.items():
            setattr(cls, key, value)

    @classmethod
    def get_lb_title(cls, timeframe):
        # A quick way to get the right title for the 'Weekly', 'Monthly' or 'All-time' leaderboard
        return {
            "weekly": cls.LB_TITLE_WEEKLY,
            "monthly": cls.LB_TITLE_MONTHLY,
            "alltime": cls.LB_TITLE_ALLTIME
        }.get(timeframe.lower(), cls.LB_TITLE_DEFAULT)

# Initialize with HU by default
Messages.load_language("hu")
