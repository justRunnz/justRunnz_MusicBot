from datetime import datetime, timedelta
from typing import Optional

from discord import Member
from discord.ext import commands
from discord.ext.commands import Greedy
from discord.ext.commands import command, has_permissions, bot_has_permissions


class Mod(commands.Cog):
    @command(name="clear", aliases=["purge", "clr", "cl"])
    @bot_has_permissions(manage_messages=True)
    @has_permissions(manage_messages=True)
    async def clear_messages(self, ctx, targets: Greedy[Member], limit: Optional[int] = 1):
        def _check(message):
            return not len(targets) or message.author in targets

        if 0 < limit <= 100:
            with ctx.channel.typing():
                await ctx.message.delete()
                deleted = await ctx.channel.purge(limit=limit, after=datetime.utcnow() - timedelta(days=361),
                                                  check=_check)

                await ctx.send(f"Deleted {len(deleted):,} messages.", delete_after=5)

        else:
            await ctx.send("The limit provided is not within acceptable bounds.")


def setup(bot):
    bot.add_cog(Mod(bot))
