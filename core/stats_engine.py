import discord
import datetime
from config_loader import Config
from core.activity_processor import ActivityProcessor

class StatsEngine:
    def __init__(self, db, bot=None):
        self.db = db
        self.bot = bot # We keep a reference to the bot so we can check people's roles on the fly!

    def get_leaderboard(self, guild, user=None, timeframe="alltime", live_voice_times=None):
        # This is our cool leaderboard function! It gets the best players, but only the top 20 to keep it fast.
        days = {"weekly": 7, "monthly": Config.SOCIAL_STATS_DAYS, "alltime": None}.get(timeframe.lower(), None)
        
        # We get a few extra people just in case some of them are alt accounts that we need to skip.
        data = self.db.get_leaderboard_data(guild.id, days, limit=Config.LEADERBOARD_LIMIT * 2)
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        
        # We don't want to show the same person twice if they have an alt account!
        data = {uid: stats for uid, stats in data.items() if uid not in Config.USER_MAPPING}

        # If someone is currently in a voice channel, we add their current minutes to their score right now!
        if live_voice_times:
            for main_id, start in live_voice_times.items():
                if main_id in data:
                    curr_mins = (now_utc - start).total_seconds() / 60
                    data[main_id]["voice"] += curr_mins
                    member = guild.get_member(main_id)
                    # We check their role to see if they get extra points for being active
                    tier, is_streaming, _ = ActivityProcessor.get_participation_tier(member)
                    data[main_id]["points"] += (curr_mins * tier)
                    if is_streaming:
                        data[main_id]["stream"] += curr_mins

        # Now we turn our data into a nice list where everyone has their score attached.
        scores = []
        for uid, stats in data.items():
            if stats["points"] > 0:
                scores.append((uid, stats["points"], stats))
        
        # We sort them so the person with the most points is at the top!
        scores.sort(key=lambda x: x[1], reverse=True)
        top_10 = scores[:Config.LEADERBOARD_LIMIT]
        
        user_full_stats = None 
        if user:
            user_id = Config.get_main_id(user.id)
            # First, let's see if the user is already one of the lucky top 10 people.
            rank = next((i for i, (uid, _, _) in enumerate(top_10, 1) if uid == user_id), None)
            
            if rank:
                # Yay! They are in the top 10, let's just use the data we already have.
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
                
                if days:
                    u_stats = self.db.get_user_stats_for_period(user_id, guild.id, days)
                else:
                    u_raw = self.db.get_user_data(user_id, guild.id)
                    if not u_raw:
                        u_stats = {"messages":0, "reactions":0, "voice":0, "points":0, "stream":0, "media":0}
                    else:
                        u_stats = {
                            "messages": u_raw["message_count"],
                            "reactions": u_raw["reaction_count"],
                            "voice": u_raw["voice_minutes"],
                            "points": u_raw["points_total"],
                            "stream": u_raw["stream_minutes"],
                            "media": u_raw["media_count"]
                        }
                
                # If they are currently talking in a voice channel, we add those extra points too!
                live_points = 0
                if live_voice_times and user_id in live_voice_times:
                    start = live_voice_times[user_id]
                    curr_mins = (now_utc - start).total_seconds() / 60
                    member = guild.get_member(user_id)
                    tier, is_streaming, _ = ActivityProcessor.get_participation_tier(member)
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
