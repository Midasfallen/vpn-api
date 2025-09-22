import asyncio
import os
import sys
import traceback

from vpn_api.wg_easy_adapter import WgEasyAdapter


async def run():
    url = os.environ.get("WG_EASY_URL") or "http://62.84.98.109:8588/"
    pw = os.environ.get("WG_EASY_PASSWORD") or "22qc8VYV25r89ns8"
    print("URL:", url)
    try:
        async with WgEasyAdapter(url, pw) as a:
            print("adapter entered")
            res = await a.create_client("test-from-adapter-xyz")
            print("create res:", res)
    except Exception:
        print("Exception in adapter call:")
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(run())
