import re
import discord
from config_loader import Config

class ActivityProcessor:
    """
    This is where we calculate all the points people get for being active in the server!
    """

    @staticmethod
    def calculate_message_points(content):
        """
        This function decides how many points a message is worth. 
        Longer messages and links to cool media get more points!
        """
        # 1. You get some basic points just for saying anything!
        score = Config.POINTS_MESSAGE_BASE
        
        # 2. You get extra points for writing long messages (1 point for every 10 characters)
        length_bonus = len(content) / Config.POINTS_MESSAGE_SCALE
        score += min(length_bonus, Config.POINTS_MESSAGE_MAX)
        
        return score

    @staticmethod
    def contains_media(content):
        """
        We use this to check if a message has a link to a video or an image based on our secret list!
        """
        for pattern in Config.MEDIA_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def is_media(message):
        """
        This checks if a Discord message has an actual file attached or a link to a website with media!
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
        This checks what you are doing in voice. Are you streaming? Is your camera on? 
        This decides how many points you get every minute!
        """
        if not member or not member.voice or not member.voice.channel:
            return 0, False, "Inactive"

        # Explicitly ignore activity in the AFK channel
        if member.voice.channel.id == Config.AFK_CHANNEL_ID:
            return 0, False, "AFK"

        # Use additive model for better granularity
        base_points = 2 # Normal voice
        is_streaming = False
        desc = "Voice"
        
        # 1. Base Logic (Mute/Deaf)
        if member.voice.self_deaf or member.voice.deaf:
            base_points = 0
            desc = "Deafened"
        elif member.voice.self_mute or member.voice.mute:
            base_points = 1
            desc = "Muted"
            
        # 2. Bonus Logic (Streaming/Video) - These are additive to the base!
        bonus = 0
        if member.voice.self_stream:
            is_streaming = True
            bonus = Config.POINTS_STREAM_BONUS
            # Determine stream name
            stream_name = Config.DEFAULT_STREAM_NAME
            for activity in member.activities:
                if activity.type == discord.ActivityType.playing:
                    stream_name = activity.name
                    break
            desc = f"Streaming: {stream_name}"
        elif member.voice.self_video:
            bonus = Config.POINTS_VIDEO_BONUS
            desc = "Video On"
            
        final_tier = base_points + bonus
        return final_tier, is_streaming, desc

    @staticmethod
    def get_best_tier(members):
        """
        If you have two accounts logged in, we check which one is doing more cool stuff and use that for your points!
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
    
    @staticmethod
    def is_qualified(member):
        """
        This checks if you are 'active' enough to earn the Basic Member role. 
        You can't be muted, deafened, or alone in a channel!
        """
        if not member or member.bot:
            return False
            
        # 1. Role Exclusion Check
        if any(role.id in Config.BASIC_MEMBER_EXCLUDED_ROLES for role in member.roles):
            return False
            
        # 2. Voice State Check (Mute/Deaf)
        if not member.voice or not member.voice.channel:
            return False
            
        if member.voice.self_mute or member.voice.mute or member.voice.self_deaf or member.voice.deaf:
            return False
            
        # 3. Not Alone Check (at least one other non-bot member in the same channel)
        other_humans = [m for m in member.voice.channel.members if not m.bot and m.id != member.id]
        if not other_humans:
            return False
            
        return True
