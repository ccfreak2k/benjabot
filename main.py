import configparser
import logging
import os
from random import seed, choice, randint, randrange
import re
import sys

import discord
import youtube_dl.utils
from youtube_dl import YoutubeDL

import responses


class Logger(object):
    """
    A basic logging object.
    """
    @staticmethod
    def debug(msg: str):
        print(f"[DBG] {msg}")

    @staticmethod
    def warning(msg: str):
        print(f"[WRN] {msg}")

    @staticmethod
    def error(msg: str):
        print(f"[ERR] {msg}")


logger = Logger()
ydl_opts = {"logger": Logger(), "ignoreerrors": True}
ydl = YoutubeDL(ydl_opts)
# Regex for finding the youtube URL
yts = re.compile(r'http[s]?://(\w+\.)?(youtube\.com|youtu\.be)/\S+')
# Regex for finding any URL
ure = re.compile(r'http[s]?://\S+')
# Regex for finding @mentions in message content
mre = re.compile(r'<@[!&]\d+>')
# Regex to remove [this] or (this) or {this} from titles.
tre = re.compile(r'\[[^]]*]|\([^)]*\)|{[^}]*}')
# Regex to strip non-alphanumeric characters from titles.
fre = re.compile(r'[\W_]+')


class Benjabot(discord.Client):
    # Whether the bot has been silenced.
    # TODO: use an array to silence in different servers independently
    silence: bool = False
    # Whether the bot has had on_ready() called at least once.
    readied: bool = False
    # The version of the bot.
    version: str = "1.0.0"

    def __init__(self, **options):
        logging.debug('Benjabot initing...')
        # Set up the defaults
        super().__init__(**options)
        cfg = configparser.ConfigParser()
        cfg.read('config.ini')
        self.dev_server = cfg.getint('Dev', 'dev_server', fallback=None)
        if not self.dev_server:
            logger.warning('No dev server specified; ignore this if not using dev mode.')
        self.dev_user = cfg.getint('Dev', 'dev_user', fallback=None)
        if not self.dev_user:
            logger.warning('No dev user specified; ignore this if not using dev mode.')
        # The actual dev mode is retrieved from the env var.
        self.dev_mode = os.getenv('DEVMODE')
        self.bonus_chance_factor = cfg.getint('Responses', 'bonus_chance_factor', fallback=6)
        self.viewed_emote = cfg.get('Responses', 'viewed_emote', fallback='👁')
        self.empty_response = cfg.get('Responses', 'empty_response', fallback='👀')
        logging.debug('done initing')

    async def on_ready(self):
        logging.debug('on_ready()')
        if not self.readied:
            print(f"Logged in as {bot.user} (ID: {bot.user.id})")
            if self.dev_mode:
                logger.debug(f"Dev mode enabled: {self.dev_mode}")
                # Resolve the dev server and user IDs for printing to the log.
                server: discord.Guild = next((x for x in self.guilds if x.id == self.dev_server), None)
                if server:
                    logger.debug(f"Dev server: {server.name}")
                    # TODO: Resolve and print self.dev_user; this probably
                    # requires "list members" intent/permission.
        else:
            self.readied = True

    async def on_message(self, msg: discord.Message):
        if msg.author.bot:
            # Ignore our own messages
            return
        if self.user.mentioned_in(msg) and msg.mention_everyone is False:
            # Conditionally respond if dev mode is enabled.
            if not await self._dev_response(msg):
                return

            # Don't respond if this is a reply to a message written by us, i.e.
            # if someone replied to one of our messages.
            if isinstance(msg.reference, discord.MessageReference) and msg.reference.resolved.author.bot:
                return

            is_empty_message = mre.sub('', msg.content).strip() == ''

            if msg.author.guild_permissions.administrator:
                # Admin/mod stuff
                if await self._mod_commands(msg):
                    return

            if self.silence:
                logger.debug('Ignoring message due to silence')
                return

            if msg.content.endswith('help'):
                await msg.channel.send("Look here's the deal, just gimme a YouTube URL by @mentioning me, and I'll "
                                       "judge the song for you. You can also reply to a message with a YouTube link in "
                                       "it and mention me in the reply.", reference=msg, mention_author=False)
                return

            # Follow msg.referenced.resolved to get the message being replied to
            if isinstance(msg.reference, discord.MessageReference):
                msg = msg.reference.resolved

            elif is_empty_message or ure.search(msg.content) is None:
                # Send the "empty message" response if the message doesn't have a URL.
                if self.empty_response is not None:
                    await msg.channel.send(self.empty_response)
                return

            # Make sure the URL looks at least youtube-ish.
            # TODO: Maybe drop this part and let youtube-dl decide how to handle it.
            # This will allow non-YouTube sites to be used as well, e.g. Vimeo.
            match = yts.search(msg.content)
            if match is None:
                logger.debug("didn't match URL")
                await msg.channel.send("This doesn't look like a YouTube URL...", reference=msg, mention_author=False)
                return

            if self.viewed_emote is not None:
                # Add the "viewed" reaction to this message.
                await msg.add_reaction(self.viewed_emote)
            url: str = match.group(0)
            logger.debug(f"Got URL: {url}")
            # TODO: Handle the case where the video is country/region blocked.
            # Download the video title and format it.
            async with msg.channel.typing():
                try:
                    info = ydl.extract_info(match.group(0), download=False)
                except youtube_dl.utils.DownloadError as e:
                    emsg: str = re.search('ERROR: ([^\\n]+)', e.args[0]).group(1)
                    logger.warning("Got error: {0}".format(emsg))
                    if re.search("Incomplete YouTube ID", e.args[0]) is not None:
                        await msg.channel.send("I can't see this video...did you copy the whole URL?", reference=msg, mention_author=False)
                    else:
                        await msg.channel.send(f"I can't see this video...it says \"{emsg}\"", reference=msg, mention_author=False)
                    return

                # Strip out anything in brackets, then strip all non-alphanumeric and lowercase it
                title: str = fre.sub('', tre.sub('', info['title'].lower()))
                logger.debug(f"generating response for: {title}")
                # Seed the RNG and start generating the response
                seed(title)
                # Generate two random charts
                chart_prefix = choice(['S', 'D'])
                charts = [f"{chart_prefix}{randint(12, 28)}" for x in range(2)]
                # Add the song and chart descriptors.
                response: str = choice(responses.descriptors) + " " + \
                                choice(responses.charts).format(charts[0], charts[1])
                if randrange(self.bonus_chance_factor - 1) == 0:
                    # Add the bonus sentence.
                    logger.debug("adding bonus response")
                    response += " " + choice(responses.extra).format(charts[0])
                logger.debug(f"sending: \"{response}\"")
                await msg.channel.send(response, reference=msg, mention_author=False)

    async def _dev_response(self, msg: discord.Message) -> bool:
        """
        Determines whether the message should be responded to based on the dev
        mode configuration.
        :param msg: The message being processed
        :return: False if the message should not be processed; True otherwise.
        """
        if self.dev_mode is not None:
            if self.dev_mode == 'SERVER' and self.dev_server and msg.guild.id == self.dev_server:
                # Server ID must be filled in and matched.
                return True
            if self.dev_mode == 'USER' and self.dev_user and msg.author.id == self.dev_user:
                # User ID must be filled in and matched.
                return True
            if self.dev_mode == 'FULL' and self.dev_server and msg.guild.id == self.dev_server and self.dev_user and msg.author.id == self.dev_user:
                # Both IDs must be filled in and matched.
                return True
            # Don't respond in all other cases.
            return False
        # Respond if not in dev mode.
        return True

    async def _mod_commands(self, msg: discord.Message) -> bool:
        """
        Internal function for handling server mod/admin commands
        :param msg: The message we are operating on
        :return: True if the command was handled, otherwise False.
        """
        if 'help' in msg.content:
            help_text: str = """
            I can't help you! But what I _can_ do is respond to...
            **status** lets you know if I've been told to be quiet.
            **silence** tells me to shut up, or to speak up if I'm silenced.
            Otherwise just gimme a YouTube URL.
            """
            await msg.channel.send(help_text, reference=msg)
            return True

        if 'status' in msg.content:
            # Return the status of the bot
            logger.debug(f"Status - Silenced:{self.silence}")
            silenced: str = "not silenced."
            if self.silence:
                silenced = "silenced. (Except for right now)"
            await msg.channel.send(f"I am version {self.version}\n" +
                                   f"I am currently {silenced}")
            return True

        if 'silence' in msg.content:
            # Silence/unsilence the bot
            self.silence = not self.silence
            really_silence = ''
            if msg.content.endswith('!'):
                really_silence = ' No need to yell!'
            if self.silence:
                logger.debug('Silenced')
                await msg.channel.send("_Fine_, I'll be quiet." + really_silence)
            else:
                logger.debug('Unsilenced')
                await msg.channel.send("Alright I'll speak again." + really_silence)
            return True
        return False


bot = Benjabot()

if not os.getenv('TOKEN') or os.getenv('TOKEN') == '':
    print('$TOKEN not found; did you add the TOKEN env var?', file=sys.stderr)
    exit(1)
bot.run(os.getenv('TOKEN'))
