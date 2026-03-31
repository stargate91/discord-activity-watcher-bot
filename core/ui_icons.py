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
    SHUSH: discord.PartialEmoji = None
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

    @classmethod
    def setup(cls, config):
        """Initializes all icons from config or hardcoded defaults."""
        defaults = {
            "CHART": "📊", "ROCKET": "🚀", "SUCCESS": "✅", "TRASH": "🗑️",
            "CONTROLLER": "🎮", "STATS": "📈", "COMMUNITY": "🤝", "ERROR": "❌",
            "WARNING": "⚠️", "SHUSH": "🤫", "SPOTIFY": "🎵", "GAMER": "🎮",
            "VARIETY": "🎯", "STREAMER": "📺", "TROPHY": "🏆", "VETERAN": "🎖️",
            "MEDAL_1": "🥇", "MEDAL_2": "🥈", "MEDAL_3": "🥉", "TOOLS": "🛠️",
            "LIGHTNING": "⚡", "COOLDOWN": "⏳", "MEME": "🖼️",
            "ROLE_ADMIN": "👑", "ROLE_TESTER": "🧪", "ROLE_USER": "👤",
            "CHAN_ADMIN": "🛠️", "CHAN_STATS": "📊", "CHAN_ANY": "🌐"
        }

        # Load from config if available (Config.EMOJIS)
        provided_data = getattr(config, "EMOJIS", {})
        
        # Merge defaults with provided config
        all_keys = set(defaults.keys()) | set(provided_data.keys())
        
        for key in all_keys:
            val = provided_data.get(key) or defaults.get(key, "❓")
            setattr(cls, key, discord.PartialEmoji.from_str(val))

# Default initialization for safe-importing
class DefaultConfig: EMOJIS = {}
Icons.setup(DefaultConfig())
