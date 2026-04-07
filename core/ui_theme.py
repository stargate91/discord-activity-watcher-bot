import discord

class Theme:
    # These are the default colors for the bot (like blue, green, and red). 
    # They make everything look pretty and organized!
    PRIMARY = 0x3498db
    SECONDARY = 0x2b2d31
    SUCCESS = 0x2ecc71
    WARNING = 0xFEE75C
    DANGER = 0xED4245
    BACKGROUND = 0x2b2d31
    ACCENT = 0xEB459E

    @classmethod
    def init_theme(cls, config):
        """
        This function sets up the bot's look! It tries to find your custom colors in the config file, 
        but it's also smart enough to find the 'old' way we used to store colors.
        """
        theme_data = getattr(config, "THEME", {})
        ui_data = getattr(config, "_ui", {}) # Access legacy UI data
        
        def get_color(name, legacy_name, default):
            # We check the new color settings first, but if those are missing, we look for the older ones!
            val = theme_data.get(name) or ui_data.get(legacy_name)
            if not val: return default
            try:
                return int(str(val), 16)
            except:
                return default

        cls.PRIMARY = get_color("primary", "color_primary", 0x3498db)
        cls.SUCCESS = get_color("success", "color_success", 0x2ecc71)
        cls.WARNING = get_color("warning", "color_warning", 0xFEE75C)
        cls.DANGER = get_color("danger", "color_danger", 0xED4245)
        cls.ACCENT = get_color("accent", "color_accent", 0xEB459E)
