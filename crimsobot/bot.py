import asyncio
import logging
import random

import discord
from discord.ext import commands

import crimsobot.utils.markov as m
import crimsobot.utils.tools as c
from config import ADMIN_USER_IDS, BANNED_GUILD_IDS, DM_LOG_CHANNEL_ID, LEARNER_CHANNEL_IDS, LEARNER_USER_IDS
from crimsobot.utils import checks


class CrimsoBOT(commands.Bot):
    def __init__(self, **kwargs):
        command_prefix = '>'

        super().__init__(command_prefix, **kwargs)

        self.log = logging.getLogger(__name__)
        self._extensions_to_load = [
            'crimsobot.extensions.presence',  # 'crimsobot.extensions.reminder',
            'crimsobot.cogs.admin', 'crimsobot.cogs.chat', 'crimsobot.cogs.games', 'crimsobot.cogs.image',
            'crimsobot.cogs.mystery', 'crimsobot.cogs.text', 'crimsobot.cogs.utilities'
        ]

    def load_extensions(self):
        for name in self._extensions_to_load:
            try:
                self.load_extension(name)
            except Exception as error:
                self.log.error('%s cannot be loaded: %s', name, error)

    async def on_ready(self):
        self.log.info('crimsoBOT is online')

    async def on_resumed(self):
        self.log.warning('crimsoBOT RECONNECT')

    async def on_command_error(self, ctx: commands.Context, error):
        """
        Displays error messages to user for cooldown and CommandNotFound,
        and suppresses verbose error text for both in the console.
        """

        if isinstance(error, commands.CommandOnCooldown):
            self.log.error('Cooldown: %s // %s: %s', ctx.author, ctx.message.content, error)

            msg = await ctx.send('**eat glass.** %.0fs cooldown.' % error.retry_after)
            await asyncio.sleep(7)
            await msg.delete()
        elif isinstance(error, commands.CommandInvokeError):
            try:
                self.log.exception('Invoke: %s // %s: %s', ctx.author, ctx.message.content, error)

                msg = await ctx.send(':poop: `E R R O R` :poop:')
                await asyncio.sleep(7)
                await msg.delete()
            except discord.errors.Forbidden:
                self.log.error('Forbidden: %s // %s: %s', ctx.guild, ctx.channel.id, error)
        elif isinstance(error, commands.MissingRequiredArgument):
            self.log.error('Argument: %s // %s: %s', ctx.author, ctx.message.content, error)

            msg = await ctx.send('*this command requires more arguments. try `>help [cmd]`*')
            await asyncio.sleep(7)
            await msg.delete()
        elif isinstance(error, checks.NotAdmin):
            self.log.error('NotAdmin: %s // %s: %s', ctx.author, ctx.message.content, error)

            msg = await ctx.send(':rotating_light: not crimso! :rotating_light:')
            await asyncio.sleep(7)
            await msg.delete()
        elif isinstance(error, commands.CommandNotFound):
            self.log.error(
                'NotFound/Forbidden: %s/%s // %s: %s',
                ctx.message.guild.id, ctx.message.channel, ctx.message.content, error
            )
        else:
            raise error

    async def on_message(self, message):
        if c.is_banned(message.author.id):
            return

        # DM self.logger
        is_dm = isinstance(message.channel, discord.DMChannel)
        if is_dm and message.author.id != self.user.id and not message.content.startswith('>'):  # crimsoBOT
            try:
                link = message.attachments[0].url
            except Exception:
                link = ''

            dms_channel = self.get_channel(DM_LOG_CHANNEL_ID)
            await dms_channel.send(
                '`{} ({}):`\n{} {}'.format(message.channel, message.channel.id, message.content, link)
            )

        # process commands
        await self.process_commands(message)

        # learn from crimso
        if message.author.id in LEARNER_USER_IDS and message.channel.id in LEARNER_CHANNEL_IDS:
            m.learner(message.content)

        # respond to ping
        if self.user in message.mentions:
            await message.channel.send(m.crimso())

        # random chat
        if random.random() < 0.001 and not is_dm:
            await message.channel.send(m.crimso())

    async def on_guild_join(self, guild):
        """Notify me when added to guild"""

        if guild.id in BANNED_GUILD_IDS:
            await guild.leave()
            self.log.warning('Banned guild %s attempted to add crimsoBOT.', guild.id)
            return

        self.log.info("Joined %s's %s [%s]", guild.owner, guild, guild.id)

        embed = c.get_guild_info_embed(guild)

        # ...and send
        for user_id in ADMIN_USER_IDS:
            user = await self.get_user(user_id)
            try:
                await user.send('Added to {guild}'.format(guild=guild), embed=embed)
            except Exception:
                await user.send('Added to {guild}'.format(guild=guild))