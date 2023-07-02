from typing import Optional
from random import sample
from discord.ext import commands
from utility.func import getLogger

import discord

logger = getLogger(__name__)


class MahjongDrawer:
    WINDS = {"TON": "東", "NAN": "南", "SHAA": "西", "PEI": "北"}
    TILE_BACK = "█ "

    def __init__(self) -> None:
        self.new_set()

    def reveal_tiles(self, num_reveal: Optional[int] = None) -> str:
        if not num_reveal:
            num_reveal = self.num_reveal_tiles
        num_backs = 4 - num_reveal
        return " ".join(self.reveal_winds[:num_reveal]) + self.TILE_BACK * num_backs

    def new_set(self) -> None:
        self.num_reveal_tiles = 0
        self.wind_set = sample(self.WINDS.keys(), 4)
        self.reveal_winds = [self.WINDS[key] for key in self.wind_set]

    def reveal_next(self) -> str:
        if self.num_reveal_tiles >= 4:
            self.new_set()
        self.num_reveal_tiles += 1
        self.reveal_tiles()
        return self.last_revealed_tile()

    def last_revealed_tile(self) -> str:
        cur_tile = self.num_reveal_tiles - 1
        return self.reveal_winds[cur_tile] if cur_tile >= 0 else self.TILE_BACK


class Mahjong(commands.Cog):
    mahjong_drawer: MahjongDrawer = None

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def winds(
        self,
        ctx: commands.Context,
        members: commands.Greedy[discord.Member],
        *,
        force: str = None,
    ) -> None:
        if not self.mahjong_drawer or force.lower() == "force":
            self.mahjong_drawer = MahjongDrawer()

        draw_msg = ""
        if members:
            for member in members[:4]:
                cur_tile = self.mahjong_drawer.reveal_next()
                draw_msg += f"{member.name} drew: {cur_tile}\n"
        draw_msg += "\n"         

        drawn_tiles = self.mahjong_drawer.reveal_tiles()
        msg = f"""{draw_msg}Tiles:
        
        {drawn_tiles}
        """
        await ctx.send(msg)

    @commands.command()
    async def draw(
        self, ctx: commands.Context, members: commands.Greedy[discord.Member]
    ) -> None:
        if not self.mahjong_drawer:
            await self.winds(ctx)

        user = ctx.author.display_name
        cur_tile = self.mahjong_drawer.reveal_next()
        draw_msg = f"{user} drew: {cur_tile}"

        if members:
            for member in members[:3]:
                cur_tile = self.mahjong_drawer.reveal_next()
                draw_msg += f"{member.name} drew: {cur_tile}"

        drawn_tiles = self.mahjong_drawer.reveal_tiles()
        draw_msg += f"""
        
        {drawn_tiles}
        """

        await ctx.send(draw_msg)


async def setup(bot):
    await bot.add_cog(Mahjong(bot))
