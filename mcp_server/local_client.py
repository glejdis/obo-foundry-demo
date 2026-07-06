# mcp_server/local_client.py — test the Aldi Store Ops MCP server locally.
#
# Signs the user in (device code -> Tc), connects to the local streamable-HTTP
# MCP server passing the token in the Authorization header (simulating Foundry's
# OAuth identity passthrough), lists tools, and calls both generic and OBO tools.
import asyncio
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auth import get_user_token  # noqa: E402

SERVER_URL = "http://127.0.0.1:8000/mcp"


async def main() -> None:
    token = get_user_token()  # Tc — sign in once
    headers = {"Authorization": f"Bearer {token}"}

    async with streamablehttp_client(SERVER_URL, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Tools:", [t.name for t in tools.tools])

            for name, args in [
                ("get_store_hours", {"day": "Samstag"}),   # generic, no identity
                ("find_product", {"product_name": "Kaffee"}),  # generic
                ("get_my_employee_info", {}),               # OBO -> Graph /me
                ("get_my_shifts", {}),                      # OBO identity -> roster
            ]:
                result = await session.call_tool(name, args)
                text = result.content[0].text if result.content else "(no content)"
                print(f"\n[{name}] -> {text}")


if __name__ == "__main__":
    asyncio.run(main())
