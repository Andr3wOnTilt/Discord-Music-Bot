from i18n import t
import discord
from discord.ext import commands
import asyncio
import yt_dlp
from collections import deque
import logging

logger = logging.getLogger(__name__)

YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data      = data
        self.title     = data.get("title", "Unknown")
        self.url       = data.get("webpage_url", "")
        self.duration  = data.get("duration", 0)
        self.thumbnail = data.get("thumbnail", "")
        self.uploader  = data.get("uploader", "Unknown")

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=not stream))
        if "entries" in data:
            data = data["entries"][0]
        filename = data["url"] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS), data=data)


class GuildMusicState:
    def __init__(self):
        self.queue        = deque()
        self.current      = None
        self.voice_client = None
        self.volume       = 0.5
        self.loop         = False

    def is_playing(self):
        return self.voice_client and self.voice_client.is_playing()

    def is_paused(self):
        return self.voice_client and self.voice_client.is_paused()


class MusicManager(commands.Cog, name="Music"):
    def __init__(self, bot):
        self.bot    = bot
        self._states = {}

    def get_state(self, guild_id):
        if guild_id not in self._states:
            self._states[guild_id] = GuildMusicState()
        return self._states[guild_id]

    def _e(self, title, description=None, color=0x5865F2):
        em = discord.Embed(title=title, description=description, color=color)
        em.set_footer(text=t("footer_music"))
        return em

    def _err(self, msg):
        return self._e(t("err_title"), msg, 0xf23f43)

    async def _ensure_voice(self, ctx):
        if not ctx.author.voice:
            await ctx.send(embed=self._err(t("err_voice")))
            return False
        state = self.get_state(ctx.guild.id)
        if not state.voice_client or not state.voice_client.is_connected():
            state.voice_client = await ctx.author.voice.channel.connect()
        elif ctx.author.voice.channel != state.voice_client.channel:
            await state.voice_client.move_to(ctx.author.voice.channel)
        return True

    async def _play_next(self, ctx):
        state = self.get_state(ctx.guild.id)
        if state.loop and state.current:
            try:
                source = await YTDLSource.from_url(state.current.url, loop=self.bot.loop)
                state.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(
                    self._play_next(ctx), self.bot.loop))
                state.current = source
            except Exception as err:
                logger.error(err)
        elif state.queue:
            url = state.queue.popleft()
            try:
                source = await YTDLSource.from_url(url, loop=self.bot.loop)
                state.current = source
                state.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(
                    self._play_next(ctx), self.bot.loop))
                dur = f"{source.duration // 60}:{source.duration % 60:02d}"
                em = self._e(t("now_playing"), f"**[{source.title}]({source.url})**")
                em.add_field(name=t("duration"), value=f"`{dur}`")
                em.add_field(name=t("uploader"),  value=source.uploader)
                if source.thumbnail:
                    em.set_thumbnail(url=source.thumbnail)
                await ctx.send(embed=em)
            except Exception as err:
                await ctx.send(embed=self._err(str(err)))
                await self._play_next(ctx)
        else:
            state.current = None

    @commands.command(name="play", aliases=["p"])
    async def play(self, ctx, *, query: str):
        if not await self._ensure_voice(ctx):
            return
        state = self.get_state(ctx.guild.id)
        async with ctx.typing():
            try:
                url = query if query.startswith("http") else f"ytsearch:{query}"
                if state.is_playing() or state.is_paused():
                    state.queue.append(url)
                    data = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: ytdl.extract_info(url, download=False))
                    if "entries" in data:
                        data = data["entries"][0]
                    em = self._e(t("added_queue"), f"**{data.get('title','?')}**", 0x23a55a)
                    em.add_field(name=t("position"), value=f"`#{len(state.queue)}`")
                    await ctx.send(embed=em)
                else:
                    source = await YTDLSource.from_url(url, loop=self.bot.loop)
                    state.current = source
                    source.volume = state.volume
                    state.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(
                        self._play_next(ctx), self.bot.loop))
                    dur = f"{source.duration // 60}:{source.duration % 60:02d}"
                    em = self._e(t("now_playing"), f"**[{source.title}]({source.url})**")
                    em.add_field(name=t("duration"), value=f"`{dur}`")
                    em.add_field(name=t("uploader"),  value=source.uploader)
                    if source.thumbnail:
                        em.set_thumbnail(url=source.thumbnail)
                    await ctx.send(embed=em)
            except Exception as err:
                await ctx.send(embed=self._err(str(err)))

    @commands.command(name="pause")
    async def pause(self, ctx):
        state = self.get_state(ctx.guild.id)
        if state.is_playing():
            state.voice_client.pause()
            await ctx.send(embed=self._e(t("paused"), t("playback_paused"), 0xf0b232))
        else:
            await ctx.send(embed=self._err(t("err_no_song")))

    @commands.command(name="resume", aliases=["r"])
    async def resume(self, ctx):
        state = self.get_state(ctx.guild.id)
        if state.is_paused():
            state.voice_client.resume()
            await ctx.send(embed=self._e(t("resumed"), t("playback_resumed"), 0x23a55a))
        else:
            await ctx.send(embed=self._err(t("err_not_paused")))

    @commands.command(name="skip", aliases=["s"])
    async def skip(self, ctx):
        state = self.get_state(ctx.guild.id)
        if state.is_playing():
            state.voice_client.stop()
            await ctx.send(embed=self._e(t("skipped"), t("song_skipped")))
        else:
            await ctx.send(embed=self._err(t("err_no_song")))

    @commands.command(name="stop")
    async def stop(self, ctx):
        state = self.get_state(ctx.guild.id)
        state.queue.clear()
        state.loop = False
        if state.voice_client:
            state.voice_client.stop()
            await state.voice_client.disconnect()
            state.voice_client = None
        await ctx.send(embed=self._e(t("stopped"), t("stop_msg"), 0xf23f43))

    @commands.command(name="queue", aliases=["q"])
    async def queue_cmd(self, ctx):
        state = self.get_state(ctx.guild.id)
        em = discord.Embed(title=t("queue_title"), color=0x5865F2)
        if state.current:
            em.add_field(name=t("now_playing_lbl"),
                         value=f"`{state.current.title}`", inline=False)
        if state.queue:
            q_list = list(state.queue)[:10]
            lines  = "\n".join(f"`{i+1}.` {u}" for i, u in enumerate(q_list))
            em.add_field(name=t("next_songs", n=len(state.queue)),
                         value=lines, inline=False)
        else:
            em.add_field(name=t("queue_title"), value=t("queue_empty"), inline=False)
        em.add_field(name=t("loop_lbl"),
                     value=t("loop_on") if state.loop else t("loop_off"))
        em.add_field(name=t("volume_lbl"), value=f"{int(state.volume * 100)}%")
        em.set_footer(text=t("footer_music"))
        await ctx.send(embed=em)

    @commands.command(name="volume", aliases=["vol"])
    async def volume(self, ctx, vol: int):
        state = self.get_state(ctx.guild.id)
        if not 0 <= vol <= 100:
            await ctx.send(embed=self._err(t("err_vol_range")))
            return
        state.volume = vol / 100
        if state.current:
            state.current.volume = state.volume
        await ctx.send(embed=self._e(t("vol_title"), t("vol_set", vol=vol), 0x23a55a))

    @commands.command(name="loop")
    async def loop_cmd(self, ctx):
        state = self.get_state(ctx.guild.id)
        state.loop = not state.loop
        status = t("loop_status_on") if state.loop else t("loop_status_off")
        color  = 0x23a55a if state.loop else 0xf23f43
        await ctx.send(embed=self._e(t("loop_title"), status, color))

    @commands.command(name="nowplaying", aliases=["np"])
    async def now_playing(self, ctx):
        state = self.get_state(ctx.guild.id)
        if state.current:
            dur = f"{state.current.duration // 60}:{state.current.duration % 60:02d}"
            em  = self._e(t("now_playing"), f"**[{state.current.title}]({state.current.url})**")
            em.add_field(name=t("duration"), value=f"`{dur}`")
            em.add_field(name=t("volume_lbl"), value=f"`{int(state.volume * 100)}%`")
            em.add_field(name=t("loop_lbl"),
                         value=t("loop_on") if state.loop else t("loop_off"))
            if state.current.thumbnail:
                em.set_thumbnail(url=state.current.thumbnail)
            await ctx.send(embed=em)
        else:
            await ctx.send(embed=self._err(t("err_no_song")))

    @commands.command(name="clear_queue", aliases=["cq"])
    async def clear_queue(self, ctx):
        state = self.get_state(ctx.guild.id)
        state.queue.clear()
        await ctx.send(embed=self._e(t("queue_clear_t"), t("queue_cleared"), 0xf0b232))

    @commands.command(name="join")
    async def join(self, ctx):
        if await self._ensure_voice(ctx):
            ch = ctx.author.voice.channel.name
            await ctx.send(embed=self._e(t("connected"), t("connected_to", ch=ch), 0x23a55a))

    @commands.command(name="leave", aliases=["dc"])
    async def leave(self, ctx):
        state = self.get_state(ctx.guild.id)
        if state.voice_client:
            await state.voice_client.disconnect()
            state.voice_client = None
            await ctx.send(embed=self._e(t("disconnected"), t("disconnected_msg"), 0xf0b232))


async def setup(bot):
    await bot.add_cog(MusicManager(bot))