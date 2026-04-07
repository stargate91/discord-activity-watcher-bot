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
        
        # 3. If you share a video or a picture, we give you a big bonus!
        if ActivityProcessor.contains_media(content):
            score += Config.POINTS_MEDIA_BONUS
            
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

        # 1. Check if streaming to the server (Go Live) - This is a high-priority active state!
        if member.voice.self_stream:
            # Check if they are actually in a game to determine stream name
            stream_name = Config.DEFAULT_STREAM_NAME
            for activity in member.activities:
                if activity.type == discord.ActivityType.playing:
                    # If you are playing a game, we show the game name in the log!
                    stream_name = activity.name
                    break
            return Config.POINTS_STREAM_BONUS + Config.POINTS_VOICE, True, f"Streaming: {stream_name}"
        
        # 2. Camera on bonus - Also an active state
        if member.voice.self_video:
            return Config.POINTS_VOICE + 1, False, "Video On"

        # 3. Check for mute/deaf state to determine point rate for passive listeners
        if member.voice.self_deaf or member.voice.deaf:
            # Deafened people hear nothing and get nothing (0 points)
            return 0, False, "Deafened"
            
        if member.voice.self_mute or member.voice.mute:
            # Muted people are just listening, they get half points (1 point)
            return 1, False, "Muted"
            
        # Regular voice activity
        return Config.POINTS_VOICE, False, "Voice"

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
