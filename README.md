# lionbot

_A discord bot for Northernlion's subscriber server that helps keep his subscribers in the loop._

[Join the test server to see a demo of the bot](https://discord.gg/cmwrRaNvPr)

### Features

* Self-service role management via reactions
* YouTube video upload notifications to content-specific channels (e.g. Spelunky 2 goes to #spelunky)
* Twitch live notifications (because Twitch push notifications suck)
* A menu of chat commands for moderators to manage the bot


#### Role Management

* In order for the bot to assign roles, its role must be higher in the role list than all the roles it will need to change (so put it beneath admin/moderator, but above all notifier roles)

Type `!lion roles ` in a channel. The bot will post a message informing users they can react to the message to change their roles.
These roles will be used for @ mentions when videos are posted or NL goes live on Twitch.
If a user does not want to be mentioned anymore, they can re-react to the message to remove the role from themselves. 

### Commands

All commands are only useable by moderators.

* `!lion help` lists the commands available.
* `!lion roles` posts the roles management message. The bot will delete the command message and will delete previous messages if commanded again.
* `!lion add` Adds a new content stream.
* `!lion addcustom` Adds a custom role without an associated content stream.
* `!lion emoji` Changes the emoji of a role.
* `!lion delete` Deletes a content stream.
* `!lion rolecounts` Lists the number of users with each role.

### Development

1. Install Python 3.8.5
2. Clone the repo
3. `pipenv install`
4. `python worker.py` or any other script to run it locally.

Environment variables you will need:
```
DISCORD_TOKEN=
DATABASE_URL=
TWITCH_CLIENT_ID=
TWITCH_CLIENT_SECRET=
WEBHOOK_SECRET=
DOMAIN=
TWITTER_API_KEY=
TWITTER_API_SECRET=
YOUTUBE_API_KEY=
```