# foundry_mcp_client.py — Part 5: invoke a Foundry prompt agent that has the
# Aldi Store Ops MCP tool registered with OAuth identity passthrough.
#
# Demonstrates the full Foundry-managed OBO consent loop:
#   1. First call for a new user returns an `oauth_consent_request` with a
#      `consent_link`. We surface it and wait for the user to sign in + consent.
#   2. We resubmit with `previous_response_id` to continue.
#   3. We also handle `mcp_approval_request` (require_approval tools).
#
# Unlike the local MAF path, here Foundry performs the OBO exchange and manages
# consent — the client only relays the consent link and approvals.
import os

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
# Name of the Foundry prompt agent that has the MCP tool attached
# (created by register_foundry_mcp_agent.py).
AGENT_NAME = os.environ.get("FOUNDRY_MCP_AGENT_NAME", "Aldi-Filial-Assistent-mcp")

project = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=DefaultAzureCredential())
openai = project.get_openai_client()

AGENT_REF = {"agent_reference": {"name": AGENT_NAME, "type": "agent_reference"}}


def _handle_output(resp, question):
    """Process consent requests and approvals until we get a final answer."""
    while True:
        consent_link = None
        approvals = []
        for item in resp.output:
            if item.type == "oauth_consent_request":
                consent_link = item.consent_link
            elif item.type == "mcp_approval_request":
                approvals.append(item)

        if consent_link:
            print("\n>>> This tool needs your consent (one time).")
            print(">>> Open and sign in, then press Enter here:")
            print("   ", consent_link)
            input()
            resp = openai.responses.create(
                previous_response_id=resp.id,
                input=question,
                extra_body={**AGENT_REF, "tool_choice": "required"},
            )
            continue

        if approvals:
            inputs = []
            for item in approvals:
                print(f"\nApprove MCP call '{getattr(item, 'name', '?')}'? (y/N): ", end="")
                approve = input().strip().lower() == "y"
                inputs.append(
                    {"type": "mcp_approval_response",
                     "approve": approve,
                     "approval_request_id": item.id}
                )
            resp = openai.responses.create(
                previous_response_id=resp.id,
                input=inputs,
                extra_body=AGENT_REF,
            )
            continue

        return resp


def ask(question: str) -> str:
    resp = openai.responses.create(input=question, extra_body=AGENT_REF)
    resp = _handle_output(resp, question)
    return resp.output_text


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "Welche Schichten habe ich diese Woche?"
    print("Q:", q)
    print("A:", ask(q))
