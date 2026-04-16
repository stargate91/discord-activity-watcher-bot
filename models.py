"""SQLAlchemy ORM entity models for the activity watcher bot database."""
import datetime

from sqlalchemy import Column, Float, Index, Integer, String, TypeDecorator
from sqlalchemy.orm import DeclarativeBase


# ---------------------------------------------------------------------------
# Custom type decorators – store datetimes/dates as ISO 8601 strings so that
# the existing SQLite database format is preserved exactly.
# ---------------------------------------------------------------------------

class TZDateTime(TypeDecorator):
    """Stores timezone-aware datetimes as ISO 8601 strings (backward-compatible)."""
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, datetime.datetime):
            return value.isoformat()
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return datetime.datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None


class ISODate(TypeDecorator):
    """Stores dates as YYYY-MM-DD strings (backward-compatible)."""
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, (datetime.date, datetime.datetime)):
            return value.isoformat()[:10]
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            if isinstance(value, datetime.date):
                return value
            return datetime.date.fromisoformat(str(value)[:10])
        except (ValueError, TypeError):
            return None


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

class UserActivity(Base):
    """Overall lifetime statistics per user per guild."""
    __tablename__ = "user_activity"

    user_id                 = Column(Integer, primary_key=True)
    guild_id                = Column(Integer, primary_key=True)
    last_active             = Column(TZDateTime)
    returned_at             = Column(TZDateTime, nullable=True)
    message_count           = Column(Integer,   default=0)
    reaction_count          = Column(Integer,   default=0)
    voice_minutes           = Column(Float,     default=0)
    qualified_voice_minutes = Column(Float,     default=0)
    points_total            = Column(Float,     default=0)
    stream_minutes          = Column(Float,     default=0)
    joined_at               = Column(TZDateTime, nullable=True)
    media_count             = Column(Integer,   default=0)
    spotify_minutes         = Column(Float,     default=0)

    __table_args__ = (
        Index("idx_user_activity_guild", "guild_id"),
    )


class DailyStat(Base):
    """Per-channel, per-day activity breakdown for charts and champion calculation."""
    __tablename__ = "daily_stats"

    user_id         = Column(Integer, primary_key=True)
    guild_id        = Column(Integer, primary_key=True)
    channel_id      = Column(Integer, primary_key=True, default=0)
    date            = Column(ISODate, primary_key=True)
    messages        = Column(Integer, default=0)
    reactions       = Column(Integer, default=0)
    voice_minutes   = Column(Float,   default=0)
    points          = Column(Float,   default=0)
    stream_minutes  = Column(Float,   default=0)
    media_count     = Column(Integer, default=0)
    game_minutes    = Column(Float,   default=0)
    spotify_minutes = Column(Float,   default=0)

    __table_args__ = (
        Index("idx_daily_stats_guild_date",       "guild_id", "date"),
        Index("idx_daily_stats_user_guild_date",  "user_id", "guild_id", "date"),
    )


class DailyGameStat(Base):
    """Per-game, per-day playtime used for the Variety Gamer champion."""
    __tablename__ = "daily_game_stats"

    user_id   = Column(Integer, primary_key=True)
    guild_id  = Column(Integer, primary_key=True)
    game_name = Column(String,  primary_key=True)
    date      = Column(ISODate, primary_key=True)
    minutes   = Column(Float,   default=0)


class RoleHistory(Base):
    """Audit log of role assignments and removals made by the bot."""
    __tablename__ = "role_history"

    id        = Column(Integer, primary_key=True, autoincrement=True)
    user_id   = Column(Integer)
    guild_id  = Column(Integer)
    role_name = Column(String)
    action    = Column(String,     default="ADDED")
    timestamp = Column(TZDateTime)

    __table_args__ = (
        Index("idx_role_history_user_guild", "user_id", "guild_id"),
        Index("idx_role_history_time",       "timestamp"),
    )


