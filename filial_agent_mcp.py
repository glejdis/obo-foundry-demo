# filial_agent_mcp.py — Aldi Filial-Assistent that gets its tools from the custom
# Aldi Store Ops MCP server, built with Microsoft Agent Framework (MAF).
#
# This is Flow B of the two-agent OBO demo, both built with MAF:
#   filial_agent_obo.py   -> Flow A: OBO exchange runs IN-PROCESS (no MCP)
#   filial_agent_mcp.py   -> Flow B: tools come from a CUSTOM MCP server (this file)
#
# Here MAF runs the tool-calling loop, but the tools live on the remote MCP
# server. We sign the user in once (device code -> Tc) and attach the token to
# every MCP request via the Authorization header — this is the OAuth identity
# passthrough the server expects. The MCP server then runs the OBO exchange and
# calls Microsoft Graph AS THE SIGNED-IN EMPLOYEE (same mechanism Foundry uses
# when it manages the passthrough).
import asyncio
import os
import sys

import httpx
from agent_framework import MCPStreamableHTTPTool
from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

from auth import get_user_token

load_dotenv()

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
MODEL_DEPLOYMENT_NAME = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4.1-mini")
# Local server by default; set to the deployed Container Apps URL to use that one.
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp")

INSTRUCTIONS = (
    "Du bist der Aldi Filial-Assistent. Nutze die MCP-Tools von 'aldi_store_ops'. "
    "Beantworte allgemeine Fragen (Öffnungszeiten, Produkte) sowie persönliche "
    "Fragen ('Wer bin ich?', 'meine Schichten') — letztere greifen im Namen des "
    "angemeldeten Mitarbeiters auf dessen Daten zu. Antworte kurz auf Deutsch."
)


async def main() -> None:
    token = get_user_token()  # Tc — sign in once; passed to the MCP server below.

    # A default Authorization header is applied to every request the tool makes
    # (initialize, list_tools, and each tool call), so the MCP server can run the
    # OBO exchange as this user. We own this client, so we close it via async with.
    async with httpx.AsyncClient(headers={"Authorization": f"Bearer {token}"}) as http_client:
        mcp_tool = MCPStreamableHTTPTool(
            name="aldi_store_ops",
            url=MCP_SERVER_URL,
            http_client=http_client,
            # Read-only demo tools -> no approval gate. Use "always_require" to
            # gate write tools behind an approval callback.
            approval_mode="never_require",
        )

        # Entering the tool's context connects to the server and loads its tools
        # before the agent is created.
        async with DefaultAzureCredential() as credential, mcp_tool:
            client = AzureAIAgentClient(
                project_endpoint=PROJECT_ENDPOINT,
                model_deployment_name=MODEL_DEPLOYMENT_NAME,
                credential=credential,
            )
            try:
                agent = client.as_agent(
                    name="Aldi-Filial-Assistent-mcp",
                    instructions=INSTRUCTIONS,
                    tools=[mcp_tool],
                )
                questions = sys.argv[1:] or [
                    "Wann habt ihr am Samstag geöffnet?",   # generic MCP tool, no identity
                    "Wer bin ich und in welchem Team?",      # OBO in the server -> Graph /me
                    "Welche Schichten habe ich?",            # OBO identity -> my roster
                ]
                for q in questions:
                    resp = await agent.run(q)
                    print("\nQ:", q)
                    print("A:", resp.text)
            finally:
                await client.close()


if __name__ == "__main__":
    asyncio.run(main())
