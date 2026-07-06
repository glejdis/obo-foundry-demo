# agent.py — Phase 1 OBO agent, built with Microsoft Agent Framework (MAF).
#
# MAF runs the tool-calling loop. The OBO tool executes in-process and calls
# Microsoft Graph AS THE SIGNED-IN USER via the on-behalf-of exchange.
import asyncio
import os

from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

from auth import get_user_token
from obo import get_my_profile as _get_my_profile

load_dotenv()

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
MODEL_DEPLOYMENT_NAME = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4.1-mini")

# Set after device-code sign-in; read by the OBO tool below.
_USER_TOKEN: str | None = None


def get_my_profile() -> str:
    """Get the signed-in user's name, title and department."""
    return _get_my_profile(_USER_TOKEN)


async def main() -> None:
    global _USER_TOKEN
    _USER_TOKEN = get_user_token()  # Tc — sign in once

    async with DefaultAzureCredential() as credential:
        client = AzureAIAgentClient(
            project_endpoint=PROJECT_ENDPOINT,
            model_deployment_name=MODEL_DEPLOYMENT_NAME,
            credential=credential,
        )
        try:
            agent = client.as_agent(
                name="obo-demo",
                instructions=(
                    "When the user asks about themselves, call get_my_profile "
                    "and answer using its result."
                ),
                tools=[get_my_profile],
            )
            resp = await agent.run("Who am I?")
            print("\nAgent:", resp.text)
        finally:
            await client.close()


if __name__ == "__main__":
    asyncio.run(main())
