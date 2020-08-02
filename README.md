# lionbot

_A discord bot for Northernlion's subscriber server that helps keep his subscribers in the loop._

### Goals

* [x] Per-series/twitch role management for notifications (via reactions)
* [x] YouTube video upload notifications to per-series channels (e.g. NL tries goes to #nl-tries)
* [x] Twitch live notifications
* [ ] A way for server moderators/admins to manage the bot (currently evaluating solutions)

### Potential future additions

* [ ] Twitch sub duration role management (assigns roles similar to Twitch's sub flair so user's have different username colors based on sub duration. This clashes with username coloring of admin/moderator.)

#### Role Management

* In order for the bot to assign roles, its role must be higher in the role list than all the roles it will need to change (so put it beneath admin/moderator, but above all notifier roles)

Type `!lion roles ` in a channel. The bot will post a message informing users they can react to the message to change their roles.
These roles will be used for @ mentions when videos are posted or NL goes live on Twitch.
If a user does not want to be mentioned anymore, they can re-react to the message to remove the role from themselves. 

### Commands

`!lion roles` posts the roles management message. Only moderators can use this command. The bot will delete the command message and will delete previous messages if commanded again.