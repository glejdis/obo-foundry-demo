# agent.py — Steps 5 & 6: Foundry prompt agent with a client-side function tool.
# The function executes in THIS process, where the OBO exchange happens.
import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from auth import get_user_token
from obo import get_my_profile

load_dotenv()

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
MODEL_DEPLOYMENT_NAME = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4o-mini")

project = AIProjectClient(
    endpoint=PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
)
openai = project.get_openai_client()

# Client-side function tool declaration (no server required).
profile_tool = {
    "type": "function",
    "name": "get_my_profile",
    "description": "Get the signed-in user's name, title and department.",
    "parameters": {"type": "object", "properties": {}, "required": []},
}


def main() -> None:
    agent = project.agents.create_version(
        agent_name="obo-demo",
        definition=PromptAgentDefinition(
            model=MODEL_DEPLOYMENT_NAME,
            instructions=(
                "When the user asks about themselves, call get_my_profile "
                "and answer using its result."
            ),
            tools=[profile_tool],
        ),
    )
    print(f"Agent ready: {agent.name} (v{agent.version})")

    user_token = get_user_token()  # Tc — sign in once

    resp = openai.responses.create(
        input="Who am I?",
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
    )

    tool_outputs = []
    for item in resp.output:
        if item.type == "function_call" and item.name == "get_my_profile":
            result = get_my_profile(user_token)  # <-- OBO happens here
            tool_outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": result,
                }
            )

    if tool_outputs:
        resp = openai.responses.create(
            input=tool_outputs,
            previous_response_id=resp.id,
            extra_body={
                "agent_reference": {"name": agent.name, "type": "agent_reference"}
            },
        )

    print("\nAgent:", resp.output_text)


if __name__ == "__main__":
    main()
