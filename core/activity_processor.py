import re
from config_loader import Config

class ActivityProcessor:
    """
    Centralized logic for processing user activities, calculating points, 
    and detecting rich media content.
    """

    @staticmethod
    def calculate_message_points(content):
        """
        Calculates points for a single message based on base points, 
        character length, and media attachments.
        """
        # 1. Base points for any message
        score = Config.POINTS_MESSAGE_BASE
        
        # 2. Add points for length (1 point per 10 characters)
        length_bonus = len(content) / Config.POINTS_MESSAGE_SCALE
        score += min(length_bonus, Config.POINTS_MESSAGE_MAX)
        
        # 3. Add bonus for detecting rich media (YouTube, TikTok, images)
        if ActivityProcessor.contains_media(content):
            score += Config.POINTS_MEDIA_BONUS
            
        return score

    @staticmethod
    def contains_media(content):
        """
        Detects if a message contains links to rich media or image extensions 
        using regex patterns defined in config.json.
        """
        for pattern in Config.MEDIA_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def get_participation_tier(member_id, guild):
        """
        Determines the voice activity tier based on current member status 
        (streaming, camera on, or regular voice).
        
        Returns:
            tuple: (multiplier, is_streaming, status_description)
        """
        member = guild.get_member(member_id)
        if not member or not member.voice:
            return 1, False, "Voice"

        # Check if streaming to the server (Go Live)
        if member.voice.self_stream:
            # Check if they are actually in a game to determine stream name
            stream_name = Config.DEFAULT_STREAM_NAME
            for activity in member.activities:
                if activity.type == "playing":
                    stream_name = activity.name
                    break
            return Config.POINTS_STREAM_BONUS + Config.POINTS_VOICE, True, f"Streaming: {stream_name}"
        
        # Camera on bonus
        if member.voice.self_video:
            return Config.POINTS_VOICE + 1, False, "Video On"
            
        # Regular voice activity
        return Config.POINTS_VOICE, False, "Voice"
