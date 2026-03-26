import discord
import datetime
from config_loader import Config

class StatsEngine:
    def __init__(self, db):
        self.db = db

    def get_leaderboard(self, guild, user=None, timeframe="alltime", live_voice_times=None):
        """
        Calculates leaderboard data for a guild, optionally including a specific user's detailed stats.
        Incorporate live voice session times if provided.
        """
        days = {"weekly": 7, "monthly": Config.SOCIAL_STATS_DAYS, "alltime": None}.get(timeframe.lower(), None)
        data = self.db.get_leaderboard_data(guild.id, days)
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        
        # Filter out alts from the DB data (if any old ones exist)
        data = {uid: stats for uid, stats in data.items() if uid not in Config.USER_MAPPING}

        # Add live voice session time (now keyed by main_id in bot.voice_start_times)
        if live_voice_times:
            for main_id, start in live_voice_times.items():
                if main_id in data:
                    curr_mins = (now_utc - start).total_seconds() / 60
                    data[main_id]["voice"] += curr_mins
                else:
                    # We only add if they are in this guild
                    m = guild.get_member(main_id)
                    if m:
                        curr_mins = (now_utc - start).total_seconds() / 60
                        data[main_id] = {"messages": 0, "reactions": 0, "voice": curr_mins}

        scores = []
        user_full_stats = None # Will store (user, db_data_row, total_pts, total_voice_mins, rank)
        
        for uid, stats in data.items():
            points = (stats["messages"] * Config.POINTS_MESSAGE) + \
                     (stats["reactions"] * Config.POINTS_REACTION) + \
                     (int(stats["voice"]) * Config.POINTS_VOICE)
            if points > 0:
                scores.append((uid, points, stats))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        top_10 = scores[:Config.LEADERBOARD_LIMIT]
        
        if user:
            user_id = Config.get_main_id(user.id)
            rank = next((i for i, (uid, _, _) in enumerate(scores, 1) if uid == user_id), "N/A")
            if rank != "N/A":
                u_entry = next(x for x in scores if x[0] == user.id)
                # Reconstruct DB-style data dict for the profile view
                db_compat_data = {
                    "message_count": u_entry[2]["messages"],
                    "reaction_count": u_entry[2]["reactions"],
                    "voice_minutes": u_entry[2]["voice"], # This already includes live time
                    "last_active": now_utc # Approximation
                }
                # user_full_stats format: (user, db_compat_data, points, voice_mins, rank)
                user_full_stats = (user, db_compat_data, u_entry[1], u_entry[2]["voice"], rank)
                
        return top_10, user_full_stats