class GameActivity(Base):
    """Cumulative playtime per game per user, used for Player role management."""
    __tablename__ = "game_activity"

    user_id       = Column(Integer, primary_key=True)
    guild_id      = Column(Integer, primary_key=True)
    role_name     = Column(String,  primary_key=True)
    last_played   = Column(TZDateTime)
    total_minutes = Column(Float,   default=0)
    bot_assigned  = Column(Integer, default=0)

    __table_args__ = (
        Index("idx_game_activity_user_guild", "user_id", "guild_id"),
    )


class VoiceSession(Base):
    """Completed voice channel visit with duration and optional stream detail."""
    __tablename__ = "voice_sessions"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    user_id          = Column(Integer)
    guild_id         = Column(Integer)
    channel_id       = Column(Integer)
    start_time       = Column(TZDateTime)
    end_time         = Column(TZDateTime)
    duration_minutes = Column(Float)
    stream_detail    = Column(String, nullable=True)

    __table_args__ = (
        Index("idx_voice_sessions_user_guild", "user_id", "guild_id"),
        Index("idx_voice_sessions_start",      "start_time"),
    )


class ReactionHistory(Base):
    """Log of every reaction event for social-graph analysis."""
    __tablename__ = "reaction_history"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    user_id        = Column(Integer)
    target_user_id = Column(Integer)
    guild_id       = Column(Integer)
    channel_id     = Column(Integer)
    message_id     = Column(Integer)
    emoji          = Column(String)
    timestamp      = Column(TZDateTime)

    __table_args__ = (
        Index("idx_reaction_history_user_guild", "user_id", "guild_id"),
        Index("idx_reaction_history_time",       "timestamp"),
    )


class MembershipHistory(Base):
    """Log of join and leave events for activity timeline tracking."""
    __tablename__ = "membership_history"

    id        = Column(Integer, primary_key=True, autoincrement=True)
    user_id   = Column(Integer)
    guild_id  = Column(Integer)
    action    = Column(String)
    timestamp = Column(TZDateTime)

    __table_args__ = (
        Index("idx_membership_history_user_guild", "user_id", "guild_id"),
        Index("idx_membership_history_time",       "timestamp"),
    )


class TrackedGame(Base):
    """Games the bot monitors to assign/remove Player roles automatically."""
    __tablename__ = "tracked_games"

    game_substring = Column(String, primary_key=True)
    role_suffix    = Column(String)


class ActiveVoiceSession(Base):
    """In-progress voice session; cleared when the user leaves the channel."""
    __tablename__ = "active_voice_sessions"

    user_id      = Column(Integer, primary_key=True)
    guild_id     = Column(Integer, primary_key=True)
    channel_id   = Column(Integer)
    joined_at    = Column(TZDateTime)
    multiplier   = Column(Float,   default=2.0)
    is_streaming = Column(Integer, default=0)
    stream_name  = Column(String,  nullable=True)


class ActiveGameSession(Base):
    """In-progress game session; cleared when the user stops playing."""
    __tablename__ = "active_game_sessions"

    user_id    = Column(Integer, primary_key=True)
    guild_id   = Column(Integer, primary_key=True)
    game_name  = Column(String,  primary_key=True)
    started_at = Column(TZDateTime)


class ChampionHistory(Base):
    """Weekly champion wins for role management and leaderboard display."""
    __tablename__ = "champion_history"

    id       = Column(Integer, primary_key=True, autoincrement=True)
    user_id  = Column(Integer)
    guild_id = Column(Integer)
    category = Column(String)
    win_date = Column(ISODate)


class VoiceOverlap(Base):
    """Pre-calculated shared voice time between two users (overlap cache)."""
    __tablename__ = "voice_overlaps"

    user_id1        = Column(Integer, primary_key=True)
    user_id2        = Column(Integer, primary_key=True)
    guild_id        = Column(Integer, primary_key=True)
    date            = Column(ISODate, primary_key=True)
    overlap_minutes = Column(Float,   default=0)

    __table_args__ = (
        Index("idx_voice_overlaps_u1_g", "user_id1", "guild_id"),
        Index("idx_voice_overlaps_u2_g", "user_id2", "guild_id"),
    )
