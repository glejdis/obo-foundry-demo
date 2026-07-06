# register_foundry_mcp_agent.py — Part 3: create a Foundry prompt agent that
# references the Aldi Store Ops MCP tool with OAuth identity passthrough.
#
# Prerequisites (done in the Foundry portal — see mcp_server/README + main README):
#   1. Deploy the MCP server (mcp_server/deploy.ps1) -> public URL.
#   2. In Foundry, add the MCP server as a Custom tool with OAuth Identity
#      Passthrough (Custom OAuth), reusing the obo-demo app. This creates a
#      project connection whose id you pass below as MCP_CONNECTION_ID.
#   3. Add Foundry's returned redirect URL to the obo-demo app registration.
#
# Then run this script to (re)create the agent that uses that connection.
import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import MCPTool, PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
MODEL_DEPLOYMENT_NAME = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4.1-mini")
AGENT_NAME = os.environ.get("FOUNDRY_MCP_AGENT_NAME", "Aldi-Filial-Assistent-mcp")

# From the deployment + portal connection:
MCP_SERVER_URL = os.environ["MCP_SERVER_URL"]          # https://<app>.<region>.azurecontainerapps.io/mcp
MCP_CONNECTION_ID = os.environ["MCP_CONNECTION_ID"]    # connection id/name from the portal (OAuth passthrough)

project = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=DefaultAzureCredential())

tool = MCPTool(
    server_label="aldi_store_ops",
    server_url=MCP_SERVER_URL,
    require_approval="never",           # demo; use "always" to gate write tools
    project_connection_id=MCP_CONNECTION_ID,
)

INSTRUCTIONS = (
    "Du bist der Aldi Filial-Assistent. Nutze die MCP-Tools von 'aldi_store_ops'. "
    "Beantworte allgemeine Fragen (Öffnungszeiten, Produkte) sowie persönliche "
    "Fragen ('Wer bin ich?', 'meine Schichten') — letztere greifen im Namen des "
    "angemeldeten Mitarbeiters auf dessen Daten zu. Antworte kurz auf Deutsch."
)

agent = project.agents.create_version(
    agent_name=AGENT_NAME,
    definition=PromptAgentDefinition(
        model=MODEL_DEPLOYMENT_NAME,
        instructions=INSTRUCTIONS,
        tools=[tool],
    ),
)
print(f"Agent created: {agent.name} (v{agent.version})")
print("Now run:  python foundry_mcp_client.py \"Welche Schichten habe ich?\"")
