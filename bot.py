import logging
import os

import discord

logging.basicConfig(level=logging.INFO)

fake_db = {}

class LionBot(discord.Client):
    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))

    def populate_role_id(self, roles):
        if fake_db.get('role_id') == None:
            for g_role in roles:
                if g_role.name == "twitch": # make configurable
                    role = g_role
                    fake_db['role_id'] = role.id

    async def on_reaction_add(self, reaction, user):
        if user == self.user or reaction.message.id != fake_db.get('notif_message_id'):
            return
        self.populate_role_id(reaction.message.guild.roles)
        role = reaction.message.guild.get_role(role_id=fake_db['role_id'])
        await user.add_roles(role, reason="Reacted to role message.")

    async def on_reaction_remove(self, reaction, user):
        if reaction.message.id != fake_db.get('notif_message_id'):
            return
        self.populate_role_id(reaction.message.guild.roles)
        role = reaction.message.guild.get_role(role_id=fake_db['role_id'])
        await user.remove_roles(role, reason="Reacted to role message.")

    async def on_message(self, message):
        if message.content == '!lion roles':
            # post message
            notif_message = await message.channel.send(
                'React to this message to subscribe to notifications. Remove your reaction to unsubscribe.'
            )
            fake_db['notif_message_id'] = notif_message.id
            # Add reactions
            await notif_message.add_reaction('👍')
            await message.delete()

client = LionBot()
client.run(os.environ.get('DISCORD_TOKEN'))
