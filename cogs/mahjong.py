import re
import json
import discord
from dataclasses import dataclass

from os.path import join, dirname
from typing import Optional
from random import sample
from discord.ext import commands
from utility.func import getLogger


logger = getLogger(__name__)


class MahjongDrawer:
    WINDS: dict[str, str] = {"TON": "東", "NAN": "南", "SHAA": "西", "PEI": "北"}
    TILE_BACK: str = " █ "
    DRAWN_USERS: set[str] = set()
    reveal_tile_index: int = 0

    def __init__(self) -> None:
        self.new_set()

    def current_revealed_tiles(self) -> str:
        num_backs = 4 - self.num_reveal_tiles
        return " ".join(self.reveal_winds[: self.num_reveal_tiles]) + self.TILE_BACK * num_backs

    def new_set(self) -> None:
        self.reveal_tile_index = 0
        self.wind_set = sample(self.WINDS.keys(), 4)
        self.reveal_winds = [self.WINDS[key] for key in self.wind_set]

    def reveal_next(self, user: str) -> str:
        self.DRAWN_USERS.add(user)
        if self.all_revealed():
            return None
        current_tile = self.last_revealed_tile()
        self.reveal_tile_index += 1
        return current_tile

    def last_revealed_tile(self) -> str:
        cur_tile = self.reveal_tile_index
        return self.reveal_winds[cur_tile] if cur_tile >= 0 else self.TILE_BACK

    def all_revealed(self):
        return self.num_reveal_tiles >= 3

    @property
    def num_reveal_tiles(self) -> int:
        reveal_tile = [0, 1, 2, 4, 4]
        return reveal_tile[self.reveal_tile_index]


@dataclass
class ScoreInfo:
    hand_name: Optional[str]
    han: int
    fu: int
    dealer_score: str
    non_dealer_score: str
    extra_msg: Optional[str]


class MahjongScore:
    VALID_FU = [20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 110]

    def __init__(self) -> None:
        score_table_fd = join(dirname(__file__), "score_tables")
        dealer_fn = join(score_table_fd, "dealer.json")
        nondealer_fn = join(score_table_fd, "nondealer.json")

        with open(dealer_fn) as dealer_json:
            self.dealer = json.load(dealer_json)

        with open(nondealer_fn) as nondealer_json:
            self.non_dealer = json.load(nondealer_json)

    def parse_input(self, han_fu: list[int], explicit: list[str]) -> dict:
        if set(explicit) == {"han", "fu"}:
            if len(han_fu) < 2:
                return None
            # Explicit han and fu. Both can be anything and fu will be coerced to correct
            han_fu_dict = dict(zip(explicit, han_fu[:2]))
            han_fu_dict["fu"] = self.round_up_to_closest_number(han_fu_dict["fu"], self.VALID_FU)
            return han_fu_dict
        elif len(han_fu) == 1:
            fu = self.round_up_to_closest_number(0, self.VALID_FU)
            if han_fu[0] == 1:
                fu = 30
            return {"han": han_fu[0], "fu": fu}
        elif (han_fu[0] < 20 and han_fu[0] > 0) ^ (han_fu[1] < 20 and han_fu[1] > 0):
            if han_fu[0] < 20 and han_fu[0] > 0:
                fu = self.round_up_to_closest_number(han_fu[1], self.VALID_FU)
                return {"han": han_fu[0], "fu": fu}
            else:
                fu = self.round_up_to_closest_number(han_fu[0], self.VALID_FU)
                return {"han": han_fu[1], "fu": fu}
        else:
            return None

    def get_table(self, han: int, fu: int) -> ScoreInfo:
        # han expected to be between 1 and 13. Fu should be validated before
        han = max(1, min(han, 13))
        table_index = str(han - 1)

        hand_name = self.dealer["Hand Name"][table_index]
        if not hand_name:
            if han == 3 and fu >= 70:
                hand_name = "Mangan"
            if han == 4 and fu >= 40:
                hand_name = "Mangan"

        extra_msg = None
        if (han == 3 and fu == 60) or (han == 4 and fu == 30):
            extra_msg = "If kiriage mangan. Round up.\ndealer: 4000 12000\nnon dealer: 2000/4000 8000"

        score_info = ScoreInfo(
            hand_name=hand_name,
            han=han,
            fu=fu,
            dealer_score=self.dealer[str(fu)][table_index],
            non_dealer_score=self.non_dealer[str(fu)][table_index],
            extra_msg=extra_msg,
        )

        return score_info

    @staticmethod
    def round_up_to_closest_number(n, numbers):
        for x in numbers:
            if x >= n:
                return x
        return numbers[-1]


