class Messages:
    # --- Leaderboard & UI ---
    LB_TITLE_WEEKLY = "Heti Top 10"
    LB_TITLE_MONTHLY = "Havi Top 10"
    LB_TITLE_ALLTIME = "Összesített Top 10"
    LB_TITLE_DEFAULT = "Top 10"
    
    LB_SHARED_BY = "📊 **{user}** megosztotta ezt a ranglistát:"
    LB_EMPTY = "*Nincs elég adat az időszakhoz... Legyél te az első!* 🚀"
    LB_UNKNOWN_USER = "Ismeretlen ({id})"
    LB_POINTS = "pont"
    LB_FOOTER_POINTS = "### Üzenet 10 | Reakció 5 | Voice 2/perc"
    
    # Buttons
    BTN_WEEKLY = "Heti"
    BTN_MONTHLY = "Havi"
    BTN_ALLTIME = "Összesített"
    BTN_MY_RANK = "Saját helyezésem"
    BTN_SHARE = "Megosztás"
    
    # --- Profile ---
    PROFILE_SHARED_BY = "📊 **{user}** megosztotta a profilját:"
    PROFILE_RANK = "Helyezés"
    PROFILE_SUBTITLE = "Összesített profilod a szerveren."
    
    SECTION_ACTIVITY = "### 📊 Aktivitás"
    SECTION_STATS = "### 📈 Statisztikák"
    SECTION_COMMUNITY = "### 🤝 Közösség (30 nap)"
    SECTION_GAMES = "### 🎮 Legutóbbi játékok"
    
    STAT_TOTAL_SCORE = "**Összpontszám:** ### **{points}**"
    STAT_DETAILS = "**Üzenetek:** `{msg}` | **Reakciók:** `{reac}` | **Voice:** `{voice}p`"
    STAT_LAST_ACTIVE = "**Utoljára aktív:** `{time}`"
    STAT_DAILY_AVG = "**Napi átlag (30 nap):** `{avg:.2f} üzenet/nap`"
    
    SOCIAL_FAV_ROOM = "**Kedvenc szoba:** <#{id}>"
    SOCIAL_FAV_EMOJI = "**Kedvenc emoji:** {emoji}"
    SOCIAL_MAIN_TARGET = "**Fő célpont:** <@{id}>"
    SOCIAL_BEST_FRIEND = "**Best Friend (Voice):** <@{id}>"
    
    # --- Command Feedback ---
    ERR_NO_DATA = "Még nincs adatod az adatbázisban. Írj pár üzenetet előbb!"
    ERR_NO_DATA_PERIOD = "Sajnos ebben az időszakban még nincs rögzített adatod."
    ERR_STATS_CHANNEL = "Ezt a parancsot csak a <#{id}> szobában használhatod!"
    ERR_ADMIN_ONLY = "Ez a parancs csak az admin csatornában használható: <#{id}>"
    
    SUCCESS_SHARED = "Sikeresen megosztva a csatornán! ✅"
    
    REPORT_GEN_STATUS = "Status report generálása..."
    REPORT_GEN_ROLE = "Játékos-rang napló generálása..."
    REPORT_EMPTY_HISTORY = "Még nincs bejegyzés a naplóban."
    
    GAME_ADDED = "✅ Hozzáadva: Ha a névben szerepel: `{name}`, a rang ez lesz: `Player: {suffix}`"
    GAME_REMOVED = "🗑️ `{name}` eltávolítva a figyelési listából."
    GAME_LIST_EMPTY = "Nincsenek figyelt játékok."
    GAME_LIST_TITLE = "🎮 Figyelt játékok listája"
    
    GAME_REPORT_GEN = "Riport generálása..."
    GAME_REPORT_EMPTY = "Nincsenek adatok a választott időszakhoz."
    GAME_REPORT_DONE = "📊 Elkészült a(z) `{tf}` játék riport ({count} különböző játék)."
    
    DB_RESET_SUCCESS = "✅ Az adatbázis sikeresen kiürítve! Minden aktivitási adat törölve lett."
    DB_RESET_ERROR = "❌ Hiba történt a törlés során: {e}"
    
    # --- Reports (Admin) ---
    REPORT_TITLE_HEADER = "--- REPORT: {guild} ---\nGen: {now}\nUser                      | Stat         | M    | R    | V    | Details"
    REPORT_STAGE_1 = "Stage 1"
    REPORT_STAGE_2 = "Stage 2"
    REPORT_STAGE_NORMAL = "Normal"
    REPORT_INACTIVE = "Inaktív"
    REPORT_S2_RETURN = "S2-ből: {days} nap"
    REPORT_S1_LIMIT = "S1-ig: {days} nap"
    
    ROLE_LOG_TITLE = "--- JÁTÉKOS-RANG NAPLÓ: {guild} ---\nGen: {now}\nTimestamp            | User                      | Státusz    | Role"
    ROLE_LOG_REMOVED = "ELVÉVE"
    ROLE_LOG_ADDED = "ADVA"
    
    GAME_POP_TITLE = "--- JÁTÉK NÉPSZERŰSÉGI RIPORT ({tf}) ---"
    GAME_POP_MONTHLY = "HAVI"
    GAME_POP_ALLTIME = "ÖSSZESÍTETT"
    GAME_POP_GEN = "Generálva: {now}"
    GAME_POP_HEADER = "Játék neve                               | Egyedi játékosok"
    
    # Presence
    PRESENCE_WATCHING = "Figyelem a lazsálókat... 🤫"

    @classmethod
    def get_lb_title(cls, timeframe):
        return {
            "weekly": cls.LB_TITLE_WEEKLY,
            "monthly": cls.LB_TITLE_MONTHLY,
            "alltime": cls.LB_TITLE_ALLTIME
        }.get(timeframe.lower(), cls.LB_TITLE_DEFAULT)
