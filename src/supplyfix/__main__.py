import asyncio
import sys

from supplyfix.cli import main

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
