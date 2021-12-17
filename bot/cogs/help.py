import asyncio
import datetime as dt
import time

import discord
from discord.ext.commands import Cog
from discord.ext.commands import command

OPTIONS = {"❌": 0}


class Help(Cog):

    def __init__(self, bot):
        self.bot = bot

    @command(name="help")
    async def show_help(self, ctx):
        await ctx.message.delete()

        def _check(r, u):
            return (
                    r.emoji in OPTIONS.keys()
                    and u == ctx.author
                    and r.message.id == msg.id
            )

        embed = discord.Embed(title="justRunnz Help",
                              description=f"Shows all commands bot",
                              color=ctx.author.colour,
                              timestamp=dt.datetime.utcnow()
                              )
        embed.add_field(name=f"`.join`", value="Connect the bot to the current channel.", inline=False)
        embed.add_field(name=f".`leave` | `.lv`", value="Disconnect the bot from the channel.", inline=False)
        embed.add_field(name=f"`.play <url> | <track name>`", value="Play the track that you choose", inline=False)
        embed.add_field(name=f"`.resume` | `.rs`", value="Resumes the track if is in pause", inline=False)
        embed.add_field(name=f"`.pause` | `.p`", value="Pauses the track if is playing", inline=False)
        embed.add_field(name=f"`.next` | `.skip`", value="Skip to the next track", inline=False)
        embed.add_field(name=f"`.previous`", value="Play the previous track", inline=False)
        embed.add_field(name=f"`.repeat` | `.rpt` | `.rp`", value="Repeat the track", inline=False)
        embed.add_field(name=f"`.queue` | `.q `", value="Shows tracks in queue", inline=False)
        embed.add_field(name=f"`.clearqueue` | `.clearq`", value="Clears the queue", inline=False)
        embed.add_field(name=f"`.playing` | .np`", value="Shows the playing track", inline=False)
        embed.add_field(name=f"`.skipto <track>`", value="Skip to the track that you choose", inline=False)
        embed.add_field(name=f"`.volume < up or + > | < down or - > | < value >`", value="Regulates the volume",
                        inline=False)

        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar_url)

        msg = await ctx.send(embed=embed)

        await msg.add_reaction("❌")

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", check=_check)
        except asyncio.TimeoutError:
            await msg.delete()
        else:
            time.sleep(0.25)
            await msg.delete()


def setup(bot):
    bot.add_cog(Help(bot))
