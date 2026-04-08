import discord

class Icons:
    CHART: discord.PartialEmoji = None
    ROCKET: discord.PartialEmoji = None
    SUCCESS: discord.PartialEmoji = None
    TRASH: discord.PartialEmoji = None
    CONTROLLER: discord.PartialEmoji = None
    STATS: discord.PartialEmoji = None
    COMMUNITY: discord.PartialEmoji = None
    ERROR: discord.PartialEmoji = None
    WARNING: discord.PartialEmoji = None
    SPOTIFY: discord.PartialEmoji = None
    GAMER: discord.PartialEmoji = None
    VARIETY: discord.PartialEmoji = None
    STREAMER: discord.PartialEmoji = None
    TROPHY: discord.PartialEmoji = None
    VETERAN: discord.PartialEmoji = None
    MEDAL_1: discord.PartialEmoji = None
    MEDAL_2: discord.PartialEmoji = None
    MEDAL_3: discord.PartialEmoji = None
    TOOLS: discord.PartialEmoji = None
    LIGHTNING: discord.PartialEmoji = None
    COOLDOWN: discord.PartialEmoji = None
    MEME: discord.PartialEmoji = None
    ROLE_ADMIN: discord.PartialEmoji = None
    ROLE_TESTER: discord.PartialEmoji = None
    ROLE_USER: discord.PartialEmoji = None
    CHAN_ADMIN: discord.PartialEmoji = None
    CHAN_STATS: discord.PartialEmoji = None
    CHAN_ANY: discord.PartialEmoji = None
    LOCK: discord.PartialEmoji = None
    ELITE_LOG: discord.PartialEmoji = None
    PREV_PAGE: discord.PartialEmoji = None
    NEXT_PAGE: discord.PartialEmoji = None

    @classmethod
    def setup(cls, config):
        """
        This function sets up all the emojis the bot uses. It tries to get them from your 
        config file, but if it can't find them, it uses some nice default ones!
        """
        defaults = {
            "CHART": "📊", "ROCKET": "🚀", "SUCCESS": "✅", "TRASH": "🗑️",
            "CONTROLLER": "🎮", "STATS": "📈", "COMMUNITY": "🤝", "ERROR": "❌",
            "WARNING": "⚠️", "SPOTIFY": "🎵", "GAMER": "🎮",
            "VARIETY": "🎯", "STREAMER": "📺", "TROPHY": "🏆", "VETERAN": "🎖️",
            "MEDAL_1": "🥇", "MEDAL_2": "🥈", "MEDAL_3": "🥉", "TOOLS": "🛠️",
            "LIGHTNING": "⚡", "COOLDOWN": "⏳", "MEME": "🖼️",
            "ROLE_ADMIN": "👑", "ROLE_TESTER": "🧪", "ROLE_USER": "👤",
            "CHAN_ADMIN": "🛠️", "CHAN_STATS": "📊", "CHAN_ANY": "🌐", 
            "LOCK": "🔒", "ELITE_LOG": "🏆", "PREV_PAGE": "⬅️", "NEXT_PAGE": "➡️"
        }

        # We check if you have added your own custom emojis in the 'EMOJIS' part of the config!
        provided_data = getattr(config, "EMOJIS", {})
        
        # We combine our default emojis with yours!
        all_keys = set(defaults.keys()) | set(provided_data.keys())
        
        for key in all_keys:
            val = provided_data.get(key) or defaults.get(key, "❓")
            try:
                setattr(cls, key, discord.PartialEmoji.from_str(val))
            except:
                # If something goes wrong with the special Discord emoji format, we just use the plain emoji symbol instead!
                setattr(cls, key, val)

# This part makes sure that even if we don't have a config, the bot doesn't crash on startup!
class DefaultConfig: EMOJIS = {}
try:
    Icons.setup(DefaultConfig())
except:
    pass
