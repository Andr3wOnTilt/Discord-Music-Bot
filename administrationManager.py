from i18n import t
import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class AdministrationManager(commands.Cog, name="Admin"):
    def __init__(self, bot):
        self.bot = bot

    def _e(self, title, description=None, color=0x5865F2):
        em = discord.Embed(title=title, description=description, color=color)
        em.timestamp = datetime.utcnow()
        em.set_footer(text=t("footer_admin"))
        return em

    def _err(self, msg):
        return self._e(t("err_title"), msg, 0xf23f43)

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        reason = reason or t("no_reason")
        await member.kick(reason=reason)
        em = self._e(t("kicked"), color=0xf0b232)
        em.add_field(name=t("member"),    value=f"{member.mention}")
        em.add_field(name=t("reason"),    value=reason)
        em.add_field(name=t("moderator"), value=ctx.author.mention)
        await ctx.send(embed=em)

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        reason = reason or t("no_reason")
        await member.ban(reason=reason)
        em = self._e(t("banned"), color=0xf23f43)
        em.add_field(name=t("member"),    value=f"{member.mention}")
        em.add_field(name=t("reason"),    value=reason)
        em.add_field(name=t("moderator"), value=ctx.author.mention)
        await ctx.send(embed=em)

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, *, user_tag: str):
        banned = [entry async for entry in ctx.guild.bans()]
        for entry in banned:
            if f"{entry.user.name}#{entry.user.discriminator}" == user_tag \
                    or str(entry.user.id) == user_tag:
                await ctx.guild.unban(entry.user)
                em = self._e(t("unbanned"), color=0x23a55a)
                em.add_field(name=t("member"),    value=f"`{entry.user}`")
                em.add_field(name=t("moderator"), value=ctx.author.mention)
                await ctx.send(embed=em)
                return
        await ctx.send(embed=self._err(t("user_nf")))

    @commands.command(name="mute")
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, minutes: int = 10, *, reason=None):
        reason = reason or t("no_reason")
        await member.timeout(timedelta(minutes=minutes), reason=reason)
        em = self._e(t("muted"), color=0xf0b232)
        em.add_field(name=t("member"),       value=member.mention)
        em.add_field(name=t("duration_lbl"), value=f"`{minutes} {t('minutes')}`")
        em.add_field(name=t("reason"),       value=reason)
        em.add_field(name=t("moderator"),    value=ctx.author.mention)
        await ctx.send(embed=em)

    @commands.command(name="unmute")
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member):
        await member.timeout(None)
        em = self._e(t("unmuted"), color=0x23a55a)
        em.add_field(name=t("member"),    value=member.mention)
        em.add_field(name=t("moderator"), value=ctx.author.mention)
        await ctx.send(embed=em)

    @commands.command(name="purge", aliases=["clear"])
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int = 10):
        await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(embed=self._e(t("purge_done"), t("purge_msg", n=amount), 0x23a55a))
        await asyncio.sleep(3)
        await msg.delete()

    @commands.command(name="warn")
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, *, reason=None):
        reason = reason or t("no_reason")
        em = self._e(t("warned"), color=0xf0b232)
        em.add_field(name=t("member"),    value=member.mention)
        em.add_field(name=t("reason"),    value=reason)
        em.add_field(name=t("moderator"), value=ctx.author.mention)
        await ctx.send(embed=em)
        try:
            dm = self._e(f"{t('warned')} — {ctx.guild.name}", color=0xf0b232)
            dm.add_field(name=t("reason"), value=reason)
            await member.send(embed=dm)
        except discord.Forbidden:
            pass

    @commands.command(name="embed")
    @commands.has_permissions(manage_messages=True)
    async def embed_builder(self, ctx):

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        async def ask(prompt, optional=False):
            skip = t("skip_word")
            hint = f" *(type `{skip}` to skip)*" if optional else ""
            await ctx.send(embed=self._e(t("embed_builder_t"), f"{prompt}{hint}"))
            try:
                msg = await self.bot.wait_for("message", check=check, timeout=60)
                return None if msg.content.lower() == skip else msg.content
            except asyncio.TimeoutError:
                await ctx.send(embed=self._err(t("eb_timeout_msg")))
                return "__timeout__"

        await ctx.send(embed=self._e(t("embed_builder_t"), t("eb_guide")))

        title = await ask(t("eb_title_q"))
        if not title or title == "__timeout__": return
        desc  = await ask(t("eb_desc_q"),    optional=True)
        if desc == "__timeout__": return
        color_str = await ask(t("eb_color_q"), optional=True)
        if color_str == "__timeout__": return
        footer    = await ask(t("eb_footer_q"), optional=True)
        if footer == "__timeout__": return
        image     = await ask(t("eb_image_q"),  optional=True)
        if image == "__timeout__": return
        thumb     = await ask(t("eb_thumb_q"),  optional=True)
        if thumb == "__timeout__": return
        author    = await ask(t("eb_author_q"), optional=True)
        if author == "__timeout__": return

        fields = []
        add_f  = await ask(t("eb_add_field_q"))
        while add_f and add_f.lower() == t("yes_word"):
            fn = await ask(t("eb_fname_q"))
            if not fn or fn == "__timeout__": break
            fv = await ask(t("eb_fval_q"))
            if not fv or fv == "__timeout__": break
            inl = await ask(t("eb_inline_q"), optional=True)
            fields.append((fn, fv, inl == t("yes_word") if inl else False))
            add_f = await ask(t("eb_another_q"))

        try:
            color = int(color_str.lstrip("#"), 16) if color_str else 0x5865F2
        except Exception:
            color = 0x5865F2

        em = discord.Embed(title=title, description=desc or "", color=color)
        if footer: em.set_footer(text=footer)
        if image:  em.set_image(url=image)
        if thumb:  em.set_thumbnail(url=thumb)
        if author: em.set_author(name=author)
        for fn, fv, inl in fields:
            em.add_field(name=fn, value=fv, inline=inl)
        em.timestamp = datetime.utcnow()

        await ctx.send(content=t("eb_preview"), embed=em)
        confirm = await ask(t("eb_confirm_q"))
        if confirm and confirm.lower() == t("yes_word"):
            ch_ans = await ask(t("eb_channel_q"))
            here_w = t("here_word")
            if ch_ans and ch_ans.lower() != here_w:
                target = discord.utils.get(ctx.guild.text_channels,
                                           name=ch_ans.strip("#"))
            else:
                target = ctx.channel
            if target:
                await target.send(embed=em)
                await ctx.send(embed=self._e(t("eb_sent"), t("eb_sent_msg", ch=target.mention), 0x23a55a))
            else:
                await ctx.send(embed=self._err(t("err_title")))
        else:
            await ctx.send(embed=self._e(t("eb_cancelled"), t("eb_cancel_msg"), 0xf23f43))

    @commands.command(name="quickembed", aliases=["qe"])
    @commands.has_permissions(manage_messages=True)
    async def quick_embed(self, ctx, *, args: str):
        parts = [p.strip() for p in args.split("|")]
        title = parts[0] if len(parts) > 0 else "Embed"
        desc  = parts[1] if len(parts) > 1 else ""
        try:
            color = int(parts[2].lstrip("#"), 16) if len(parts) > 2 else 0x5865F2
        except Exception:
            color = 0x5865F2
        em = discord.Embed(title=title, description=desc, color=color)
        em.timestamp = datetime.utcnow()
        await ctx.send(embed=em)

    @commands.command(name="serverinfo", aliases=["si"])
    async def server_info(self, ctx):
        g  = ctx.guild
        em = self._e(f"{t('server_info_t')} — {g.name}")
        if g.icon:
            em.set_thumbnail(url=g.icon.url)
        em.add_field(name=t("owner"),       value=g.owner.mention)
        em.add_field(name=t("members"),     value=g.member_count)
        em.add_field(name=t("created"),     value=g.created_at.strftime("%d/%m/%Y"))
        em.add_field(name=t("text_ch"),     value=len(g.text_channels))
        em.add_field(name=t("voice_ch"),    value=len(g.voice_channels))
        em.add_field(name=t("roles"),       value=len(g.roles))
        em.add_field(name=t("emojis"),      value=len(g.emojis))
        em.add_field(name=t("verification"),value=str(g.verification_level).capitalize())
        em.add_field(name=t("server_id"),   value=f"`{g.id}`")
        await ctx.send(embed=em)

    @commands.command(name="userinfo", aliases=["ui"])
    async def user_info(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        em = self._e(t("user_info_t"), color=member.color)
        em.set_thumbnail(url=member.display_avatar.url)
        em.add_field(name="ID",                  value=f"`{member.id}`")
        em.add_field(name=t("account_created"),  value=member.created_at.strftime("%d/%m/%Y"))
        em.add_field(name=t("joined"),            value=member.joined_at.strftime("%d/%m/%Y"))
        em.add_field(name=t("top_role"),          value=member.top_role.mention)
        em.add_field(name=t("status"),            value=str(member.status).capitalize())
        roles = [r.mention for r in reversed(member.roles) if r.name != "@everyone"]
        em.add_field(name=f"{t('roles')} ({len(roles)})",
                     value=" ".join(roles[:10]) or "—", inline=False)
        await ctx.send(embed=em)

    @commands.command(name="botinfo")
    async def info_bot(self, ctx):
        em = self._e(t("bot_info_t"))
        em.set_thumbnail(url=self.bot.user.display_avatar.url)
        em.add_field(name=t("ping_lbl"),     value=f"`{round(self.bot.latency * 1000)}ms`")
        em.add_field(name=t("servers"),      value=len(self.bot.guilds))
        em.add_field(name=t("users"),        value=sum(g.member_count for g in self.bot.guilds))
        em.add_field(name=t("commands_lbl"), value=len(self.bot.commands))
        em.add_field(name="ID",              value=f"`{self.bot.user.id}`")
        await ctx.send(embed=em)

    @commands.command(name="ping")
    async def ping(self, ctx):
        ms    = round(self.bot.latency * 1000)
        color = 0x23a55a if ms < 100 else (0xf0b232 if ms < 200 else 0xf23f43)
        await ctx.send(embed=self._e(t("pong"), t("latency", ms=ms), color))

    @commands.command(name="announce")
    @commands.has_permissions(manage_messages=True)
    async def announce(self, ctx, channel: discord.TextChannel, *, message: str):
        em = self._e(t("announcement"), message, 0xf0b232)
        em.set_author(name=ctx.author.display_name,
                      icon_url=ctx.author.display_avatar.url)
        await channel.send(embed=em)
        await ctx.send(embed=self._e(t("ann_sent"),
                                     t("ann_sent_msg", ch=channel.mention), 0x23a55a))

    @kick.error
    @ban.error
    @mute.error
    @purge.error
    async def perm_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(embed=self._err(t("no_perms")))
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(embed=self._err(t("member_nf")))
        else:
            await ctx.send(embed=self._err(str(error)))
            logger.error(error)


async def setup(bot):
    await bot.add_cog(AdministrationManager(bot))