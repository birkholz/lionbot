import logging
import os

import discord

logging.basicConfig(level=logging.INFO)

fake_db = {}

# TODO: Make this configurable without changing code
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
    },
    {
        'desc': 'new episode of The Golden Goblet',
        'role': 'goblet',
        'emoji': '🏆',
        'channel': 'golden-goblet',
    },
    {
        'desc': 'new episode of Binding of Isaac',
        'role': 'isaac',
        'emoji': '👶',
        'channel': 'isaac',
    },
    {
        'desc': 'new episode of Monster Train',
        'role': 'monstertrain',
        'emoji': '🚆',
        'channel': 'monster-train',
    },
    {
        'desc': 'new episode of GeoGuessr',
        'role': 'geo',
        'emoji': '🌎',
        'channel': 'geoguessr',
    },
    {
        'desc': 'new episode of Trackmania',
        'role': 'trackmania',
        'emoji': '🏎',
        'channel': 'trackmania',
    },
    {
        'desc': 'new episode of Super Mega Baseball',
        'role': 'baseball',
        'emoji': '⚾',
        'channel': 'baseball',
    },
    {
        'desc': 'new episode of Check The Wire',
        'role': 'checkthewire',
        'emoji': '🎙',
        'channel': 'check-the-wire',
    },
]


class LionBot(discord.Client):
    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))

    @staticmethod
    def find_role(emoji, roles):
        for stream in streams:
            if emoji == stream['emoji']:
                # TODO: move this to an init step instead of every reaction
                for role in roles:
                    if role.name == stream['role']:
                        return role
        return None

    async def on_reaction_add(self, reaction, user):
        if user == self.user or reaction.message.id != fake_db.get('role_message_id'):
            return

        await reaction.remove(user)

        role = self.find_role(reaction.emoji, reaction.message.guild.roles)
        if role is not None:
            if role in user.roles:
                await user.remove_roles(role, reason="Reacted to role message.")
            else:
                await user.add_roles(role, reason="Reacted to role message.")

    @staticmethod
    async def send_role_message(channel):
        message_text = 'React to this message to be mentioned when:'
        for i, stream in enumerate(streams):
            message_text += f'\n{stream["emoji"]} - {stream["desc"]}'
        role_message = await channel.send(message_text)
        fake_db['role_message_id'] = role_message.id
        for stream in streams:
            await role_message.add_reaction(stream['emoji'])

    async def on_message(self, message):
        if message.content == '!lion roles':
            await message.delete()
            await self.send_role_message(message.channel)

LionBot().run(os.environ.get('DISCORD_TOKEN'))
