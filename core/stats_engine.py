import discord
import datetime
from config_loader import Config
from core.activity_processor import ActivityProcessor

class StatsEngine:
    def __init__(self, db, bot=None):
        self.db = db
        self.bot = bot # Store bot reference for live tier lookups

    def get_leaderboard(self, guild, user=None, timeframe="alltime", live_voice_times=None):
        # Optimized Leaderboard: Fetch only Top 20 (to account for alts) instead of everyone
        days = {"weekly": 7, "monthly": Config.SOCIAL_STATS_DAYS, "alltime": None}.get(timeframe.lower(), None)
        
        # We fetch enough to fill the Top 10 even after filtering alts
        data = self.db.get_leaderboard_data(guild.id, days, limit=Config.LEADERBOARD_LIMIT * 2)
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        
        # Filter alts
        data = {uid: stats for uid, stats in data.items() if uid not in Config.USER_MAPPING}

        # Add live voice data for those in the Top list
        if live_voice_times:
            for main_id, start in live_voice_times.items():
                if main_id in data:
                    curr_mins = (now_utc - start).total_seconds() / 60
                    data[main_id]["voice"] += curr_mins
                    tier, is_streaming, _ = ActivityProcessor.get_participation_tier(main_id, guild)
                    data[main_id]["points"] += (curr_mins * tier)
                    if is_streaming:
                        data[main_id]["stream"] += curr_mins

        # Convert to scores list
        scores = []
        for uid, stats in data.items():
            if stats["points"] > 0:
                scores.append((uid, stats["points"], stats))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        top_10 = scores[:Config.LEADERBOARD_LIMIT]
        
        user_full_stats = None 
        if user:
            user_id = Config.get_main_id(user.id)
            # 1. Check if user is in the Top 10 we already have
            rank = next((i for i, (uid, _, _) in enumerate(top_10, 1) if uid == user_id), None)
            
            if rank:
                u_entry = next(x for x in top_10 if x[0] == user_id)
                db_compat_data = {
                    "message_count": u_entry[2]["messages"],
                    "reaction_count": u_entry[2]["reactions"],
                    "voice_minutes": u_entry[2]["voice"], 
                    "stream_minutes": u_entry[2].get("stream", 0),
                    "last_active": now_utc 
                }
                user_full_stats = (user, db_compat_data, u_entry[1], u_entry[2]["voice"], rank)
            else:
                # 2. Not in Top 10, fetch specific rank and stats
                rank = self.db.get_user_rank(user_id, guild.id, days)
                
                u_raw = self.db.get_user_data(user_id, guild.id)
                if not u_raw:
                    u_stats = {"messages":0, "reactions":0, "voice":0, "points":0, "stream":0}
                else:
                    u_stats = {
                        "messages": u_raw["message_count"],
                        "reactions": u_raw["reaction_count"],
                        "voice": u_raw["voice_minutes"],
                        "points": u_raw["points_total"],
                        "stream": u_raw["stream_minutes"]
                    }
                
                # Add live data if any
                live_points = 0
                if live_voice_times and user_id in live_voice_times:
                    start = live_voice_times[user_id]
                    curr_mins = (now_utc - start).total_seconds() / 60
                    tier, is_streaming, _ = ActivityProcessor.get_participation_tier(user_id, guild)
                    live_points = curr_mins * tier
                    u_stats["voice"] += curr_mins
                    u_stats["stream"] += curr_mins if is_streaming else 0
                
                total_pts = u_stats["points"] + live_points
                db_compat_data = {
                    "message_count": u_stats["messages"],
                    "reaction_count": u_stats["reactions"],
                    "voice_minutes": u_stats["voice"],
                    "stream_minutes": u_stats["stream"],
                    "last_active": now_utc
                }
                user_full_stats = (user, db_compat_data, total_pts, u_stats["voice"], rank)
                
        return top_10, user_full_stats
