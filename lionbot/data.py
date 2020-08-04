from sqlalchemy import Column, Integer, String, ForeignKey, BigInteger, Index
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
    streams = relationship("Stream", backref="guild", foreign_keys="Stream.guild_id")

    def __repr__(self):
        return f"<Guild {self.id} name='{self.name}'>"


class Stream(Base):
    __tablename__ = 'streams'
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, ForeignKey('guilds.id'))
    description = Column(String) # The description given in the role message
    emoji = Column(String) # The unicode emoji of the reaction on the role message
    title_contains = Column(String) # The text to look for in a YouTube title to associate it with this stream
    # Populated from Discord's API
    role_id = Column(BigInteger)
    channel_id = Column(BigInteger)

    def __repr__(self):
        return f"<Stream {self.id} description='{self.description}'>"


class Video(Base):
    """
    Saves the videos received by YouTube's webhook to prevent reposts
    """
    __tablename__ = 'videos'
    id = Column(String, primary_key=True) # YouTube's video ID
    guild_id = Column(BigInteger, ForeignKey('guilds.id'))

    Index('videos_id_guild_id', 'id', 'guild_id', unique=True)


class TwitchStream(Base):
    """
    Saves a Twitch stream so we don't repost a stream when it updates.
    Twitch's webhooks do not differentiate between new streams and game name updates.
    """
    __tablename__ = 'twitch_streams'
    id = Column(BigInteger, primary_key=True)
    guild_id = Column(BigInteger, ForeignKey('guilds.id'))

    Index('twitch_streams_id_guild_id', 'id', 'guild_id', unique=True)


def seed_data():
    return [
        {
            'desc': 'new episode of Northernlion Tries',
            'role': 'nltries',
            'emoji': '🎮',
            'channel': 'northernlion-tries',
            'name_contains': '(Northernlion Tries)',
        },
        {
            'desc': 'new episode of The Golden Goblet',
            'role': 'goblet',
            'emoji': '🏆',
            'channel': 'golden-goblet',
            'name_contains': '(Golden Goblet',
        },
        {
            'desc': 'new episode of Binding of Isaac',
            'role': 'isaac',
            'emoji': '👶',
            'channel': 'isaac',
            'name_contains': 'The Binding of Isaac:',
        },
        {
            'desc': 'new episode of Monster Train',
            'role': 'monstertrain',
            'emoji': '🚆',
            'channel': 'monster-train',
            'name_contains': 'Monster Train (Episode',
        },
        {
            'desc': 'new episode of GeoGuessr',
            'role': 'geo',
            'emoji': '🌎',
            'channel': 'geoguessr',
            'name_contains': 'Geoguessr with Sinvicta'
        },
        {
            'desc': 'new episode of Trackmania',
            'role': 'trackmania',
            'emoji': '🏎',
            'channel': 'trackmania',
            'name_contains': 'Trackmania TOTD',
        },
        {
            'desc': 'new episode of Super Mega Baseball',
            'role': 'baseball',
            'emoji': '⚾',
            'channel': 'baseball',
            'name_contains': 'Super Mega Baseball 3',
        },
        {
            'desc': 'new episode of Check The Wire',
            'role': 'checkthewire',
            'emoji': '🎙',
            'channel': 'check-the-wire',
            'name_contains': 'Check the Wire #'
        },
    ]