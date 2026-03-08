import asyncio
import json
import sys

import websockets

BROWSER_WS = sys.argv[1]
URL = sys.argv[2]


async def call(ws, method, params=None, msg_id=1):
    await ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
    while True:
        resp = json.loads(await ws.recv())
        if resp.get("id") == msg_id:
            return resp


async def main():
    async with websockets.connect(BROWSER_WS, max_size=2**22) as ws:
        created = await call(ws, "Target.createTarget", {"url": URL}, 1)
        print(json.dumps(created, ensure_ascii=False))
        targets = await call(ws, "Target.getTargets", {}, 2)
        print(json.dumps(targets, ensure_ascii=False))


asyncio.run(main())
