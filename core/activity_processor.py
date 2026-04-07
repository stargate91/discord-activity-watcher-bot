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
    def get_voice_components(member):
        """Calculates the raw components of voice activity for a single member."""
        if not member or not member.voice or not member.voice.channel:
            return 0, 0, 0, None, False, "Inactive"
            
        if member.voice.channel.id == Config.AFK_CHANNEL_ID:
            return 0, 0, 0, None, False, "AFK"

        # 1. Base Logic (Mute/Deaf)
        base = 2 # Normal voice
        desc = "Voice"
        if member.voice.self_deaf or member.voice.deaf:
            base = 0
            desc = "Deafened"
        elif member.voice.self_mute or member.voice.mute:
            base = 1
            desc = "Muted"
            
        # 2. Bonus Logic (Streaming & Video)
        stream_bonus = 0
        video_bonus = 0
        is_streaming = False
        stream_name = None
        
        if member.voice.self_stream:
            is_streaming = True
            stream_bonus = Config.POINTS_STREAM_BONUS
            stream_name = Config.DEFAULT_STREAM_NAME
            for activity in member.activities:
                if activity.type == discord.ActivityType.playing:
                    stream_name = activity.name
                    break
            
        if member.voice.self_video:
            video_bonus = Config.POINTS_VIDEO_BONUS
            
        return base, stream_bonus, video_bonus, stream_name, is_streaming, desc

    @staticmethod
    def get_participation_tier(member):
        """Standard tier calculation for a single member (legacy support/internal use)."""
        base, s_bonus, v_bonus, s_name, is_stream, base_desc = ActivityProcessor.get_voice_components(member)
        
        final_tier = base + s_bonus + v_bonus
        
        # Build description
        status_parts = []
        if is_stream: status_parts.append(f"Streaming: {s_name}")
        if v_bonus > 0: status_parts.append("Video")
        
        if not status_parts:
            desc = base_desc
        else:
            desc = " + ".join(status_parts)
            
        return final_tier, is_stream, desc

    @staticmethod
    def get_best_tier(members):
        """UNIFIED: Aggregates the best possible state across ALL linked accounts."""
        if not members:
            return 0, False, "Inactive"
            
        best_base = 0
        max_stream_bonus = 0
        max_video_bonus = 0
        best_stream_name = None
        has_any_streaming = False
        
        # We collect the best of each component from all accounts
        for m in members:
            base, s_bonus, v_bonus, s_name, is_stream, _ = ActivityProcessor.get_voice_components(m)
            
            if base > best_base:
                best_base = base
                
            if s_bonus > max_stream_bonus:
                max_stream_bonus = s_bonus
                best_stream_name = s_name
                has_any_streaming = True
                
            if v_bonus > max_video_bonus:
                max_video_bonus = v_bonus
                
        # Combine everything
        final_tier = best_base + max_stream_bonus + max_video_bonus
        
        # Build unified description
        status_parts = []
        if has_any_streaming:
            status_parts.append(f"Streaming: {best_stream_name}")
        if max_video_bonus > 0:
            status_parts.append("Video")
            
        if not status_parts:
            # Fallback to base description logic
            desc = "Voice" if best_base == 2 else ("Muted" if best_base == 1 else "Deafened/AFK")
        else:
            desc = " + ".join(status_parts)
            
        return final_tier, has_any_streaming, desc
    
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
