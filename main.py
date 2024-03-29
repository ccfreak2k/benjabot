import configparser
import logging
import os
from random import seed, choice, randint, randrange
import re
import subprocess
import sys

import discord
import yt_dlp.utils
from yt_dlp import YoutubeDL

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
ydl_opts = {"logger": Logger(), "ignoreerrors": False, "noplaylist": True}
ydl = YoutubeDL(ydl_opts)

# Regex for finding any URL
ure = re.compile(r'http[s]?://\S+')
# Regex for finding @mentions in message content
mre = re.compile(r'<@[!&]\d+>')
# Regex to remove [this] or (this) or {this} from titles.
tre = re.compile(r'\[[^]]*]|\([^)]*\)|{[^}]*}')
# Regex to strip non-alphanumeric characters from titles.
fre = re.compile(r'[\W_]+')
# Regex to remove difficulty from titles (e.g. S8, D23).
dre = re.compile(r'[sd]\d{1,2}')


class Benjabot(discord.Client):
    # Whether the bot has had on_ready() called at least once.
    readied: bool = False
    # The version of the bot.
    version: str = "1.1.0"
    cfg = configparser.ConfigParser()
    # The path to the config file.
    cfg_path = 'config.ini'
    # Default fallbacks for config values.
    defaults = {
        'silence': False,
        'bonus_chance_factor': 3,
        'viewed_emote':  '👁️',
        'empty_response': '👀'
    }

    def __init__(self, **options):
        logging.debug('Benjabot initing...')
        # Set up the defaults
        super().__init__(intents=discord.Intents.default(), **options)
        self.cfg.read(self.cfg_path)
        # TODO: Handle missing config file case.
        self.dev_server = self.cfg.getint('Dev', 'dev_server', fallback=None)
        # The actual dev mode is retrieved from the env var.
        self.dev_mode = os.getenv('DEVMODE')
        if not self.dev_server and self.dev_mode:
            logger.warning('No dev server specified')
        self.dev_user = self.cfg.getint('Dev', 'dev_user', fallback=None)
        if not self.dev_user and self.dev_mode:
            logger.warning('No dev user specified')
        # Append the git hash to the version string
        try:
            self.version += f"+{subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('utf-8').strip()}"
        except FileNotFoundError:
            logger.debug('No git found')
        logging.debug('done initing')

    async def on_ready(self):
        logging.debug('on_ready()')
        if not self.readied:
            print(f"Logged in as {bot.user} (ID: {bot.user.id})")
            if self.dev_mode:
                logger.debug(f"Dev mode enabled: {self.dev_mode}")
                # Resolve the dev server and user IDs for printing to the log.
                dev_server = self.get_guild(self.dev_server)
                if dev_server:
                    logger.debug(f"Dev server: {dev_server.name}")
                dev_user = self.get_user(self.dev_user)
                if dev_user:
                    logger.debug(f"Dev user: {dev_user.name}")
            self.readied = True

    async def on_message(self, msg: discord.Message):
        # Ignore our own messages
        if msg.author.bot:
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

            if self._read_setting(msg.guild.id, 'silence'):
                logger.debug('Ignoring message due to silence')
                return

            if msg.content.endswith('help'):
                await msg.channel.send("Look here's the deal, just gimme a video site URL by @mentioning me, and I'll "
                                       "judge the song for you. You can also reply to a message with a video site link "
                                       "in it and mention me in the reply.", reference=msg, mention_author=False)
                return

            # Attempt to find a URL in the message.
            match = ure.search(msg.content)

            # Follow msg.referenced.resolved to get the message being replied to
            if isinstance(msg.reference, discord.MessageReference):
                msg = msg.reference.resolved

            empty_response = self._read_setting(msg.guild.id, 'empty_response')
            if match is None:
                # Look for any matching autoresponses to send
                if not is_empty_message:
                    for regex, response in responses.autoresponses.items():
                        if re.search(regex, msg.content):
                            logger.debug(f'Matched: ( {regex} ); sending {response}')
                            await msg.channel.send(response, reference=msg)
                            return
                # Send the "empty message" response if the message doesn't have a URL.
                if empty_response is not None and empty_response != '':
                    await msg.channel.send(empty_response)
                return

            viewed_emote = self._read_setting(msg.guild.id, 'viewed_emote')
            if viewed_emote is not None and viewed_emote != '':
                # Add the "viewed" reaction to this message.
                await msg.add_reaction(viewed_emote)
            url: str = match.group(0)
            logger.debug(f"Got URL: {url}")
            # TODO: Handle the case where the video is country/region blocked.
            # Download the video title and format it.
            async with msg.channel.typing():
                try:
                    info = ydl.extract_info(match.group(0), download=False)
                except yt_dlp.utils.DownloadError as e:
                    emsg: str = re.search('ERROR: ([^\\n]+)', e.args[0]).group(1)
                    logger.warning(f"Got error: {emsg}")
                    if re.search("Unsupported URL", e.args[0], re.IGNORECASE):
                        await msg.channel.send("Sorry man, either this isn't a video or I don't recognize this site.", reference=msg, mention_author=False)
                    elif re.search("Incomplete YouTube ID", e.args[0], re.IGNORECASE) is not None:
                        await msg.channel.send("I can't see this video...did you copy the whole URL?", reference=msg, mention_author=False)
                    else:
                        await msg.channel.send(f"I can't see this video...it says \"{emsg}\"", reference=msg, mention_author=False, suppress_embeds=True)
                    return

                if info is None:
                    await msg.channel.send("This doesn't look like a video...", reference=msg, mention_author=False)
                    return
                # Strip out anything in brackets, then strip all non-alphanumeric and lowercase it
                title: str = fre.sub('', dre.sub('', tre.sub('', info['title'].lower())))
                logger.debug(f"generating response for: {title}")
                # Seed the RNG and start generating the response
                seed(title)
                # Generate two random charts
                chart_prefix = choice(['S', 'D'])
                charts = [f"{chart_prefix}{randint(12, 28)}" for x in range(2)]
                # Add the song and chart descriptors.
                response: str = choice(responses.descriptors) + " " + \
                                choice(responses.charts).format(charts[0], charts[1])
                if randrange(self._read_setting(msg.guild.id, 'bonus_chance_factor') - 1) == 0:
                    # Add the bonus sentence.
                    logger.debug("adding bonus response")
                    # Generate an extra chart
                    extra_chart = f"{choice(['S', 'D'])}{randint(12, 28)}"
                    response += " " + choice(responses.extra).format(extra_chart)
                logger.debug(f"sending: \"{response}\"")
                await msg.channel.send(response, reference=msg, mention_author=False)

    def _read_setting(self, server_id: int, key: str):
        """
        Reads a per-server setting from the config file. If the setting does not
        exist for the server, the default is returned.

        :param server_id: The server ID for the setting
        :param key: The name of the setting
        :return: The current setting
        :raises: KeyError if the setting does not exist
        """
        if key not in self.defaults.keys():
            raise KeyError(f"{key} is not a valid setting.")
        if isinstance(self.defaults[key], bool):
            value = self.cfg.getboolean(f"server:{server_id}", key, fallback=self.defaults[key])
        else:
            value = self.cfg.get(f"server:{server_id}", key, fallback=self.defaults[key])
        logger.debug(f"Read setting {key}={value} for server {server_id}")
        return value

    def _write_setting(self, server_id: int, key: str, value) -> None:
        """
        Writes a per-server setting to the config file. The server section and
        setting key will be created as needed.

        :param server_id: The server ID for the setting
        :param key: The name of the setting
        :param value: The new value to write
        :return: None
        :raises: KeyError if the setting does not exist
        """
        if key not in self.defaults.keys():
            raise KeyError(f"{key} is not a valid setting.")
        try:
            self.cfg.set(f"server:{server_id}", key, str(value))
        except configparser.NoSectionError:
            self.cfg.add_section(f"server:{server_id}")
            self.cfg.set(f"server:{server_id}", key, str(value))
        logger.debug(f"Write setting {key}={value} for server {server_id}")
        with open(self.cfg_path, 'w') as f:
            self.cfg.write(f)

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
            Otherwise just gimme a video site URL.
            """
            await msg.channel.send(help_text, reference=msg)
            return True

        if 'status' in msg.content:
            # Return the status of the bot
            silenced: str = "not silenced."
            if self._read_setting(msg.guild.id, 'silence'):
                silenced = "silenced. (Except for right now)"
            await msg.channel.send(f"I am version {self.version}\n" +
                                   f"I am currently {silenced}")
            return True

        if 'silence' in msg.content:
            # Silence/unsilence the bot
            self._write_setting(msg.guild.id, 'silence', not bool(self._read_setting(msg.guild.id, 'silence')))
            logger.debug(f"Silenced: {msg.guild.id} -> {self._read_setting(msg.guild.id, 'silence')}")
            really_silence = ''
            if msg.content.endswith('!'):
                really_silence = ' No need to yell!'
            if self._read_setting(msg.guild.id, 'silence'):
                await msg.channel.send("_Fine_, I'll be quiet." + really_silence)
            else:
                await msg.channel.send("Alright I'll speak again." + really_silence)
            return True

        return False


bot = Benjabot()

# Make sure the TOKEN environment variable is set.
if not os.environ.get('TOKEN') or os.environ.get('TOKEN') == '':
    raise RuntimeError("TOKEN environment variable not set")
    exit(1)
bot.run(os.getenv('TOKEN'))
