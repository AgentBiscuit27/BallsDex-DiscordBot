from __future__ import annotations

import asyncio
import logging
import math
from typing import cast

import aiohttp
import discord
import discord.gateway
from discord import app_commands
from discord.ext import commands
from rich import print

from ballsdex.core.dev import Dev
from ballsdex.core.metrics import PrometheusServer
from ballsdex.core.models import BlacklistedGuild, BlacklistedID, Special, Ball, balls, specials
from ballsdex.core.commands import Core
from ballsdex.settings import settings

import sqlite3
from colorama import Fore, Style
import time, datetime

bot = commands.Bot(command_prefix=".", intents=discord.Intents.all())

log = logging.getLogger("ballsdex.core.bot")

PACKAGES = ["config", "players", "countryballs", "info", "admin", "trade"]


def owner_check(ctx: commands.Context[BallsDexBot]):
    return ctx.bot.is_owner(ctx.author)

connection = sqlite3.connect('vouches.db')
cursor = connection.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS vouches (
        user_id INTEGER PRIMARY KEY,
        vouch_count INTEGER DEFAULT 0
    )
''')
connection.commit()

@bot.event
async def on_ready():
    print(Fore.RED + f"{bot.user}" + Fore.BLUE + " is here to the rescue!")
    print(Style.RESET_ALL)
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="The Spooderman Movie Trailer"))

start_time = time.time()

@bot.command()
async def help(ctx, embed_choice):
    embed = discord.Embed(title = "Help", description = "This is the first page of commands that the Spooder Bot offers", color = discord.Color.red())
    embed.add_field(name = "Help command - \'help\'", value = "This command will list the commands of this bot. The prefix is \'`.`\'.")
    embed.add_field(name = "Bot Info command - \'botinfo\'", value = "This command tells you lots of information about this bot, including the prefix.", inline = False)
    embed.add_field(name = "AFK command - \'afk\'", value = "This command lets you go AFK, and when someone pings you, they will be told you're AFK.", inline = False)
    embed.add_field(name = "Vouch command - \'vouch\'", value = "This command lets you add a vouch to any user (except yourself).")
    embed.add_field(name = "Vouches command - \'vouches\'", value = "This command shows you how many vouches a user has.", inline = False)
    embed.set_author(name = "Spooder Bot#6273", icon_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSQVfeZlEOZKeGRgafZ3u5HA-movjZayxoPCw&usqp=CAU")
    embed.set_footer(text = "Spooder Bot help | Spooder Bot#6273", icon_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSQVfeZlEOZKeGRgafZ3u5HA-movjZayxoPCw&usqp=CAU")

    embed2 = discord.Embed(title = "Help", description = "This is the second page of commands that the Spooder Bot offers", color = discord.Color.red())
    embed2.add_field(name = "Add vouches command - \'addvouches\'", value = "This command lets you add vouches to a user.", inline = False)
    embed2.add_field(name = "Delete vouches command - \'delvouches\'", value = "This command will let you remove vouches from a user.", inline = False)
    embed2.add_field(name = "Countryvia command - \'countryvia\'", value = "This command will start a round of countryvia, where you have to guess the country based on the flag.", inline = False)
    embed2.set_author(name = "Spooder Bot#6273", icon_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSQVfeZlEOZKeGRgafZ3u5HA-movjZayxoPCw&usqp=CAU")
    embed2.set_footer(text = "Spooder Bot help | Spooder Bot#6273", icon_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSQVfeZlEOZKeGRgafZ3u5HA-movjZayxoPCw&usqp=CAU")

    if embed_choice == "1":
        await ctx.send(embed = embed)
    elif embed_choice == "2":
        await ctx.send(embed = embed2)
    else:
        await ctx.send("The page you have chosen doesn't exist. Please choose a different page.")

@bot.command()
async def botinfo(ctx):
    current_time = time.time()
    difference = int(round(current_time - on_ready()))
    embed = discord.Embed(title = "Spooder Bot information", description = "This is all the information about the Spooder Bot", color = discord.Color.red())
    embed.add_field(name = "Developers", value = "goofy ahh spiderman#0001 and Darghano#3333", inline = False)
    embed.add_field(name = "Language", value = "Python", inline = False)
    embed.add_field(name = "Prefix", value = ".", inline = False)
    embed.add_field(name = "Guilds", value = len(bot.guilds), inline = False)
    embed.add_field(name = "Members", value = ctx.guild.member_count, inline = False)
    embed.add_field(name = "Ping", value = f"{bot.latency}ms", inline = False)
    embed.add_field(name = "Uptime", value = str(datetime.timedelta(seconds = difference)), inline = False)
    embed.set_author(name = "Spooder Bot#6273", icon_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSQVfeZlEOZKeGRgafZ3u5HA-movjZayxoPCw&usqp=CAU")
    embed.set_footer(text = "Spooder Bot info | Spooder Bot#6273", icon_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSQVfeZlEOZKeGRgafZ3u5HA-movjZayxoPCw&usqp=CAU")
    await ctx.send(embed = embed)

@bot.listen()
async def on_message(message):
    if message.author == bot.user:
        return
    for user in message.mentions:
        if user.id in afkDict:
            await message.channel.send(f"**{str(user)}** is currently AFK: {afkDict[message.author.id].get('reason')}")

afkDict = {}

@bot.command()
async def afk(ctx, *, reason):
    afkDict[ctx.author.id] = {"reason": reason, "start_time": datetime.datetime.now()}
    await ctx.send("You are now AFK: " + reason)
    start_time = datetime.datetime.now()
    await bot.wait_for("message")
    await ctx.send(f"Welcome back {ctx.author.mention}, you've been away since {discord.utils.format_dt(start_time, style = 'R')}.")

@bot.command()
async def vouch(ctx, member: discord.Member):
    cursor.execute('SELECT vouch_count FROM vouches WHERE user_id = ?', (member.id,))
    result = cursor.fetchone()
    
    if result:
        vouch_count = result[0]
    else:
        cursor.execute('INSERT INTO vouches (user_id) VALUES (?)', (member.id,))
        vouch_count = 0
    
    vouch_count += 1
    cursor.execute('UPDATE vouches SET vouch_count = ? WHERE user_id = ?', (vouch_count, member.id))
    connection.commit()
    embed = discord.Embed(description = f"{member.mention}, you have just been vouched by {ctx.author.mention}!", color = discord.Color.green())
    await ctx.send(member.mention, embed = embed)

@bot.command()
async def vouches(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    
    if member == ctx.author:
        await ctx.send("You cant vouch yourself bozo ☠️")
        return

    cursor.execute('SELECT vouch_count FROM vouches WHERE user_id = ?', (member.id,))
    result = cursor.fetchone()

    if result:
        vouch_count = result[0]
        if vouch_count == 1:
            await ctx.send(f"{member.mention} has {vouch_count} vouch.")
        await ctx.send(f'{member.mention} has {vouch_count} vouches.')
    else:
        await ctx.send(f'{member.mention} has no vouches.')

# make so that only mods or smth can use
@bot.command()
async def addvouches(ctx, member: discord.Member, amount: int):
    cursor.execute('SELECT vouch_count FROM vouches WHERE user_id = ?', (member.id,))
    result = cursor.fetchone()

    if result:
        current_count = result[0]
        new_count = current_count + amount
        cursor.execute('UPDATE vouches SET vouch_count = ? WHERE user_id = ?', (new_count, member.id))
        connection.commit()
        await ctx.send(f'Added {amount} vouches to {member.mention}. New vouch count: {new_count}.')
    else:
        cursor.execute('INSERT INTO vouches (user_id, vouch_count) VALUES (?, ?)', (member.id, amount))
        connection.commit()
        await ctx.send(f'Added {amount} vouches to {member.mention}. New vouch count: {new_count}.')

# make so that only mods or smth can use
@bot.command()
async def delvouches(ctx, member: discord.Member, amount: int):
    cursor.execute('SELECT vouch_count FROM vouches WHERE user_id = ?', (member.id,))
    result = cursor.fetchone()

    if result:
        current_count = result[0]
        new_count = current_count - amount
        if new_count < 0:
            new_count = 0
        cursor.execute('UPDATE vouches SET vouch_count = ? WHERE user_id = ?', (new_count, member.id))
        connection.commit()
        await ctx.send(f'Deleted {amount} vouches from {member.mention}. New vouch count: {new_count}.')
    else:
        await ctx.send(f'{member.mention} does not have any vouches.')

@bot.command()
async def clear(ctx, amount: int):
    """Clears a specified number of messages in a channel."""
    # Check if the user has the required permissions
    if not ctx.message.author.guild_permissions.manage_messages:
        await ctx.send("You don't have the required permissions to manage messages.")
        return

    # Delete the specified number of messages
    await ctx.message.delete()
    deleted = await ctx.channel.purge(limit=amount)

    # Send a response with the number of messages cleared
    response = f"Cleared {len(deleted)} messages."
    await ctx.send(response)

@bot.command()
async def vouchleaderboard(ctx):
    # Fetch the top 10 vouches from the database
    cursor.execute("SELECT user_id, vouch_count FROM vouches ORDER BY vouch_count DESC LIMIT 10")
    results = cursor.fetchall()

    # Create an embed to display the leaderboard
    embed = discord.Embed(title="Vouch Leaderboard", color=discord.Color.red())

    # Populate the embed with leaderboard data
    for i, (user_id, vouches) in enumerate(results, start=1):
        user = ctx.guild.get_member(user_id)
        username = user.name if user else f"Unknown User ({user_id})"
        embed.add_field(name=f"`#{i}` - {username}", value=f"Vouches: {vouches}", inline=False)

    await ctx.send(embed=embed)

class CommandTree(app_commands.CommandTree):
    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        bot = cast(BallsDexBot, interaction.client)
        if not bot.is_ready():
            if interaction.type != discord.InteractionType.autocomplete:
                await interaction.response.send_message(
                    "The bot is currently starting, please wait for a few minutes... "
                    f"({round((len(bot.shards)/bot.shard_count)*100)}%)",
                    ephemeral=True,
                )
            return False  # wait for all shards to be connected
        return await bot.blacklist_check(interaction)


class BallsDexBot(commands.AutoShardedBot):
    """
    BallsDex Discord bot
    """

    def __init__(self, command_prefix: str, dev: bool = False, **options):
        # An explaination for the used intents
        # guilds: needed for basically anything, the bot needs to know what guilds it has
        # and accordingly enable automatic spawning in the enabled ones
        # guild_messages: spawning is based on messages sent, content is not necessary
        # emojis_and_stickers: DB holds emoji IDs for the balls which are fetched from 3 servers
        intents = discord.Intents(
            guilds=True, guild_messages=True, emojis_and_stickers=True, message_content=True
        )

        super().__init__(command_prefix, intents=intents, tree_cls=CommandTree, **options)

        self.dev = dev
        self.prometheus_server: PrometheusServer | None = None

        self.tree.error(self.on_application_command_error)
        self.add_check(owner_check)  # Only owners are able to use text commands

        self._shutdown = 0
        self.blacklist: set[int] = set()
        self.blacklist_guild: set[int] = set()
        self.locked_balls: set[int] = set()

    async def start_prometheus_server(self):
        self.prometheus_server = PrometheusServer(
            self, settings.prometheus_host, settings.prometheus_port
        )
        await self.prometheus_server.run()

    def assign_ids_to_app_groups(
        self, group: app_commands.Group, synced_commands: list[app_commands.AppCommandGroup]
    ):
        for synced_command in synced_commands:
            bot_command = group.get_command(synced_command.name)
            if not bot_command:
                continue
            bot_command.extras["mention"] = synced_command.mention
            if isinstance(bot_command, app_commands.Group) and bot_command.commands:
                self.assign_ids_to_app_groups(
                    bot_command, cast(list[app_commands.AppCommandGroup], synced_command.options)
                )

    def assign_ids_to_app_commands(self, synced_commands: list[app_commands.AppCommand]):
        for synced_command in synced_commands:
            bot_command = self.tree.get_command(synced_command.name, type=synced_command.type)
            if not bot_command:
                continue
            bot_command.extras["mention"] = synced_command.mention
            if isinstance(bot_command, app_commands.Group) and bot_command.commands:
                self.assign_ids_to_app_groups(
                    bot_command, cast(list[app_commands.AppCommandGroup], synced_command.options)
                )

    async def load_cache(self):
        balls.clear()
        for ball in await Ball.all():
            balls.append(ball)
        log.info(f"Loaded {len(balls)} balls")

        specials.clear()
        for special in await Special.all():
            specials.append(special)
        log.info(f"Loaded {len(specials)} specials")

        self.blacklist = set()
        for blacklisted_id in await BlacklistedID.all().only("discord_id"):
            self.blacklist.add(blacklisted_id.discord_id)
        self.blacklist_guild = set()
        for blacklisted_id in await BlacklistedGuild.all().only("discord_id"):
            self.blacklist_guild.add(blacklisted_id.discord_id)

    async def gateway_healthy(self) -> bool:
        """Check whether or not the gateway proxy is ready and healthy."""
        if settings.gateway_url is None:
            raise RuntimeError("This is only available on the production bot instance.")

        try:
            base_url = str(discord.gateway.DiscordWebSocket.DEFAULT_GATEWAY).replace(
                "ws://", "http://"
            )
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{base_url}/health", timeout=10) as resp:
                    return resp.status == 200
        except (aiohttp.ClientConnectionError, asyncio.TimeoutError):
            return False

    async def setup_hook(self) -> None:
        log.info("Starting up with %s shards...", self.shard_count)
        if settings.gateway_url is None:
            return

        while True:
            response = await self.gateway_healthy()
            if response is True:
                log.info("Gateway proxy is ready!")
                break

            log.warning("Gateway proxy is not ready yet, waiting 30 more seconds...")
            await asyncio.sleep(30)

    async def on_ready(self):
        assert self.user
        log.info(f"Successfully logged in as {self.user} ({self.user.id})!")

        # set bot owners
        assert self.application
        if self.application.team:
            if settings.team_owners:
                self.owner_ids.update(m.id for m in self.application.team.members)
            else:
                self.owner_ids.add(self.application.team.owner_id)
        else:
            self.owner_ids.add(self.application.owner.id)
        if settings.co_owners:
            self.owner_ids.update(settings.co_owners)
        log.info(
            f"{self.owner_ids} {'are' if len(self.owner_ids) > 1 else 'is'} set as the bot owner."
        )

        await self.load_cache()
        if self.blacklist:
            log.info(f"{len(self.blacklist)} blacklisted users.")

        log.info("Loading packages...")
        await self.add_cog(Core(self))
        if self.dev:
            await self.add_cog(Dev())

        loaded_packages = []
        for package in PACKAGES:
            try:
                await self.load_extension("ballsdex.packages." + package)
            except Exception:
                log.error(f"Failed to load package {package}", exc_info=True)
            else:
                loaded_packages.append(package)
        if loaded_packages:
            log.info(f"Packages loaded: {', '.join(loaded_packages)}")
        else:
            log.info("No package loaded.")

        synced_commands = await self.tree.sync()
        if synced_commands:
            log.info(f"Synced {len(synced_commands)} commands.")
            try:
                self.assign_ids_to_app_commands(synced_commands)
            except Exception:
                log.error("Failed to assign IDs to app commands", exc_info=True)
        else:
            log.info("No command to sync.")

        if "admin" in PACKAGES:
            for guild_id in settings.admin_guild_ids:
                guild = self.get_guild(guild_id)
                if not guild:
                    continue
                synced_commands = await self.tree.sync(guild=guild)
                log.info(f"Synced {len(synced_commands)} admin commands for guild {guild.id}.")

        if settings.prometheus_enabled:
            try:
                await self.start_prometheus_server()
            except Exception:
                log.exception("Failed to start Prometheus server, stats will be unavailable.")

        print(
            f"\n    [bold][red]{settings.bot_name} bot[/red] [green]"
            "is now operational![/green][/bold]\n"
        )

    async def blacklist_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id in self.blacklist:
            await interaction.response.send_message(
                "You are blacklisted from the bot."
                "\nYou can appeal this blacklist in our support server: {}".format(
                    settings.discord_invite
                ),
                ephemeral=True,
            )
            return False
        if interaction.guild_id and interaction.guild_id in self.blacklist_guild:
            await interaction.response.send_message(
                "This server is blacklisted from the bot."
                "\nYou can appeal this blacklist in our support server: {}".format(
                    settings.discord_invite
                ),
                ephemeral=True,
            )
            return False
        return True

    async def on_command_error(
        self, context: commands.Context, exception: commands.errors.CommandError
    ):
        if isinstance(
            exception, (commands.CommandNotFound, commands.CheckFailure, commands.DisabledCommand)
        ):
            return

        assert context.command
        if isinstance(exception, (commands.ConversionError, commands.UserInputError)):
            # in case we need to know what happened
            log.debug("Silenced command exception", exc_info=exception)
            await context.send_help(context.command)
            return

        if isinstance(exception, commands.MissingRequiredAttachment):
            await context.send("An attachment is missing.")
            return

        if isinstance(exception, commands.CommandInvokeError):
            if isinstance(exception.original, discord.Forbidden):
                await context.send("The bot does not have the permission to do something.")
                # log to know where permissions are lacking
                log.warning(
                    f"Missing permissions for text command {context.command.name}",
                    exc_info=exception.original,
                )
                return

            log.error(f"Error in text command {context.command.name}", exc_info=exception.original)
            await context.send(
                "An error occured when running the command. Contact support if this persists."
            )
            return

        await context.send(
            "An error occured when running the command. Contact support if this persists."
        )
        log.error(f"Unknown error in text command {context.command.name}", exc_info=exception)

    async def on_application_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        async def send(content: str):
            if interaction.response.is_done():
                await interaction.followup.send(content, ephemeral=True)
            else:
                await interaction.response.send_message(content, ephemeral=True)

        if isinstance(error, app_commands.CheckFailure):
            if isinstance(error, app_commands.CommandOnCooldown):
                await send(
                    "This command is on cooldown. Please retry "
                    f"in {math.ceil(error.retry_after)} seconds."
                )
                return
            await send("You are not allowed to use that command.")
            return

        if isinstance(error, app_commands.CommandInvokeError):
            assert interaction.command

            if isinstance(error.original, discord.Forbidden):
                await send("The bot does not have the permission to do something.")
                # log to know where permissions are lacking
                log.warning(
                    f"Missing permissions for app command {interaction.command.name}",
                    exc_info=error.original,
                )
                return

            if isinstance(error.original, discord.InteractionResponded):
                # most likely an interaction received twice (happens sometimes),
                # or two instances are running on the same token.
                log.warning(
                    f"Tried invoking command {interaction.command.name}, but the "
                    "interaction was already responded to.",
                    exc_info=error.original,
                )
                # still including traceback because it may be a programming error

            log.error(
                f"Error in slash command {interaction.command.name}", exc_info=error.original
            )
            await send(
                "An error occured when running the command. Contact support if this persists."
            )
            return

        await send("An error occured when running the command. Contact support if this persists.")
        log.error("Unknown error in interaction", exc_info=error)

    async def on_error(self, event_method: str, /, *args, **kwargs):
        formatted_args = ", ".join(args)
        formatted_kwargs = " ".join(f"{x}={y}" for x, y in kwargs.items())
        log.error(
            f"Error in event {event_method}. Args: {formatted_args}. Kwargs: {formatted_kwargs}",
            exc_info=True,
        )
        self.tree.interaction_check
