import asyncio
import datetime as dt
import re
import typing as t
from enum import Enum

import discord
import wavelink
from discord.ext import commands

URL_REGEX = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
OPTIONS = {
    "1️⃣": 0,
    "2⃣": 1,
    "3⃣": 2,
    "4⃣": 3,
    "5⃣": 4,
}


class AlreadyConnectedToChannel(commands.CommandError):
    pass


class NoVoiceChannel(commands.CommandError):
    pass


class QueueIsEmpty(commands.CommandError):
    pass


class NoTracksFound(commands.CommandError):
    pass


class PlayerIsAlreadyPaused(commands.CommandError):
    pass


class PlayerIsAlreadyPlaying(commands.CommandError):
    pass


class NoMoreTracks(commands.CommandError):
    pass


class NoPreviousTracks(commands.CommandError):
    pass


class InvalidRepeatMode(commands.CommandError):
    pass


class VolumeTooLow(commands.CommandError):
    pass


class VolumeTooHigh(commands.CommandError):
    pass


class MaxVolume(commands.CommandError):
    pass


class MinVolume(commands.CommandError):
    pass


class RepeatMode(Enum):
    NONE = 0
    ONE = 1
    ALL = 2


class Queue:
    def __init__(self):
        self._queue = []
        self.position = 0
        self.repeat_mode = RepeatMode.NONE

    @property
    def is_empty(self):
        return not self._queue

    @property
    def first_track(self):
        if not self._queue:
            raise QueueIsEmpty

        return self._queue[0]

    @property
    def current_track(self):
        if not self._queue:
            raise QueueIsEmpty

        return self._queue[self.position]

    @property
    def upcoming(self):
        if not self._queue:
            raise QueueIsEmpty

        return self._queue[self.position + 1:]

    @property
    def length(self):
        return len(self._queue)

    @property
    def history(self):
        if not self._queue:
            raise QueueIsEmpty
        return self._queue[:self.position]

    def add(self, *args):
        self._queue.extend(args)

    def get_next_track(self):
        if not self._queue:
            raise QueueIsEmpty

        self.position += 1

        if self.position < 0:
            return None
        elif self.position > len(self._queue) - 1:
            if self.repeat_mode == RepeatMode.ALL:
                self.position = 0
            else:
                return None

        return self._queue[self.position]

    # def shuffle(self):
    #     if not self._queue:
    #         raise QueueIsEmpty
    #
    #     upcoming = self.upcoming
    #     random.shuffle(upcoming)
    #     self._queue = self._queue[:self.position + 1]
    #     self._queue.extend(upcoming)
    #

    def set_repeat_mode(self, mode):
        if mode == "off":
            self.repeat_mode = RepeatMode.NONE
        elif mode == "song":
            self.repeat_mode = RepeatMode.ONE
        elif mode == "queue" or mode == "q":
            self.repeat_mode = RepeatMode.ALL

    def empty(self):
        self._queue.clear()


class Player(wavelink.Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = Queue()

    async def connect(self, ctx, channel=None):
        if self.is_connected:
            raise AlreadyConnectedToChannel

        if (channel := getattr(ctx.author.voice, "channel", channel)) is None:
            raise NoVoiceChannel

        await super().connect(channel.id)
        return channel

    # Stop the music
    async def teardown(self):
        try:
            await self.destroy()
        except KeyError:
            pass

    async def add_tracks(self, ctx, tracks):
        if not tracks:
            raise NoTracksFound

        if isinstance(tracks, wavelink.TrackPlaylist):
            self.queue.add(*tracks.tracks)
        elif len(tracks) == 1:
            self.queue.add(tracks[0])
            await ctx.send(f"Added {tracks[0].title} to the queue.")
        else:
            if (track := await self.choose_track(ctx, tracks)) is not None:
                self.queue.add(track)
                await ctx.send(f"Added {track.title} to the queue.")

        if not self.is_playing and not self.queue.is_empty:
            await self.start_playback()

    async def choose_track(self, ctx, tracks):
        def _check(r, u):
            return (
                    r.emoji in OPTIONS.keys()
                    and u == ctx.author
                    and r.message.id == msg.id
            )

        embed = discord.Embed(
            title="Choose a song",
            description=(
                "\n".join(
                    f"**{i + 1}.** {t.title} ({t.length // 60000}:{str(t.length % 60).zfill(2)})"
                    for i, t in enumerate(tracks[:5])
                )
            ),
            colour=ctx.author.colour,
            timestamp=dt.datetime.utcnow()
        )

        embed.set_author(name="Query Results")
        embed.set_footer(text=f"Invoked by {ctx.author.display_name}")

        msg = await ctx.send(embed=embed)

        for emoji in list(OPTIONS.keys())[:min(len(tracks), len(OPTIONS))]:
            await msg.add_reaction(emoji)

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=60.0, check=_check)
        except asyncio.TimeoutError:
            await msg.delete() + 1
            await ctx.message.delete() + 1
        else:
            await msg.delete() + 1
            return tracks[OPTIONS[reaction.emoji]]

    async def start_playback(self):
        await self.play(self.queue.first_track)

    async def advance(self):
        try:
            if (track := self.queue.get_next_track()) is not None:
                await self.play(track)
        except QueueIsEmpty:
            pass

    async def repeat_track(self):
        await self.play(self.queue.current_track)


