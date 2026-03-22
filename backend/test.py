import asyncio
import logging
import sys

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

from main import run_analysis_pipeline, DEFAULT_SYMBOLS

async def test():
    for sym in DEFAULT_SYMBOLS:
        print(f"Testing {sym}...")
        try:
            res = await run_analysis_pipeline(sym)
            if "error" in res:
                print(f"[{sym}] ERROR: {res['error']}")
            else:
                print(f"[{sym}] SUCCESS")
        except Exception as e:
            print(f"[{sym}] EXCEPTION: {e}")

if __name__ == "__main__":
    asyncio.run(test())
