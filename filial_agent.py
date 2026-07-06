# filial_agent.py — a simple Aldi "Filial-Assistent" (store assistant) prompt agent
# with client-side function tools backed by mock store data.
import json
import os
import sys

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
MODEL_DEPLOYMENT_NAME = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4.1-mini")
AGENT_NAME = "Aldi-Filial-Assistent-demo"

project = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=DefaultAzureCredential())
openai = project.get_openai_client()

# ---- Mock store data -------------------------------------------------------
STORE_HOURS = {
    "montag": "07:00–21:00",
    "dienstag": "07:00–21:00",
    "mittwoch": "07:00–21:00",
    "donnerstag": "07:00–21:00",
    "freitag": "07:00–21:00",
    "samstag": "07:00–20:00",
    "sonntag": "geschlossen",
}

PRODUCTS = {
    "milch": {"gang": "3 (Kühlregal)", "preis": "0,95 €", "bestand": 120},
    "brot": {"gang": "1 (Backwaren)", "preis": "1,29 €", "bestand": 45},
    "bananen": {"gang": "0 (Obst & Gemüse)", "preis": "1,49 €/kg", "bestand": 80},
    "schokolade": {"gang": "5 (Süßwaren)", "preis": "0,99 €", "bestand": 200},
    "eier": {"gang": "3 (Kühlregal)", "preis": "1,79 €", "bestand": 60},
    "kaffee": {"gang": "6 (Getränke & Heißgetränke)", "preis": "4,99 €", "bestand": 30},
}


# ---- Tool implementations --------------------------------------------------
def get_store_hours(day: str) -> str:
    d = (day or "").strip().lower()
    if d in STORE_HOURS:
        return f"Öffnungszeiten {day.capitalize()}: {STORE_HOURS[d]}"
    return (
        "Öffnungszeiten: Mo–Fr 07:00–21:00, Sa 07:00–20:00, So geschlossen."
    )


def find_product(product_name: str) -> str:
    q = (product_name or "").strip().lower()
    for name, info in PRODUCTS.items():
        if q in name or name in q:
            return (
                f"{name.capitalize()}: Gang {info['gang']}, Preis {info['preis']}, "
                f"Bestand {info['bestand']} Stück."
            )
    return f"'{product_name}' ist nicht im Sortiment gelistet."


TOOL_IMPLS = {"get_store_hours": get_store_hours, "find_product": find_product}

# ---- Tool declarations (sent to the model) ---------------------------------
TOOLS = [
    {
        "type": "function",
        "name": "get_store_hours",
        "description": "Öffnungszeiten der Filiale für einen Wochentag abrufen.",
        "parameters": {
            "type": "object",
            "properties": {
                "day": {
                    "type": "string",
                    "description": "Wochentag, z. B. 'Samstag'.",
                }
            },
            "required": ["day"],
        },
    },
    {
        "type": "function",
        "name": "find_product",
        "description": "Gang, Preis und Lagerbestand eines Produkts nachschlagen.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Produktname, z. B. 'Milch'.",
                }
            },
            "required": ["product_name"],
        },
    },
]

INSTRUCTIONS = (
    "Du bist der Aldi Filial-Assistent, ein freundlicher Assistent für Mitarbeiter "
    "und Kunden einer Aldi-Filiale. Beantworte Fragen zu Öffnungszeiten, "
    "Produktstandorten (Gang), Preisen und Lagerbeständen. Nutze dafür die "
    "verfügbaren Tools und antworte kurz und höflich auf Deutsch. Wenn du etwas "
    "nicht weißt, sage es ehrlich."
)


def create_agent():
    agent = project.agents.create_version(
        agent_name=AGENT_NAME,
        definition=PromptAgentDefinition(
            model=MODEL_DEPLOYMENT_NAME,
            instructions=INSTRUCTIONS,
            tools=TOOLS,
        ),
    )
    print(f"Agent ready: {agent.name} (v{agent.version})")
    return agent


def ask(agent, question: str) -> str:
    resp = openai.responses.create(
        input=question,
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
    )
    # Execute any function calls the model requested, then send outputs back.
    outputs = []
    for item in resp.output:
        if item.type == "function_call" and item.name in TOOL_IMPLS:
            args = json.loads(item.arguments or "{}")
            result = TOOL_IMPLS[item.name](**args)
            outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": result,
                }
            )
    if outputs:
        resp = openai.responses.create(
            input=outputs,
            previous_response_id=resp.id,
            extra_body={
                "agent_reference": {"name": agent.name, "type": "agent_reference"}
            },
        )
    return resp.output_text


def main():
    agent = create_agent()

    if len(sys.argv) > 1:  # one-shot question from CLI
        print("\nQ:", " ".join(sys.argv[1:]))
        print("A:", ask(agent, " ".join(sys.argv[1:])))
        return

    demo = [
        "Wann habt ihr am Samstag geöffnet?",
        "In welchem Gang finde ich Kaffee und was kostet er?",
        "Habt ihr Bananen vorrätig?",
    ]
    for q in demo:
        print("\nQ:", q)
        print("A:", ask(agent, q))


if __name__ == "__main__":
    main()