class Music(commands.Cog, wavelink.WavelinkMixin):
    def __init__(self, bot):
        self.bot = bot
        self.wavelink = wavelink.Client(bot=bot)
        self.bot.loop.create_task(self.start_nodes())

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not member.bot and after.channel is None:
            if not [m for m in before.channel.members if not m.bot]:
                # await self.get_player(member.guild).teardown()
                pass

    @wavelink.WavelinkMixin.listener()
    async def on_node_ready(self, node):
        print(f"Wavelink node {node.identifier} ready.")

    @wavelink.WavelinkMixin.listener("on_track_stuck")
    @wavelink.WavelinkMixin.listener("on_track_end")
    @wavelink.WavelinkMixin.listener("on_track_exception")
    async def on_player_stop(self, payload):
        if payload.player.queue.repeat_mode == RepeatMode.ONE:
            await payload.player.repeat_track()
        else:
            await payload.player.advance()

    async def cog_check(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send("Music commands are not available in DMs")
            return False
        return True

    async def start_nodes(self):
        await self.bot.wait_until_ready()

        nodes = {
            "MAIN": {
                "host": "127.0.0.1",
                "port": 2333,
                "rest_uri": "http://127.0.0.1:2333",
                "password": "youshallnotpass",
                "identifier": "MAIN",
                "region": "europe",
            }
        }

        for node in nodes.values():
            await self.wavelink.initiate_node(**node)

    def get_player(self, obj):
        if isinstance(obj, commands.Context):
            return self.wavelink.get_player(obj.guild.id, cls=Player, context=obj)
        elif isinstance(obj, discord.Guild):
            return self.wavelink.get_player(obj.id, cls=Player)

    # @slash.slash(name = "connect", guild_ids=[890657274236915712] ,description = "Connect the bot to the channel")
    @commands.command(name="connect", aliases=["join"])
    async def connect_command(self, ctx, *, channel: t.Optional[discord.VoiceChannel]):
        player = self.get_player(ctx)
        channel = await player.connect(ctx, channel)
        await ctx.send(f"Connect to {channel.name}.")

    @connect_command.error
    async def connect_command_error(self, ctx, exc):
        if isinstance(exc, AlreadyConnectedToChannel):
            await ctx.send(f"Already connected to a voice channel.")
        elif isinstance(exc, NoVoiceChannel):
            await ctx.send("No suitable voice channel was provided.")

    @commands.command(name="disconnect", aliases=["leave", "lv"])
    async def disconnect_command(self, ctx):
        player = self.get_player(ctx)
        await player.teardown()
        await ctx.send("Disconnect.")

    @commands.command(name="play")
    async def play_command(self, ctx, *, query: t.Optional[str]):
        player = self.get_player(ctx)

        if not player.is_connected:
            await player.connect(ctx)

        # Resume the music
        if query is None:
            await player.set_pause(False)
            await ctx.send("Music resumed")

        else:
            query = query.strip(" ")
            if not re.match(URL_REGEX, query):
                query = f"ytsearch:{query}"

            await player.add_tracks(ctx, await self.wavelink.get_tracks(query))

    @play_command.error
    async def play_command_error(self, ctx, exc):
        if isinstance(exc, PlayerIsAlreadyPlaying):
            await ctx.send("Already playing")
        elif isinstance(exc, QueueIsEmpty):
            await ctx.send("No songs to play because the queue is empty")

    @commands.command(name="resume", aliases=["rs"])
    async def resume_command(self, ctx, *, query: t.Optional[str]):
        player = self.get_player(ctx)
        # Resume the music
        if query is None:
            await player.set_pause(False)
            await ctx.send("Music resumed")

    @play_command.error
    async def resume_command_error(self, ctx, exc):
        if isinstance(exc, PlayerIsAlreadyPlaying):
            await ctx.send("Music is already playing")
        elif isinstance(exc, QueueIsEmpty):
            await ctx.send("No songs to play because the queue is empty")

    @commands.command(name="pause", aliases=["p"])
    async def pause_command(self, ctx):
        player = self.get_player(ctx)

        if player.is_paused:
            raise PlayerIsAlreadyPaused

        await player.set_pause(True)
        await ctx.send("Music paused")

    @pause_command.error
    async def clear_queue_command_error(self, ctx, exc):
        if isinstance(exc, PlayerIsAlreadyPaused):
            await ctx.send("The queue has already cleared ")

    @commands.command(name="next", aliases=["skip"])
    async def next_command(self, ctx):
        player = self.get_player(ctx)

        if not player.queue.upcoming:
            raise NoMoreTracks

        await player.stop()
        await ctx.send("Playing next track in queue")

    @next_command.error
    async def next_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            await ctx.send("Cannot skip because the queue is empty")
        elif isinstance(exc, NoMoreTracks):
            await ctx.send("There are no more tracks in the queue to play")

    @commands.command(name="previous")
    async def previous_command(self, ctx):
        player = self.get_player(ctx)

        if not player.queue.history:
            raise NoPreviousTracks

        player.queue.position -= 2
        await player.stop()
        await ctx.send("Playing previous track in queue")

    @previous_command.error
    async def previous_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            await ctx.send("Cannot see the previous tracks because the queue is empty")
        elif isinstance(exc, NoPreviousTracks):
            await ctx.send("There are no more tracks in the queue to play")

    # @commands.command(name="shuffle",aliases=["shlf","sh"])
    # async def shuffle_command(self, ctx):
    #     player = self.get_player(ctx)
    #     player.queue.shuffle()
    #     await ctx.send("Queue shuffled.")
    #
    # @shuffle_command.error
    # async def shuffle_command_error(self, ctx, exc):
    #     if isinstance(exc, QueueIsEmpty):
    #         await ctx.send("The queue could not be shuffled as it is currently empty.")

    @commands.command(name="repeat", aliases=["rpt", "rp"])
    async def repeat_command(self, ctx, mode: str):
        if mode not in ("off", "song", "queue", "q"):
            raise InvalidRepeatMode

        player = self.get_player(ctx)
        player.queue.set_repeat_mode(mode)

        if mode == "off":
            await ctx.send(f"RepeatMode  ➡️  Off ...")
        elif mode == "song":
            await ctx.send(f"Repeating current song  ➡️  {player.queue.current_track} ...")
        elif mode == "queue" or mode == "q":
            await ctx.send("RepeatMode  ➡️  Queue ...")

    @commands.command(name="restart")
    async def restart_command(self, ctx):
        player = self.get_player(ctx)

        if player.queue.is_empty:
            raise QueueIsEmpty

        await player.seek(0)
        await ctx.send("Track restarted.")

    @restart_command.error
    async def restart_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            await ctx.send("There are no tracks in the queue.")

    @commands.command(name="queue", aliases=["q"], value="dfefezfzefez")
    async def queue_command(self, ctx, show: t.Optional[int] = 10):
        player = self.get_player(ctx)

        embed = discord.Embed(
            title="Queue",
            description=f"Showing up to next {show} tracks",
            colour=ctx.author.colour,
            timestamp=dt.datetime.utcnow()
        )

        embed.set_author(name="Query Results")
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar_url)
        embed.add_field(
            name="Currently playing",
            value=getattr(player.queue.current_track, "title", "No tracks currently playing."),
            inline=False
        )
        if upcoming := player.queue.upcoming:
            embed.add_field(
                name="Next up",
                value="\n".join("✅ " + t.title for t in upcoming[:show]),
                inline=False
            )

        msg = await ctx.send(embed=embed)

    @queue_command.error
    async def queue_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            await ctx.send("The queue is currently empty.")

    @commands.command(name="clearqueue", aliases=[".clearq"])
    async def clear_queue_command(self, ctx):
        player = self.get_player(ctx)
        player.queue.empty()
        await ctx.send("The queue has been cleared")

    @commands.command(name="playing", aliases=["np"])
    async def playing_command(self, ctx):
        player = self.get_player(ctx)

        if not player.is_playing:
            raise PlayerIsAlreadyPaused

        embed = discord.Embed(
            title="Now playing",
            colour=ctx.author.colour,
            timestamp=dt.datetime.utcnow(),
        )
        embed.set_author(name="Playback Information")
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar_url)
        embed.add_field(name="Track title", value=player.queue.current_track.title, inline=False)
        embed.add_field(name="Artist", value=player.queue.current_track.author, inline=False)

        position = divmod(player.position, 60000)
        length = divmod(player.queue.current_track.length, 60000)
        embed.add_field(
            name="Position",
            value=f"{int(position[0])}:{round(position[1] / 1000):02}/{int(length[0])}:{round(length[1] / 1000):02}",
            inline=False
        )

        await ctx.send(embed=embed)

    @playing_command.error
    async def playing_command_error(self, ctx, exc):
        if isinstance(exc, PlayerIsAlreadyPaused):
            await ctx.send("There is no track currently playing.")

    @commands.command(name="skipto")
    async def skipto_command(self, ctx, index: int):
        player = self.get_player(ctx)

        if player.queue.is_empty:
            raise QueueIsEmpty

        if not 0 <= index <= player.queue.length:
            raise NoMoreTracks

        player.queue.position = index - 2
        await player.stop()
        await ctx.send(f"Playing track in position {index}.")

    @skipto_command.error
    async def skipto_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            await ctx.send("There are no tracks in the queue.")
        elif isinstance(exc, NoMoreTracks):
            await ctx.send("That index is out of the bounds of the queue.")

    @commands.group(name="volume", invoke_without_command=True)
    async def volume_group(self, ctx, volume: int):
        player = self.get_player(ctx)

        if volume < 0:
            raise VolumeTooLow

        if volume > 150:
            raise VolumeTooHigh

        await player.set_volume(volume)
        await ctx.send(f"Volume set to {volume:,}%")

    @volume_group.error
    async def volume_group_error(self, ctx, exc):
        if isinstance(exc, VolumeTooLow):
            await ctx.send("The volume must be 0% or above.")
        elif isinstance(exc, VolumeTooHigh):
            await ctx.send("The volume must be 150% or below.")

    @volume_group.command(name="up", aliases=["+"])
    async def volume_up_command(self, ctx):
        player = self.get_player(ctx)

        if player.volume == 150:
            raise MaxVolume

        await player.set_volume(value := min(player.volume + 10, 150))
        await ctx.send(f"Volume set to {value:,}%")

    @volume_up_command.error
    async def volume_up_command_error(self, ctx, exc):
        if isinstance(exc, MaxVolume):
            await ctx.send("The player is already at max volume.")

    @volume_group.command(name="down", aliases=["d", "dw", "-"])
    async def volume_down_command(self, ctx):
        player = self.get_player(ctx)

        if player.volume == 0:
            raise MinVolume

        await player.set_volume(value := max(0, player.volume - 10))
        await ctx.send(f"Volume set to {value:,}%")

    @volume_down_command.error
    async def volume_down_command_error(self, ctx, exc):
        if isinstance(exc, MinVolume):
            await ctx.send("The player is already at min volume.")


def setup(bot):
    bot.add_cog(Music(bot))
