import logging
import os

import discord
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from data import Guild, seed_data, Stream

logging.basicConfig(level=logging.INFO)
engine = create_engine(os.environ.get('DATABASE_URL'))
Session = sessionmaker(bind=engine)
session = Session()


# TODO: Make this configurable without changing code
# Ideally NL would put his YT vids in separate playlists, then we wouldn't have to check the vid names.


class LionBot(discord.Client):
    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))

    async def on_guild_join(self, disc_guild):
        self.init_guild(disc_guild)

    def init_guild(self, disc_guild):
        guild = session.query(Guild).filter_by(id=disc_guild.id).first()
        if guild is None:
            guild = Guild(id=disc_guild.id, name=disc_guild.name)
            session.add(guild)

        for seed in seed_data():
            channel = discord.utils.get(disc_guild.text_channels, name=seed['channel'])
            role = discord.utils.get(disc_guild.roles, name=seed['role'])
            if channel is None:
                logging.error(f"Channel not found: {seed['channel']}")
                continue
            if role is None:
                logging.error(f"Role not found: {seed['role']}")
                continue

            stream = session.query(Stream).filter_by(guild_id=channel.guild.id, channel_id=channel.id).first()
            if stream:
                stream.description = seed['desc']
                stream.emoji = seed['emoji']
                stream.title_contains = seed.get('name_contains')
                stream.channel_id = channel.id
                stream.role_id = role.id
            else:
                stream = Stream(
                    guild_id=channel.guild.id,
                    description=seed['desc'],
                    emoji=seed['emoji'],
                    title_contains=seed.get('name_contains'),
                    channel_id=channel.id,
                    role_id=role.id,
                )
            session.add(stream)

        session.commit()

        return guild

    async def toggle_role(self, guild, payload):
        stream = session.query(Stream).filter_by(emoji=payload.emoji.name).first()
        if not stream:
            logging.error(f"No stream found for emoji: {payload.emoji.name}")
        role = guild.get_role(stream.role_id)
        if role is not None:
            if role in payload.member.roles:
                await payload.member.remove_roles(role, reason="Reacted to role message.")
            else:
                await payload.member.add_roles(role, reason="Reacted to role message.")

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

    async def send_role_message(self, channel):
        guild = session.query(Guild).filter_by(id=channel.guild.id).first()
        if guild is None:
            guild = self.init_guild(channel.guild)
            if guild is None:
                # Error during init
                return

        if guild.role_message_id:
            old_channel = discord.utils.get(channel.guild.text_channels, id=guild.role_channel_id)
            old_message = await old_channel.fetch_message(guild.role_message_id)
            await old_message.delete()

        streams = session.query(Stream).filter_by(guild_id=channel.guild.id)
        message_text = 'React to this message to be mentioned when:'
        for stream in streams:
            message_text += f'\n{stream.emoji} - {stream.description}'
        role_message = await channel.send(message_text)
        for stream in streams:
            await role_message.add_reaction(stream.emoji)

        guild.role_channel_id = channel.id
        guild.role_message_id = role_message.id
        session.commit()

    async def on_message(self, message):
        if message.content == '!lion roles':
            await message.delete()
            await self.send_role_message(message.channel)


discord_client = LionBot()
discord_client.run(os.environ.get('DISCORD_TOKEN'))
