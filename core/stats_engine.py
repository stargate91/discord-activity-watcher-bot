import discord
import datetime
from config_loader import Config

class StatsEngine:
    def __init__(self, db):
        self.db = db

    def get_leaderboard(self, guild, user=None, timeframe="alltime", live_voice_times=None):
        # This function calculates the points for everyone to see who is the most active
        # It can do this for just one week, one month, or everything together.
        
        days = {"weekly": 7, "monthly": Config.SOCIAL_STATS_DAYS, "alltime": None}.get(timeframe.lower(), None)
        data = self.db.get_leaderboard_data(guild.id, days)
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        
        # We make sure we don't count 'alt' accounts separately if they are linked to a main account
        data = {uid: stats for uid, stats in data.items() if uid not in Config.USER_MAPPING}

        # If people are currently in a voice channel, we add those 'live' minutes too
        if live_voice_times:
            for main_id, start in live_voice_times.items():
                if main_id in data:
                    curr_mins = (now_utc - start).total_seconds() / 60
                    data[main_id]["voice"] += curr_mins
                else:
                    # If they are in the server but not in the database yet, we add them now
                    m = guild.get_member(main_id)
                    if m:
                        curr_mins = (now_utc - start).total_seconds() / 60
                        data[main_id] = {"messages": 0, "reactions": 0, "voice": curr_mins}

        # Now we turn messages and voice minutes into actual points (the 'score')
        scores = []
        user_full_stats = None 
        
        for uid, stats in data.items():
            points = (stats["messages"] * Config.POINTS_MESSAGE) + \
                     (stats["reactions"] * Config.POINTS_REACTION) + \
                     (int(stats["voice"]) * Config.POINTS_VOICE)
            if points > 0:
                scores.append((uid, points, stats))
        
        # Sort the list so the person with the most points is at the top
        scores.sort(key=lambda x: x[1], reverse=True)
        top_10 = scores[:Config.LEADERBOARD_LIMIT]
        
        # If we asked for a specific person's stats, find where they are on the list (their rank)
        if user:
            user_id = Config.get_main_id(user.id)
            rank = next((i for i, (uid, _, _) in enumerate(scores, 1) if uid == user_id), "N/A")
            if rank != "N/A":
                u_entry = next(x for x in scores if x[0] == user_id)
                # Pack the data together so it's easy for the bot to show on a profile card
                db_compat_data = {
                    "message_count": u_entry[2]["messages"],
                    "reaction_count": u_entry[2]["reactions"],
                    "voice_minutes": u_entry[2]["voice"], 
                    "last_active": now_utc 
                }
                user_full_stats = (user, db_compat_data, u_entry[1], u_entry[2]["voice"], rank)
                
        return top_10, user_full_stats
