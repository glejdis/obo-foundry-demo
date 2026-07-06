# filial_agent_obo.py — Aldi Filial-Assistent with OBO (per-employee) tools.
#
# Generic store info (hours, products) uses mock data — NO identity.
# Personalized info (your profile, your shifts) uses the OBO flow — the tool
# calls Microsoft Graph AS THE SIGNED-IN EMPLOYEE.
import json
import os
import sys

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from auth import get_user_token
from obo import get_my_profile, graph_get

load_dotenv()

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
MODEL_DEPLOYMENT_NAME = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4.1-mini")
AGENT_NAME = "Aldi-Filial-Assistent-obo"

project = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=DefaultAzureCredential())
openai = project.get_openai_client()

# ---- Mock store data (generic, no identity) --------------------------------
STORE_HOURS = {
    "montag": "07:00–21:00", "dienstag": "07:00–21:00", "mittwoch": "07:00–21:00",
    "donnerstag": "07:00–21:00", "freitag": "07:00–21:00", "samstag": "07:00–20:00",
    "sonntag": "geschlossen",
}
PRODUCTS = {
    "milch": {"gang": "3 (Kühlregal)", "preis": "0,95 €", "bestand": 120},
    "brot": {"gang": "1 (Backwaren)", "preis": "1,29 €", "bestand": 45},
    "bananen": {"gang": "0 (Obst & Gemüse)", "preis": "1,49 €/kg", "bestand": 80},
    "kaffee": {"gang": "6 (Getränke)", "preis": "4,99 €", "bestand": 30},
}


def get_store_hours(day: str) -> str:
    d = (day or "").strip().lower()
    if d in STORE_HOURS:
        return f"Öffnungszeiten {day.capitalize()}: {STORE_HOURS[d]}"
    return "Mo–Fr 07:00–21:00, Sa 07:00–20:00, So geschlossen."


def find_product(product_name: str) -> str:
    q = (product_name or "").strip().lower()
    for name, info in PRODUCTS.items():
        if q in name or name in q:
            return f"{name.capitalize()}: Gang {info['gang']}, {info['preis']}, Bestand {info['bestand']}."
    return f"'{product_name}' ist nicht gelistet."


# ---- OBO tools (per-employee, act as the signed-in user) -------------------
# _USER_TOKEN holds this session's user token (Tc), injected at startup.
_USER_TOKEN: str | None = None

# Mock store roster, keyed by employee UPN. In reality this would be a call to
# your workforce/scheduling backend — but the KEY is the identity we obtain via
# OBO, so each employee only ever sees their own shifts.
STORE_ROSTER = {
    "amberr@m365cpi49218200.onmicrosoft.com": [
        "Mo 07:00–15:00 (Kasse)",
        "Mi 12:00–20:00 (Warenannahme)",
        "Sa 07:00–13:00 (Kasse)",
    ],
}


def get_my_employee_info() -> str:
    """OBO: read the signed-in employee's profile from Graph /me."""
    return get_my_profile(_USER_TOKEN)


def get_my_shifts() -> str:
    """OBO: identify the employee via Graph /me, then return THEIR roster.

    The identity comes from the OBO'd token (Graph /me), so the store backend
    lookup is scoped to the signed-in employee — nobody can read another's shifts.
    """
    me = graph_get(_USER_TOKEN, "/me", scopes=["User.Read"])
    upn = (me.get("userPrincipalName") or "").lower()
    shifts = STORE_ROSTER.get(upn)
    if not shifts:
        return f"Keine Schichten für {me.get('displayName') or upn} hinterlegt."
    return f"Schichten für {me.get('displayName')}:\n- " + "\n- ".join(shifts)


TOOL_IMPLS = {
    "get_store_hours": get_store_hours,
    "find_product": find_product,
    "get_my_employee_info": get_my_employee_info,
    "get_my_shifts": get_my_shifts,
}

TOOLS = [
    {
        "type": "function", "name": "get_store_hours",
        "description": "Öffnungszeiten der Filiale für einen Wochentag.",
        "parameters": {
            "type": "object",
            "properties": {"day": {"type": "string", "description": "Wochentag, z. B. 'Samstag'."}},
            "required": ["day"],
        },
    },
    {
        "type": "function", "name": "find_product",
        "description": "Gang, Preis und Lagerbestand eines Produkts.",
        "parameters": {
            "type": "object",
            "properties": {"product_name": {"type": "string", "description": "Produktname."}},
            "required": ["product_name"],
        },
    },
    {
        "type": "function", "name": "get_my_employee_info",
        "description": "Persönliche Infos des ANGEMELDETEN Mitarbeiters (Name, Abteilung/Team, Büro). Nutzt die Identität des Nutzers.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "type": "function", "name": "get_my_shifts",
        "description": "Schichten des ANGEMELDETEN Mitarbeiters. Nutzt die Identität des Nutzers (OBO), um dessen Dienstplan abzurufen.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
]

INSTRUCTIONS = (
    "Du bist der Aldi Filial-Assistent. Beantworte allgemeine Fragen zu "
    "Öffnungszeiten und Produkten mit den entsprechenden Tools. Für persönliche "
    "Fragen wie 'Wer bin ich?', 'meine Abteilung' oder 'meine Schichten' nutze "
    "die Tools get_my_employee_info bzw. get_my_shifts — diese greifen im Namen "
    "des angemeldeten Mitarbeiters auf dessen Daten zu. Antworte kurz auf Deutsch."
)


def create_agent():
    agent = project.agents.create_version(
        agent_name=AGENT_NAME,
        definition=PromptAgentDefinition(
            model=MODEL_DEPLOYMENT_NAME, instructions=INSTRUCTIONS, tools=TOOLS
        ),
    )
    print(f"Agent ready: {agent.name} (v{agent.version})")
    return agent


def ask(agent, question: str) -> str:
    resp = openai.responses.create(
        input=question,
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
    )
    outputs = []
    for item in resp.output:
        if item.type == "function_call" and item.name in TOOL_IMPLS:
            args = json.loads(item.arguments or "{}")
            result = TOOL_IMPLS[item.name](**args)  # OBO tools act as the user
            outputs.append(
                {"type": "function_call_output", "call_id": item.call_id, "output": result}
            )
    if outputs:
        resp = openai.responses.create(
            input=outputs,
            previous_response_id=resp.id,
            extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
        )
    return resp.output_text


def main():
    global _USER_TOKEN
    agent = create_agent()
    _USER_TOKEN = get_user_token()  # sign in once -> Tc (used by OBO tools)

    questions = sys.argv[1:] or [
        "Wann habt ihr am Samstag geöffnet?",   # mock tool, no identity
        "Wer bin ich und in welchem Team?",      # OBO -> Graph /me
        "Welche Schichten habe ich?",            # OBO identity -> my roster
    ]
    for q in questions:
        print("\nQ:", q)
        print("A:", ask(agent, q))


if __name__ == "__main__":
    main()
