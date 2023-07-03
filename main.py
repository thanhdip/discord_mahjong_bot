import os
import discord
import logging
import asyncio
from os.path import join, dirname
from dotenv import load_dotenv
from utility.func import getLogger
from discord.ext import commands

from aiohttp import ClientSession

logger = getLogger(__name__)
dotenv_path = join(dirname(__file__), ".env")
load_dotenv(dotenv_path)


class MahjongBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="?", intents=intents)
        self.loaded_cogs = ["cogs.mahjong"]

        self._connected = None
        self.session = None
        self.token = os.environ.get("MAHJONG_DISCORD_TOKEN")

        self._configure_logging()

    def _configure_logging(self):
        level_text = os.environ.get("log_level")
        logging_levels = {
            "CRITICAL": logging.CRITICAL,
            "ERROR": logging.ERROR,
            "WARNING": logging.WARNING,
            "INFO": logging.INFO,
            "DEBUG": logging.DEBUG,
        }
        logger.line()

        log_level = logging_levels.get(level_text)
        if log_level is None:
            logger.warning("Invalid logging level set: %s.", level_text)
            logger.warning("Using default logging level: INFO.")
        else:
            logger.info("Logging level: %s", level_text)

        logger.debug("Successfully configured logging.")

    def run(self):
        async def runner():
            async with self:
                self._connected = asyncio.Event()
                self.session = ClientSession(loop=self.loop)

                try:
                    await self.start(self.token)
                except discord.PrivilegedIntentsRequired:
                    logger.critical(
                        "Privileged intents are not explicitly granted in the discord developers dashboard."
                    )
                except discord.LoginFailure:
                    logger.critical("Invalid token")
                except Exception:
                    logger.critical("Fatal exception", exc_info=True)
                finally:
                    if self.session:
                        await self.session.close()
                    if not self.is_closed():
                        await self.close()

        async def _cancel_tasks():
            async with self:
                task_retriever = asyncio.all_tasks
                loop = self.loop
                tasks = {t for t in task_retriever() if not t.done() and t.get_coro() != cancel_tasks_coro}

                if not tasks:
                    return

                logger.info("Cleaning up after %d tasks.", len(tasks))
                for task in tasks:
                    task.cancel()

                await asyncio.gather(*tasks, return_exceptions=True)
                logger.info("All tasks finished cancelling.")

                for task in tasks:
                    try:
                        if task.exception() is not None:
                            loop.call_exception_handler(
                                {
                                    "message": "Unhandled exception during Client.run shutdown.",
                                    "exception": task.exception(),
                                    "task": task,
                                }
                            )
                    except (asyncio.InvalidStateError, asyncio.CancelledError):
                        pass

        try:
            asyncio.run(runner(), debug=bool(os.getenv("DEBUG_ASYNCIO")))
        except (KeyboardInterrupt, SystemExit):
            logger.info("Received signal to terminate bot and event loop.")
        finally:
            logger.info("Cleaning up tasks.")

            try:
                cancel_tasks_coro = _cancel_tasks()
                asyncio.run(cancel_tasks_coro)
            finally:
                logger.info("Closing the event loop.")

    async def on_connect(self):
        # Load all defined cogs
        for cog in self.loaded_cogs:
            if cog in self.extensions:
                continue
            logger.debug("Loading %s.", cog)
            try:
                await self.load_extension(cog)
                logger.debug("Successfully loaded %s.", cog)
            except Exception:
                logger.exception("Failed to load %s.", cog)
        logger.line("debug")


def main():
    # Set up discord.py internal logging
    if os.environ.get("LOG_DISCORD"):
        logger.debug(f"Discord logging enabled: {os.environ['LOG_DISCORD'].upper()}")
        d_logger = logging.getLogger("discord")

        d_logger.setLevel(os.environ["LOG_DISCORD"].upper())
        handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
        handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
        d_logger.addHandler(handler)

    bot = MahjongBot()
    bot.run()


if __name__ == "__main__":
    main()
