import logging
import os

import discord
import redis

logging.basicConfig(level=logging.INFO)
redis_client = redis.Redis.from_url("redis://localhost/")
discord_client = None
# TODO: Make this configurable without changing code
# Ideally NL would put his YT vids in separate playlists, then we wouldn't have to check the vid names.
streams = [
    {
        'desc': 'NL goes live on Twitch',
        'role': 'twitch',
        'emoji': '🎥',
        'channel': 'twitch',
    },
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
        'name_contains': 'Geoguessr With Sinvicta'
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


class LionBot(discord.Client):
    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))

    @staticmethod
    def find_role(emoji, roles):
        for stream in streams:
            if emoji.name == stream['emoji']:
                for role in roles:
                    if role.name == stream['role']:
                        return role
        return None

    async def toggle_role(self, guild, payload):
        role = self.find_role(payload.emoji, guild.roles)
        if role is not None:
            if role in payload.member.roles:
                await payload.member.remove_roles(role, reason="Reacted to role message.")
            else:
                await payload.member.add_roles(role, reason="Reacted to role message.")

    @property
    def role_message_id(self):
        return int(redis_client.get('role_message_id'))

    @property
    def role_channel_id(self):
        return int(redis_client.get('role_channel_id'))

    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.user.id or payload.message_id != self.role_message_id:
            return

        guild = await discord_client.fetch_guild(payload.guild_id)
        if guild is not None:
            channel = discord.utils.get(self.get_all_channels(), id=self.role_channel_id)
            message = await channel.fetch_message(self.role_message_id)
            await message.remove_reaction(payload.emoji, payload.member)
            await self.toggle_role(guild, payload)

    async def send_role_message(self, channel):
        message_text = 'React to this message to be mentioned when:'
        for i, stream in enumerate(streams):
            message_text += f'\n{stream["emoji"]} - {stream["desc"]}'
        role_message = await channel.send(message_text)
        redis_client.set('role_channel_id', channel.id)
        redis_client.set('role_message_id', role_message.id)
        for stream in streams:
            await role_message.add_reaction(stream['emoji'])

    async def on_message(self, message):
        if message.content == '!lion roles':
            await message.delete()
            await self.send_role_message(message.channel)

discord_client = LionBot()
discord_client.run(os.environ.get('DISCORD_TOKEN'))
