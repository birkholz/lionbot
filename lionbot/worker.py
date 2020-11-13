import logging
import os
import re

import discord
from discord import NotFound, PartialEmoji, HTTPException, CustomActivity
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from lionbot.data import Guild, Stream
from lionbot.errors import CommandError
from lionbot.utils import init_sentry

logging.basicConfig(level=logging.INFO)
engine = create_engine(os.environ.get('DATABASE_URL'))
Session = sessionmaker(bind=engine)
session = Session()

init_sentry()


# TODO: Make this configurable without changing code
# Ideally NL would put his YT vids in separate playlists, then we wouldn't have to check the vid names.


class LionBot(discord.Client):
    async def on_ready(self):
        await discord_client.change_presence(activity=CustomActivity("I don't read messages."))
        print('Logged on as {0}!'.format(self.user))

    async def on_guild_join(self, disc_guild):
        self.init_guild(disc_guild)

    def init_twitch_stream(self, guild, disc_guild):
        twitch_channel = "twitch"
        twitch_role = "twitch"
        twitch_description = "NL goes live on Twitch"
        twitch_emoji = "🎥"
        channel = discord.utils.get(disc_guild.text_channels, name=twitch_channel)
        role = discord.utils.get(disc_guild.roles, name=twitch_role)

        twitch_stream = session.query(Stream).filter_by(guild_id=channel.guild.id, channel_id=channel.id).first()
        if twitch_stream:
            twitch_stream.description = twitch_description
            twitch_stream.emoji = twitch_emoji
            twitch_stream.channel_id = channel.id
            twitch_stream.role_id = role.id
        else:
            twitch_stream = Stream(
                guild_id=channel.guild.id,
                description=twitch_description,
                emoji=twitch_emoji,
                channel_id=channel.id,
                role_id=role.id,
            )
        session.add(twitch_stream)
        session.commit()
        guild.twitch_stream_id = twitch_stream.id
        session.add(guild)
        session.commit()

    def init_guild(self, disc_guild):
        guild = session.query(Guild).filter_by(id=disc_guild.id).first()
        if guild is None:
            guild = Guild(id=disc_guild.id, name=disc_guild.name)
            session.add(guild)
        session.commit()

        # Handle twitch stream separately so we can get an ID
        self.init_twitch_stream(guild, disc_guild)

        # Skipping seed data for now, its safer to add each manually

        # for seed in seed_data():
        #     channel = discord.utils.get(disc_guild.text_channels, name=seed['channel'])
        #     role = discord.utils.get(disc_guild.roles, name=seed['role'])
        #     if channel is None:
        #         logging.error(f"Channel not found: {seed['channel']}")
        #         continue
        #     if role is None:
        #         logging.error(f"Role not found: {seed['role']}")
        #         continue
        #
        #     stream = session.query(Stream).filter_by(guild_id=channel.guild.id, channel_id=channel.id).first()
        #     if stream:
        #         stream.description = seed['desc']
        #         stream.emoji = seed['emoji']
        #         stream.title_contains = seed.get('name_contains')
        #         stream.channel_id = channel.id
        #         stream.role_id = role.id
        #     else:
        #         stream = Stream(
        #             guild_id=channel.guild.id,
        #             description=seed['desc'],
        #             emoji=seed['emoji'],
        #             title_contains=seed.get('name_contains'),
        #             channel_id=channel.id,
        #             role_id=role.id,
        #         )
        #     session.add(stream)

        session.commit()

        return guild

    async def toggle_role(self, guild, payload):
        stream = session.query(Stream).filter_by(guild_id=guild.id, emoji=payload.emoji.name).first()
        if not stream:
            logging.error(f"No stream found for emoji: {payload.emoji.name}")

        role = guild.get_role(stream.role_id)
        if role is not None:
            if role in payload.member.roles:
                await payload.member.remove_roles(role, reason="Reacted to role message.")
            else:
                await payload.member.add_roles(role, reason="Reacted to role message.")
        else:
            logging.error(f"Role id {stream.role_id} not found.")

    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.user.id:
            return
        guild = session.query(Guild).filter_by(id=payload.guild_id).first()
        if guild is None or payload.message_id != guild.role_message_id:
            return

        disc_guild = await discord_client.fetch_guild(payload.guild_id)
        if disc_guild is None:
            # We need populated ids
            return

        channel = discord.utils.get(self.get_all_channels(), id=guild.role_channel_id)
        message = await channel.fetch_message(guild.role_message_id)
        await message.remove_reaction(payload.emoji, payload.member)
        await self.toggle_role(disc_guild, payload)

    async def send_role_message(self, channel, guild=None):
        if not guild:
            guild = session.query(Guild).filter_by(id=channel.guild.id).first()
        if not guild:
            guild = self.init_guild(channel.guild)
            if guild is None:
                # Error during init
                return

        if guild.role_message_id:
            old_channel = discord.utils.get(channel.guild.text_channels, id=guild.role_channel_id)
            try:
                old_message = await old_channel.fetch_message(guild.role_message_id)
                await old_message.delete()
            except NotFound:
                pass

        streams = session.query(Stream).filter_by(guild_id=channel.guild.id)
        message_text = 'React to this message to be mentioned when:'
        for stream in streams:
            if stream.emoji_id:
                emoji = f'<:{stream.emoji}:{stream.emoji_id}>'
            else:
                emoji = stream.emoji
            message_text += f'\n{emoji} - {stream.description}'
        role_message = await channel.send(message_text)
        for stream in streams:
            if stream.emoji_id:
                emoji = PartialEmoji(name=stream.emoji, id=stream.emoji_id)
            else:
                emoji = stream.emoji
            await role_message.add_reaction(emoji)

        guild.role_channel_id = channel.id
        guild.role_message_id = role_message.id
        session.commit()

    async def set_stream_emoji(self, message):
        channel, emoji = self.parse_args(message.content, count=2)
        channel_id = re.match('<#(\d+)>', channel).groups()[0]
        emoji_match = re.match('<:(\w+):(\d+)>', emoji)
        if emoji_match:
            emoji_name, emoji_id = emoji_match.groups()
        else:
            emoji_name = emoji
            emoji_id = None
        stream = session.query(Stream).filter_by(channel_id=channel_id).first()
        if not stream:
            raise CommandError('Invalid channel.')
        stream.emoji = emoji_name
        stream.emoji_id = emoji_id
        session.add(stream)
        session.commit()

        channel = discord.utils.get(self.get_all_channels(), id=stream.guild.role_channel_id)
        await self.send_role_message(channel, guild=stream.guild)

    def is_moderator(self, author):
        if author.id == '140333328241786880': # My id
            return True
        for role in author.roles:
            if role.name == 'Moderator':
                return True
        return False

    def parse_args(self, msg, count=1, maxsplits=None):
        if maxsplits:
            args = msg.split(' ', 2+maxsplits)[2:]
        else:
            args = msg.split(' ')[2:]
        if len(args) < count:
            raise CommandError('Not enough arguments.')
        if len(args) > count:
            raise CommandError('Too many arguments.')
        return args

    async def delete_stream(self, message):
        args = self.parse_args(message.content)
        channel_id = self.parse_channel(args[0])

        stream = session.query(Stream).filter_by(channel_id=channel_id).first()
        if not stream:
            raise CommandError('Invalid channel.')

        role_channel_id = stream.guild.role_channel_id
        guild = stream.guild
        session.query(Stream).filter_by(channel_id=channel_id).delete()
        session.commit()

        channel = discord.utils.get(self.get_all_channels(), id=role_channel_id)
        await self.send_role_message(channel, guild=guild)

    def parse_emoji(self, tag):
        name = tag
        e_id = None
        match = re.match('<:(\w+):(\d+)>', tag)
        if match:
            name, e_id = match.groups()
        return name, e_id

    def parse_channel(self, tag):
        return re.match('<#(\d+)>', tag).groups()[0]

    def parse_role(self, tag):
        return re.match('<@&(\d+)>', tag).groups()[0]

    async def create_stream(self, message):
        channel, role, emoji, name = self.parse_args(message.content, count=4, maxsplits=3)
        channel_id = self.parse_channel(channel)
        role_id = self.parse_role(role)
        emoji_name, emoji_id = self.parse_emoji(emoji)
        stream = Stream(
            guild_id=message.guild.id,
            description=f"New episode of {name}",
            title_contains=name,
            emoji=emoji_name,
            emoji_id=emoji_id,
            channel_id=channel_id,
            role_id=role_id
        )
        session.add(stream)
        session.commit()

        guild = session.query(Guild).filter_by(id=message.guild.id).first()
        channel = discord.utils.get(self.get_all_channels(), id=guild.role_channel_id)
        await self.send_role_message(channel, guild=guild)

    async def configure_twitter(self, message):
        channel, role, emoji, title = self.parse_args(message.content, count=4, maxsplits=3)
        channel_id = self.parse_channel(channel)
        role_id = self.parse_role(role)
        emoji_name, emoji_id = self.parse_emoji(emoji)

        stream = Stream(
            guild_id = message.guild.id,
            description=title,
            emoji=emoji_name,
            emoji_id=emoji_id,
            channel_id=channel_id,
            role_id=role_id
        )
        session.add(stream)
        session.commit()

        guild = session.query(Guild).filter_by(id=message.guild.id).first()
        if guild.twitter_stream_id is not None:
            guild.twitter_stream_id = None
            session.add(guild)
            session.commit()
            session.delete(guild.twitter_stream)

        guild.twitter_stream_id = stream.id
        session.add(guild)
        session.commit()

        channel = discord.utils.get(self.get_all_channels(), id=guild.role_channel_id)
        await self.send_role_message(channel, guild=guild)

    async def toggle_pinning(self, channel):
        guild = session.query(Guild).filter_by(id=channel.guild.id).first()
        if not guild:
            return
        new_value = not guild.pinning_enabled
        guild.pinning_enabled = new_value
        session.add(guild)
        session.commit()
        await channel.send(f'Auto-pinning turned: {"ON" if new_value else "OFF" }')

    async def on_message(self, message):
        if message.content == '!lion help':
            if self.is_moderator(message.author):
                msg = 'Commands:\n' \
                      'roles - Posts the role message in the current channel\n' \
                      'add - Adds a new content stream\n' \
                      'emoji - Changes the emoji of a content stream\n' \
                      'delete - Deletes a content stream\n' \
                      'pinning - Toggles auto-pinning\n' \
                      'twitter - Sets up a twitter feed'
                await message.channel.send(msg)

        if message.content == '!lion roles':
            if self.is_moderator(message.author):
                await self.send_role_message(message.channel)

        if message.content[:11] == '!lion emoji':
            if self.is_moderator(message.author):
                try:
                    await self.set_stream_emoji(message)
                except CommandError as e:
                    await message.channel.send(f'ERROR: {e.msg}\nFormat: !lion emoji #channel 👍')
                except HTTPException as e:
                    await message.channel.send('ERROR :(')
                    raise e

        if message.content[:12] == '!lion delete':
            if self.is_moderator(message.author):
                try:
                    await self.delete_stream(message)
                except CommandError as e:
                    await message.channel.send(f'ERROR: {e.msg}\nFormat: !lion delete #channel')

        if message.content[:9] == '!lion add':
            if self.is_moderator(message.author):
                try:
                    await self.create_stream(message)
                except CommandError as e:
                    await message.channel.send(f'ERROR: {e.msg}\nFormat: !lion add #channel @role 👍 Game Name')

        if message.content[:13] == '!lion pinning':
            if self.is_moderator(message.author):
                await self.toggle_pinning(message.channel)

        if message.content[:13] == '!lion twitter':
            if self.is_moderator(message.author):
                try:
                    await self.configure_twitter(message)
                except CommandError as e:
                    await message.channel.send(f'ERROR: {e.msg}\nFormat: !lion twitter #channel @role 👍 Role Description')


discord_client = LionBot()
discord_client.run(os.environ.get('DISCORD_TOKEN'))
