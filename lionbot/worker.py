import logging
import os
import re
from collections import defaultdict, OrderedDict

import discord
from discord import NotFound, PartialEmoji, CustomActivity, AllowedMentions, Intents, Embed
from sentry_sdk import capture_exception
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from lionbot.data import Guild, Stream
from lionbot.errors import CommandError
from lionbot.utils import init_sentry

logging.basicConfig(level=logging.INFO)

database_uri = os.getenv("DATABASE_URL")  # or other relevant config var
if database_uri and database_uri.startswith("postgres://"):
    database_uri = database_uri.replace("postgres://", "postgresql://", 1)
engine = create_engine(database_uri)
Session = sessionmaker(bind=engine)
session = Session()

init_sentry()


class LionBot(discord.Client):
    COMMANDS = OrderedDict([
        ("add", {
            "name": "add",
            "desc": "Adds a new content stream for YouTube videos",
            "format": "`!lion add #channel @role 👍 Game Name`"
        }),
        ("addcustom", {
            "name": "addcustom",
            "desc": "Adds a custom role",
            "format": "`!lion addcustom @role 👍 Role Description`"
        }),
        ("playlist", {
            "name": "playlist",
            "desc": "Sets the playlist for a content stream",
            "format": "`!lion playlist @role playlist_id_1234`"
        }),
        ("roles", {
            "name": "roles",
            "desc": "Posts the role message in the current channel",
            "format": "`!lion roles`"
        }),
        ("delete", {
            "name": "delete",
            "desc": "Deletes a content stream/role",
            "format": "`!lion delete @role`"
        }),
        ("emoji", {
            "name": "emoji",
            "desc": "Changes the emoji of a content stream/role",
            "format": "`!lion emoji @role 👍`"
        }),
        ("pinning", {
            "name": "pinning",
            "desc": "Toggles auto-pinning of YouTube videos",
            "format": "`!lion pinning`"
        }),
        ("playlistlinks", {
           "name": "playlistlinks",
            "desc": "Toggles posting video links with their playlist",
            "format": "`!lion playlistlinks`"
        }),
        ("count", {
            "name": "count",
            "desc": "Returns the count of users with a role",
            "format": "`!lion count @role`"
        }),
        ("rolecounts", {
            "name": "rolecounts",
            "desc": "Returns a list with the number of members that have each role",
            "format": "`!lion rolecounts`"
        }),
        ("reloadroles", {
            "name": "reloadroles",
            "desc": "Reloads the roles message in case something went wrong",
            "format": "`!lion reloadroles`"
        }),
        ("countroleusers", {
            "name": "countroleusers",
            "desc": "Counts the number of users with any bot-assigned role",
            "format": "`!lion countroleusers`"
        })
    ])

    async def on_ready(self):
        state = "See #roles for info"
        await discord_client.change_presence(activity=CustomActivity('Custom Status', state=state))
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
            return

        role = guild.get_role(stream.role_id)
        if role is not None:
            logging.info(f"Toggling role id: {stream.role_id} for member: {payload.member.id}")
            if role in payload.member.roles:
                await payload.member.remove_roles(role, reason="Reacted to role message.")
            else:
                await payload.member.add_roles(role, reason="Reacted to role message.")
        else:
            logging.error(f"Role id {stream.role_id} not found.")

    async def on_raw_reaction_add(self, payload, is_retry=False):
        if payload.user_id == self.user.id:
            return
        try:
            guild = session.query(Guild).filter_by(id=payload.guild_id).first()
        except OperationalError:
            session.rollback()
            if not is_retry:
                await self.on_raw_reaction_add(payload, is_retry=True)
            return
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

        streams = session.query(Stream).filter_by(guild_id=guild.id).order_by(Stream.id)
        twitch_stream = None
        content_streams = []
        custom_roles = []
        for stream in streams:
            if stream.id == guild.twitch_stream_id:
                twitch_stream = stream
            elif stream.title_contains is None and stream.playlist_id is None:
                custom_roles.append(stream)
            else:
                content_streams.append(stream)

        # Always put twitch first
        content_streams = [twitch_stream,] + content_streams

        # Build message
        message_text = 'React to this message to be mentioned when:'
        for stream in content_streams:
            if stream.emoji_id:
                emoji = f'<:{stream.emoji}:{stream.emoji_id}>'
            else:
                emoji = stream.emoji
            message_text += f'\n{emoji} - {stream.description}'

        # get custom roles
        if custom_roles:
            message_text += '\n\nOr manage your other roles:'
            for stream in custom_roles:
                if stream.emoji_id:
                    emoji = f'<:{stream.emoji}:{stream.emoji_id}>'
                else:
                    emoji = stream.emoji
                # Custom roles show the role given
                role = f'<@&{stream.role_id}>'
                message_text += f'\n{emoji} - {role} {stream.description}'

        role_message = await channel.send(message_text, allowed_mentions=AllowedMentions.none())

        # Commit channel and message to DB before adding reactions, as that's usually when errors occur
        guild.role_channel_id = channel.id
        guild.role_message_id = role_message.id
        session.commit()

        # Add Reactions
        for stream in streams:
            if stream.emoji_id:
                emoji = PartialEmoji(name=stream.emoji, id=stream.emoji_id)
            else:
                emoji = stream.emoji
            await role_message.add_reaction(emoji)

    async def reload_roles(self, message):
        guild = session.query(Guild).filter_by(id=message.guild.id).first()
        channel = discord.utils.get(self.get_all_channels(), id=guild.role_channel_id)
        await self.send_role_message(channel, guild=guild)

    async def set_stream_emoji(self, message):
        role, emoji = self.parse_args(message.content, count=2)
        role_id = self.parse_role(role)
        emoji_match = re.match('<:(\w+):(\d+)>', emoji)
        if emoji_match:
            emoji_name, emoji_id = emoji_match.groups()
        else:
            emoji_name = emoji
            emoji_id = None
        stream = session.query(Stream).filter_by(role_id=role_id).first()
        if not stream:
            raise CommandError('Invalid channel.')
        stream.emoji = emoji_name
        stream.emoji_id = emoji_id
        session.add(stream)
        session.commit()

        channel = discord.utils.get(self.get_all_channels(), id=stream.guild.role_channel_id)
        await self.send_role_message(channel, guild=stream.guild)

    def is_moderator(self, author):
        if str(author.id) == '140333328241786880': # My id
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

    async def delete_stream(self, message):
        args = self.parse_args(message.content)
        role_id = self.parse_role(args[0])

        stream = session.query(Stream).filter_by(role_id=role_id).first()
        if not stream:
            raise CommandError('Invalid channel.')

        role_channel_id = stream.guild.role_channel_id
        guild = stream.guild
        session.query(Stream).filter_by(role_id=role_id).delete()
        session.commit()

        channel = discord.utils.get(self.get_all_channels(), id=role_channel_id)
        await self.send_role_message(channel, guild=guild)

    async def create_stream(self, message):
        channel, role, emoji, name = self.parse_args(message.content, count=4, maxsplits=3)
        channel_id = self.parse_channel(channel)
        role_id = self.parse_role(role)
        emoji_name, emoji_id = self.parse_emoji(emoji)
        if not emoji_name or emoji_name == '':
            raise CommandError('Unable to read emoji. Please try again.')
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

    async def create_custom_role(self, message):
        role, emoji, description = self.parse_args(message.content, count=3, maxsplits=2)
        role_id = self.parse_role(role)
        emoji_name, emoji_id = self.parse_emoji(emoji)
        if not emoji_name or emoji_name == '':
            raise CommandError('Unable to read emoji. Please try again.')
        stream = Stream(
            guild_id=message.guild.id,
            description=description,
            emoji=emoji_name,
            emoji_id=emoji_id,
            role_id=role_id
        )
        session.add(stream)
        session.commit()

        guild = session.query(Guild).filter_by(id=message.guild.id).first()
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

    async def count_role(self, message):
        role = self.parse_args(message.content, count=1)[0]
        role_id = self.parse_role(role)

        guild = message.channel.guild
        stream = session.query(Stream).filter_by(guild_id=guild.id, role_id=role_id).first()
        if not stream:
            raise CommandError('Unknown role.')

        count = 0
        for member in guild.members:
            for role in member.roles:
                if str(role.id) == str(role_id):
                    count += 1

        message_text = f'Users with role <@&{role_id}>: {count}'
        await message.channel.send(message_text, allowed_mentions=AllowedMentions.none())

    async def count_roles(self, message):
        role_counts = defaultdict(lambda: 0)
        for member in message.channel.guild.members:
            for role in member.roles:
                role_counts[role.name] += 1

        ordered = OrderedDict(sorted(role_counts.items(), key=lambda r: r[1], reverse=True))

        embed = Embed(title="Role Counts")
        for role_name, count in ordered.items():
            if role_name in [
                "Twitch Subscriber",
                "Twitch Subscriber: Tier 1",
                "Twitch Subscriber: Tier 2",
                "Twitch Subscriber: Tier 3",
                "Moderator",
                "Admin",
                "LionBot"
            ]:
                continue
            embed.add_field(name=role_name, value=str(count))

        await message.channel.send(embed=embed, allowed_mentions=AllowedMentions.none())

    async def count_role_users(self, message):
        role_ids_iter = session.query(Stream).filter_by(guild_id=message.channel.guild.id).values(Stream.role_id)
        # Convert query iterator to dict for fast lookups
        role_ids = dict([(i[0], None) for i in role_ids_iter])

        user_count = 0

        def member_has_a_role(member):
            for role in member.roles:
                if role.id in role_ids:
                    return True
            return False

        for member in message.channel.guild.members:
            if member_has_a_role(member):
                user_count += 1

        await message.channel.send(f"Users with bot-assigned roles: **{user_count}**")

    async def help_message(self, message):
        embed = Embed(title="LionBot Commands")

        for command in self.COMMANDS.values():
            value = f"{command['desc']}\nFormat: {command['format'].replace(' ', ' ')}" # replace space with nb-space
            embed.add_field(name=command["name"], value=value)

        await message.channel.send(embed=embed, allowed_mentions=AllowedMentions.none())

    def command_help_embed(self, name):
        command = self.COMMANDS[name]
        desc = f"{command['desc']}\nFormat: {command['format'].replace(' ', ' ')}"  # replace space with nb-space
        embed = Embed(title=name, description=desc)
        return embed

    async def set_stream_playlist(self, message):
        role, playlist_id = self.parse_args(message.content, count=2, maxsplits=1)
        role_id = self.parse_role(role)

        guild = message.channel.guild
        stream = session.query(Stream).filter_by(guild_id=guild.id, role_id=role_id).first()
        if not stream:
            raise CommandError('Unknown role.')

        stream.playlist_id = playlist_id
        stream.title_contains = None
        session.add(stream)
        session.commit()
        await message.channel.send(f"Playlist set for role <@&{role_id}>")

    async def toggle_playlist_links(self, message):
        guild_id = message.channel.guild.id
        guild = session.query(Guild).filter_by(id=guild_id).first()
        guild.playlist_links = not guild.playlist_links
        session.add(guild)
        session.commit()

        states = {True: 'on', False: 'off'}
        await message.channel.send(f"Turning playlist links: {states[guild.playlist_links]}")

    async def on_message(self, message):
        try:
            await self.parse_message(message)
        except Exception as e:
            capture_exception(e)
            raise e

    async def parse_message(self, message):
        if message.content == '!lion roles':
            if self.is_moderator(message.author):
                await self.send_role_message(message.channel)

        elif message.content[:11] == '!lion emoji':
            if self.is_moderator(message.author):
                try:
                    await self.set_stream_emoji(message)
                except CommandError as e:
                    await message.channel.send(f'ERROR: {e.msg}\nFormat: `!lion emoji @role 👍`')

        elif message.content[:12] == '!lion delete':
            if self.is_moderator(message.author):
                try:
                    await self.delete_stream(message)
                except CommandError as e:
                    await message.channel.send(f'ERROR: {e.msg}\nFormat: `!lion delete @role`')

        elif message.content[:15] == '!lion addcustom':
            if self.is_moderator(message.author):
                try:
                    await self.create_custom_role(message)
                except CommandError as e:
                    await message.channel.send(f'ERROR: {e.msg}\nFormat: `!lion addcustom @role 👍 Role Description`')

        elif message.content[:9] == '!lion add':
            if self.is_moderator(message.author):
                try:
                    await self.create_stream(message)
                except CommandError as e:
                    await message.channel.send(f'ERROR: {e.msg}\nFormat: `!lion add #channel @role 👍 Game Name`')

        elif message.content == '!lion pinning':
            if self.is_moderator(message.author):
                await self.toggle_pinning(message.channel)

        elif message.content == '!lion countroleusers':
            if self.is_moderator(message.author):
                await self.count_role_users(message)

        elif message.content[:11] == '!lion count':
            if self.is_moderator(message.author):
                try:
                    await self.count_role(message)
                except CommandError as e:
                    await message.channel.send(f'ERROR: {e.msg}\nFormat: `!lion count @role`')

        elif message.content == '!lion rolecounts':
            if self.is_moderator(message.author):
                await self.count_roles(message)

        elif message.content == '!lion playlistlinks':
            if self.is_moderator(message.author):
                await self.toggle_playlist_links(message)

        elif message.content[:14] == '!lion playlist':
            if self.is_moderator(message.author):
                try:
                    await self.set_stream_playlist(message)
                except CommandError as e:
                    await message.channel.send(f'ERROR: {e.msg}\nFormat: `!lion playlist @role playlist_id_1234`')

        elif message.content == '!lion reloadroles':
            if self.is_moderator(message.author):
                await self.reload_roles(message)

        elif message.content[:5] == '!lion':
            if self.is_moderator(message.author):
                await self.help_message(message)



intents = Intents.default()
intents.members = True
discord_client = LionBot(intents=intents)
discord_client.run(os.environ.get('DISCORD_TOKEN'))
