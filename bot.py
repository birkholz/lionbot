import os

import discord

class LionBot(discord.Client):
    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))

    async def on_message(self, message):
        print('Message from {0.author}: {0.content}'.format(message))
        await message.channel.send('Hello')

client = LionBot()
client.run(os.environ.get('DISCORD_TOKEN'))
