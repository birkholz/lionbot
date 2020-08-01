# lionbot

_A discord bot for Northernlion's subscriber server that helps keep his subscribers in the loop._

### Goals

* [x] Per-series/twitch role management for notifications (via reactions)
* [ ] YouTube video upload notifications to per-series channels (e.g. NL tries goes to #nl-tries)
* [ ] Twitch live notifications (requires a web process to accept webhooks https://dev.twitch.tv/docs/api/webhooks-guide)
* [ ] A way for server moderators/admins to manage the bot

#### Role Management

Type `!lion roles ` in a channel. The bot will post a message informing users they can react to the message to change their roles.
These roles will be used for @ mentions when videos are posted or NL goes live on Twitch.
If a user does not want to be mentioned anymore, they can remove their reaction from the message to remove the role from themselves. 

### Commands

`!lion roles` posts the roles management message. The bot will delete the command message.