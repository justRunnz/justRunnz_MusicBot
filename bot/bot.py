from itertools import cycle
from pathlib import Path

import discord
from discord.ext import commands, tasks

class MusicBot(commands.Bot):

    def __init__(self):
        self._cogs = [p.stem for p in Path(".").glob("./bot/cogs/*.py")]
        self.status = cycle(['made by Runnz', 'bot.py', '.help'])
        print("cog loaded")
        super().__init__(command_prefix=self.prefix, case_insensitive=True, intents=discord.Intents.all(),
                         help_command=None)

    def setup(self):
        self._cogs = [p.stem for p in Path(".").glob("./bot/cogs/*.py")]
        print("Running setup ...")

        for cog in self._cogs:
            self.load_extension(f'bot.cogs.{cog}')
            print(f"Loaded `{cog}` cog.")

        print("Setup complete!")

    def run(self):
        self.setup()
        with open("data/token", "r", encoding="utf-8") as f:
            TOKEN = f.read()

        print("Running bot!")
        super().run(TOKEN, reconnect=True)

    async def shutdown(self):
        print("Shutting down the connection to Discord...")
        await super().close()

    async def close(self):
        print("Closing on keyboard interrupt...")
        await self.shutdown()

    async def on_connect(self):
        print(f"Connect to discord (latency:{self.latency * 1000} ms)")

    async def on_resumed(self):
        print("Bot resumed")

    async def on_disconnect(self):
        print("Bot disconnected")

    async def on_error(self, err, *args, **kwargs):
        raise

    async def on_command_error(self, ctx, exc):
        raise getattr(exc, "original", exc)

    @commands.Cog.listener()
    async def on_ready(self):
        self.client_id = (await self.application_info()).id
        await self.wait_until_ready()
        self.change_status.start()
        print("Bot ready to go...")

    @tasks.loop(seconds=3.0)
    async def change_status(self):
        await self.change_presence(activity=discord.Game(next(self.status)))

    async def prefix(self, bot, msg):
        return commands.when_mentioned_or(".")(bot, msg)

    async def process_commands(self, msg):
        ctx = await self.get_context(msg, cls=commands.Context)

        if ctx.command is not None:
            await self.invoke(ctx)

    async def on_message(self, msg):
        if not msg.author.bot:
            await self.process_commands(msg)
