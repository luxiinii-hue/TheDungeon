"""Entry point for Dungeon of the Acoc."""

import asyncio
from src.core.game import Game


async def main():
    game = Game()
    await game.run()


if __name__ == "__main__":
    asyncio.run(main())
