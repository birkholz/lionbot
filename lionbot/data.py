from sqlalchemy import Column, Integer, String, ForeignKey, BigInteger, Index, Boolean, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Guild(Base):
    # Maps 1 to 1 with a Discord Guild
    __tablename__ = 'guilds'
    id = Column(BigInteger, primary_key=True, autoincrement=False) # populated from Discord Guild id
    name = Column(String)
    role_channel_id = Column(BigInteger, nullable=True)
    role_message_id = Column(BigInteger, nullable=True)
    twitch_stream_id = Column(Integer, ForeignKey('streams.id'))
    twitch_stream = relationship("Stream", foreign_keys=twitch_stream_id)
    twitter_stream_id = Column(Integer, ForeignKey('streams.id'), nullable=True)
    twitter_stream = relationship("Stream", foreign_keys=twitter_stream_id)
    streams = relationship("Stream", backref="guild", foreign_keys="Stream.guild_id")
    pinning_enabled = Column(Boolean, server_default=text("TRUE"), nullable=False)
    twitter_replies = Column(Boolean, server_default=text("TRUE"), nullable=False)
    playlist_links = Column(Boolean, server_default=text("FALSE"), nullable=False)

    def __repr__(self):
        return f"<Guild {self.id} name='{self.name}'>"


class Stream(Base):
    """
    Holds the info for a subscribe-able role.
    Streams with `title_contains` are used to match YouTube videos with a channel/role.
    Twitch and Twitter streams do not have `title_contains`, and have FKs from Guild.
    Custom roles do not have `title_contains` or `channel_id`.
    """
    __tablename__ = 'streams'
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, ForeignKey('guilds.id'))
    description = Column(String) # The description given in the role message
    emoji = Column(String) # The unicode emoji of the reaction on the role message
    emoji_id = Column(BigInteger, nullable=True) # For non-default emojis
    title_contains = Column(String) # The text to look for in a YouTube title to associate it with this stream
    playlist_id = Column(String)
    # Populated from Discord's API
    role_id = Column(BigInteger)
    channel_id = Column(BigInteger)
    latest_message_id = Column(BigInteger) # The ID of the latest message posted in the channel

    def __repr__(self):
        return f"<Stream {self.id} description='{self.description}'>"


class Video(Base):
    """
    Saves the videos received by YouTube's webhook to prevent reposts
    """
    __tablename__ = 'videos'
    id = Column(Integer, primary_key=True)
    video_id = Column(String) # YouTube's video ID
    guild_id = Column(BigInteger, ForeignKey('guilds.id'))

    Index('videos_video_id_guild_id', 'video_id', 'guild_id', unique=True)


class TwitchStream(Base):
    """
    Saves a Twitch stream so we don't repost a stream when it updates.
    Twitch's webhooks do not differentiate between new streams and game name updates.
    """
    __tablename__ = 'twitch_streams'
    id = Column(Integer, primary_key=True)
    twitch_id = Column(BigInteger)
    guild_id = Column(BigInteger, ForeignKey('guilds.id'))

    Index('twitch_streams_twitch_id_guild_id', 'twitch_id', 'guild_id', unique=True)


def seed_data():
    return [
        # {
        #     'desc': 'new episode of Northernlion Tries',
        #     'role': 'nltries',
        #     'emoji': '🎮',
        #     'channel': 'northernlion-tries',
        #     'name_contains': '(Northernlion Tries)',
        # },
        # {
        #     'desc': 'new episode of The Golden Goblet',
        #     'role': 'goblet',
        #     'emoji': '🏆',
        #     'channel': 'golden-goblet',
        #     'name_contains': '(Golden Goblet',
        # },
        {
            'desc': 'new episode of Binding of Isaac',
            'role': 'isaac',
            'emoji': '👶',
            'channel': 'isaac',
            'name_contains': 'The Binding of Isaac:',
        },
        # {
        #     'desc': 'new episode of Monster Train',
        #     'role': 'monstertrain',
        #     'emoji': '🚆',
        #     'channel': 'monster-train',
        #     'name_contains': 'Monster Train (Episode',
        # },
        # {
        #     'desc': 'new episode of GeoGuessr',
        #     'role': 'geo',
        #     'emoji': '🌎',
        #     'channel': 'geoguessr',
        #     'name_contains': 'Geoguessr with Sinvicta'
        # },
        # {
        #     'desc': 'new episode of Trackmania',
        #     'role': 'trackmania',
        #     'emoji': '🏎',
        #     'channel': 'trackmania',
        #     'name_contains': 'Trackmania TOTD',
        # },
        # {
        #     'desc': 'new episode of Super Mega Baseball',
        #     'role': 'baseball',
        #     'emoji': '⚾',
        #     'channel': 'baseball',
        #     'name_contains': 'Super Mega Baseball 3',
        # },
        # {
        #     'desc': 'new episode of Check The Wire',
        #     'role': 'checkthewire',
        #     'emoji': '🎙',
        #     'channel': 'check-the-wire',
        #     'name_contains': 'Check the Wire #',
        # },
        {
            'desc': 'new episode of Fall Guys',
            'role': 'fallguys',
            'emoji': '🤸',
            'channel': 'fall-guys',
            'name_contains': '| Fall Guys',
        },
        {
            'desc': 'new episode of Spelunky 2',
            'role': ''
        }
    ]