class Mahjong(commands.Cog):
    mahjong_drawer: MahjongDrawer = None

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def test(self, ctx: commands.Context, *args):
        if ctx.author.name == "qvnsq":
            self.mahjong_drawer = MahjongDrawer()
            await ctx.send(self.mahjong_drawer.current_revealed_tiles())

    @commands.command()
    async def winds(
        self,
        ctx: commands.Context,
        members: commands.Greedy[discord.Member] = None,
        *,
        force: str = "",
    ) -> None:
        if not self.mahjong_drawer or force.lower() == "force" or self.mahjong_drawer.all_revealed():
            self.mahjong_drawer = MahjongDrawer()

        draw_msg = ""
        if members:
            for member in members[:4]:
                cur_tile = self.mahjong_drawer.reveal_next(member.name)
                draw_msg += f"{member.name} drew: {cur_tile}\n"
        draw_msg += "\n"

        drawn_tiles = self.mahjong_drawer.current_revealed_tiles()
        msg = f"""{draw_msg}Tiles:

        {drawn_tiles}
        """
        await ctx.send(msg)

    @commands.command()
    async def draw(
        self,
        ctx: commands.Context,
        members: commands.Greedy[discord.Member] = None,
        *,
        force: str = "",
    ) -> None:
        if not self.mahjong_drawer or self.mahjong_drawer.all_revealed():
            self.mahjong_drawer = MahjongDrawer()

        force = force.lower()
        draw_msg = ""
        cmd_user = ctx.author.display_name

        if members:
            given_list = [member.name for member in members]
            draw_list = list(dict.fromkeys(given_list))
            no_draw_list = self.mahjong_drawer.DRAWN_USERS
            for user in draw_list:
                if user in no_draw_list:
                    draw_msg += f"{user} has already drawn\n"
                    continue
                cur_tile = self.mahjong_drawer.reveal_next(user)
                if cur_tile:
                    draw_msg += f"{user} drew: {cur_tile}\n"
                else:
                    break
        else:
            if cmd_user in self.mahjong_drawer.DRAWN_USERS and force != "force":
                await ctx.send(
                    f"You've already drawn, {cmd_user}. Type it in again with force or tag yourself if you want to draw."
                )
                return
            else:
                if cur_tile := self.mahjong_drawer.reveal_next(cmd_user):
                    draw_msg += f"{cmd_user} drew: {cur_tile}\n"

        drawn_tiles = self.mahjong_drawer.current_revealed_tiles()
        draw_msg += f"""

        Tiles:
        {drawn_tiles}
        """

        await ctx.send(draw_msg)

    @commands.command()
    async def score(self, ctx: commands.Context, *args):
        scorer = MahjongScore()
        han_fu = []
        explicit = []
        for arg in args:
            nums = [int(i) for i in re.findall(r"\d+", arg)]
            strs = [s for s in re.split(r"[^a-zA-Z]", arg)]
            han_fu.extend(nums)
            explicit.extend(strs)

        explicit = [e for e in explicit if e is not None and e != ""]
        han_fu_inputs = scorer.parse_input(han_fu[:2], explicit[:2])
        if not han_fu_inputs:
            await ctx.send(
                f"Unable to understand your input, {ctx.author.display_name}.\nPlease try again with command like ?score 1 han 20 fu."
            )
            return

        score_table: ScoreInfo = scorer.get_table(**han_fu_inputs)
        if score_table.han < 5:
            msg = f"{score_table.han} han {score_table.fu} fu\n"
        else:
            msg = ""

        msg += f"""dealer: {score_table.dealer_score}
non dealer: {score_table.non_dealer_score}
        """

        if score_table.extra_msg:
            msg += f"\n{score_table.extra_msg}"

        if score_table.hand_name:
            msg += f"\n{score_table.hand_name}!!"

        await ctx.send(msg)


async def setup(bot):
    await bot.add_cog(Mahjong(bot))
