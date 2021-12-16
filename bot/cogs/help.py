from typing import Optional

import discord
from discord import Embed
from discord.utils import get
from discord.ext.menus import MenuPages, ListPageSource
from discord.ext.commands import Cog
from discord.ext.commands import command
import datetime as dt


def syntax(command):
    cmd_and_aliases = "|".join([str(command), *command.aliases])
    params = []

    for key, value in command.params.items():
        if key not in ("self", "ctx"):
            params.append(f"[{key}]" if "NoneType" in str(value) else f"<{key}>")

    params = " ".join(params)

    return f"`{cmd_and_aliases} {params}`"


class HelpMenu(ListPageSource):
    def __init__(self, ctx, data):
        self.ctx = ctx

        super().__init__(data, per_page=10)

    async def write_page(self, menu, fields=[]):
        offset = (menu.current_page * self.per_page) + 1
        len_data = len(self.entries)

        embed = Embed(title="Help",
                      description="Welcome to the justRunnz help!",
                      colour=self.ctx.author.colour)
        # embed.set_footer(text=f"Invoked by {self.ctx.author.display_name} "
        #                       f" {offset:,} - {min(len_data, offset + self.per_page - 1):,} of {len_data:,} commands",
        #                       icon_url=self.ctx.author.avatar_url)

        embed.set_footer(text=f"Invoked by {self.ctx.author.display_name}   {offset:,} - {min(len_data, offset + self.per_page - 1):,} of {len_data:,} commands.")

        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)

        return embed

    async def format_page(self, menu, entries):
        fields = []

        for entry in entries:
            fields.append((entry.brief or "No description", syntax(entry)))

        return await self.write_page(menu, fields)


class Help(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.remove_command("help")

    async def cmd_help(self, ctx, command):
        embed = Embed(title=f"Help with `{command}`",
                      description=syntax(command),
                      colour=ctx.author.colour)
        embed.add_field(name="Command description", value=command.help)
        await ctx.send(embed=embed)

    @command(name="help")
    async def show_help(self, ctx, cmd: Optional[str]):
        """Shows this message."""
        # if cmd is None:
        #     menu = MenuPages(source=HelpMenu(ctx, list(self.bot.commands)),
        #                      delete_message_after=True,
        #                      timeout=60.0)
        #     await menu.start(ctx)
        #
        # else:
        #     if (command := get(self.bot.commands, name=cmd)):
        #         await self.cmd_help(ctx, command)
        #
        #     else:
        #         await ctx.send("That command does not exist.")
        #
        # #### Create the initial embed object ####
        embed = discord.Embed(title="justRunnz Help",
                              description=f"Shows all commands bot",
                              color=ctx.author.colour,
                              timestamp=dt.datetime.utcnow()
                              )
        embed.set_author(name="Help Requested")

        embed.add_field(name=".join", value="Connect the bot to the current channel.",inline=False)
        embed.add_field(name=".leave | .lv", value="Disconnect the bot from the channel.", inline=False)
        embed.add_field(name=".play <url> | <track name>", value="Play the track that you choose", inline=False)
        embed.add_field(name=".resume | .rs", value="Resumes the track if is in pause", inline=False)
        embed.add_field(name=".pause | .p", value="Pauses the track if is playing", inline=False)
        embed.add_field(name=".next | .skip", value="Skip to the next track", inline=False)
        embed.add_field(name=".previous", value="Play the previous track", inline=False)
        embed.add_field(name=".repeat | .rpt | .rp", value="Repeat the track", inline=False)
        embed.add_field(name=".queue | .q ", value="Shows tracks in queue", inline=False)
        embed.add_field(name=".clearqueue | .clearq", value="Clears the queue", inline=False)
        embed.add_field(name=".playing | .np", value="Shows the playing track", inline=False)
        embed.add_field(name=".skipto <track>", value="Skip to the track that you choose", inline=False)
        embed.add_field(name=".volume < up or + > < down or - > < value >", value="Regulates the volume", inline=False)

        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar_url)

        msg = await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Help(bot))
