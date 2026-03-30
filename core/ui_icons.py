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

    @classmethod
    def setup(cls, config):
        """Initializes all icons from config or hardcoded defaults."""
        defaults = {
            "CHART": "📊",
            "ROCKET": "🚀",
            "SUCCESS": "✅",
            "TRASH": "🗑️",
            "CONTROLLER": "🎮",
            "STATS": "📈",
            "COMMUNITY": "🤝",
            "ERROR": "❌",
            "WARNING": "⚠️",
            "SHUSH": "🤫"
        }

        # Load from config if available (Config.EMOJIS)
        provided_data = getattr(config, "EMOJIS", {})
        
        def get(name):
            val = provided_data.get(name) or defaults.get(name, "❓")
            return discord.PartialEmoji.from_str(val)

        # Initialize all class properties
        cls.CHART = get("CHART")
        cls.ROCKET = get("ROCKET")
        cls.SUCCESS = get("SUCCESS")
        cls.TRASH = get("TRASH")
        cls.CONTROLLER = get("CONTROLLER")
        cls.STATS = get("STATS")
        cls.COMMUNITY = get("COMMUNITY")
        cls.ERROR = get("ERROR")
        cls.WARNING = get("WARNING")
        cls.SHUSH = get("SHUSH")

# Default initialization for safe-importing
class DefaultConfig: EMOJIS = {}
Icons.setup(DefaultConfig())
