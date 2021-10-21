Benjabot
===

Benjabot is a bot designed to glibly describe songs that may or may not be in the rhythm game _Pump it Up_. It will give
an opinion on the song itself as well as a chart that it may or may not have.

Operation
---
On the machine on which the bot will run, put the bot's auth token in the `TOKEN` environment variable, configure
`config.ini` to taste, and start it up.

**The bot will only respond if directly @mentioned**. Benjabot works by taking the song name, removing everything inside
of parens/square brackets/curly braces, stripping out spaces and special characters and converting to lower case, then
using this formatted name as a seed into lookup tables for both an "opinion" about the song and a random chart
difficulty selection and comment. For instance:

`"Some song [Foo]" -> "somesong" -> "This song is great! That S26 should be an S16"`

If a YouTube link is given, it will yield its "opinion." If a non-YouTube link is given, it will say so and not do any
judgement. If "help" is given, some help text will be given based on whether the person is an Admin or not. For any
other text given to the bot, it will respond with the `empty_response` attribute in `config.py`. (by default this is
":eyes:")

When the bot is given a YouTube link, it will also use a reaction emoji on the message with the YouTube link in
question. This is configured with the`viewed_emote` attribute. (the default is :eye:)

If someone replies to a message and @mentions the bot in their reply, these rules will apply to the message being
replied to. This allows someone to get the bot to respond to a YouTube link without having to re-post said link.

If you want to privately test the bot, add an environment variable called `DEVMODE` with the text `SERVER`, `USER`, or
`FULL`. With `SERVER`, the bot will only respond in the server given in `dev_server` in `config.ini`. In `USER` mode, it
will only  respond to the user in `dev_user`. In `FULL` mode, it will only respond to the user in that server.

**Note**: If the `DEVMODE` env var contains any other text or is blank, the bot will not respond to anybody.

Commands
---
Admins in a server have a few extra commands that the bot will accept:

* "silence": Will cause the bot to not respond to any messages other than admin commands. Saying it again will cause it
to respond normally again.
* "status": Gives the version and tells you whether the bot has been silenced.
* "help": Shows the help text (with some flavor) for these commands.

Non-admins can also use "help," and it will respond with some basic instructions on how to use the bot.
