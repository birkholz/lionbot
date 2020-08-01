# lionbot

_A discord bot for Northernlion's subscriber server that helps keep his subscribers in the loop._

### Goals

* [ ] Per-series/twitch role management for notifications (via reactions)
* [ ] YouTube video upload notifications to per-series channels (e.g. NL tries goes to #nl-tries)
* [ ] Twitch live notifications

#### Role Management
In the `#roles` channel, the bot has messages posted. On each message, there is a single reaction. Clicking the reaction (i.e., incrementing the reaction) causes the bot to add a role to the user. Clicking the reaction again (to decrement) will remove the role from the user.

### Commands

`!lion roles` posts the roles management message. The bot will delete the command message.