import re
import discord
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
    def is_media(message):
        """
        Detects if a Discord Message object contains media.
        Checks both attachments and content for media links.
        """
        if not message:
            return False
            
        # 1. Check for physical attachments
        if len(message.attachments) > 0:
            return True
            
        # 2. Check content for specific media links (YouTube, TikTok, etc.)
        if ActivityProcessor.contains_media(message.content):
            return True
            
        return False

    @staticmethod
    def get_participation_tier(member):
        """
        Determines the voice activity tier based on current member status 
        (streaming, camera on, or regular voice).
        
        Returns:
            tuple: (multiplier, is_streaming, status_description)
        """
        if not member or not member.voice or not member.voice.channel:
            return 0, False, "Inactive"

        # Explicitly ignore activity in the AFK channel
        if member.voice.channel.id == Config.AFK_CHANNEL_ID:
            return 0, False, "AFK"

        # Check if streaming to the server (Go Live)
        if member.voice.self_stream:
            # Check if they are actually in a game to determine stream name
            stream_name = Config.DEFAULT_STREAM_NAME
            for activity in member.activities:
                if activity.type == discord.ActivityType.playing:
                    stream_name = activity.name
                    break
            return Config.POINTS_STREAM_BONUS + Config.POINTS_VOICE, True, f"Streaming: {stream_name}"
        
        # Camera on bonus
        if member.voice.self_video:
            return Config.POINTS_VOICE + 1, False, "Video On"
            
        # Regular voice activity
        return Config.POINTS_VOICE, False, "Voice"

    @staticmethod
    def get_best_tier(members):
        """
        Calculates the highest participation tier from a group of linked accounts.
        Priority: Streaming > Video On > Voice > Inactive.
        """
        best_tier = 0
        best_streaming = False
        best_desc = "Inactive"

        for m in members:
            tier, streaming, desc = ActivityProcessor.get_participation_tier(m)
            if tier > best_tier:
                best_tier = tier
                best_streaming = streaming
                best_desc = desc
            elif tier == best_tier and tier > 0:
                # Tie-breaker: prioritize streaming if multipliers are identical
                if streaming and not best_streaming:
                    best_streaming = True
                    best_desc = desc
        
        return best_tier, best_streaming, best_desc
