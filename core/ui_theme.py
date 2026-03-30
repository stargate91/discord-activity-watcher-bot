import discord

class Theme:
    # Default colors (mostly dark grey and some bright status colors)
    PRIMARY = 0x3498db
    SECONDARY = 0x2b2d31
    SUCCESS = 0x2ecc71
    WARNING = 0xFEE75C
    DANGER = 0xED4245
    BACKGROUND = 0x2b2d31
    ACCENT = 0xEB459E

    @classmethod
    def init_theme(cls, config):
        """Overrides default colors with config values, supporting both old and new formats."""
        theme_data = getattr(config, "THEME", {})
        ui_data = getattr(config, "_ui", {}) # Access legacy UI data
        
        def get_color(name, legacy_name, default):
            # Check new theme dict first, then legacy ui dict
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
