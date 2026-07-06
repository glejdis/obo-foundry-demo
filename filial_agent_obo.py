# filial_agent_obo.py — Aldi Filial-Assistent with OBO (per-employee) tools,
# built with Microsoft Agent Framework (MAF).
#
# Generic tools (hours, products) use mock data — NO identity.
# Personalized tools (my info, my shifts) use the OBO flow — they call Microsoft
# Graph AS THE SIGNED-IN EMPLOYEE, so each employee sees only their own data.
import asyncio
import os
import sys

from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

from auth import get_user_token
from obo import get_my_profile as _get_my_profile
from obo import graph_get

load_dotenv()

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
MODEL_DEPLOYMENT_NAME = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4.1-mini")

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
# Keyed by employee UPN — the identity is established via OBO (Graph /me).
STORE_ROSTER = {
    "amberr@m365cpi49218200.onmicrosoft.com": [
        "Mo 07:00–15:00 (Kasse)",
        "Mi 12:00–20:00 (Warenannahme)",
        "Sa 07:00–13:00 (Kasse)",
    ],
}

# Set after device-code sign-in; read by the OBO tools below.
_USER_TOKEN: str | None = None


# ---- Generic tools ---------------------------------------------------------
def get_store_hours(day: str) -> str:
    """Öffnungszeiten der Filiale für einen Wochentag."""
    d = (day or "").strip().lower()
    if d in STORE_HOURS:
        return f"Öffnungszeiten {day.capitalize()}: {STORE_HOURS[d]}"
    return "Mo–Fr 07:00–21:00, Sa 07:00–20:00, So geschlossen."


def find_product(product_name: str) -> str:
    """Gang, Preis und Lagerbestand eines Produkts."""
    q = (product_name or "").strip().lower()
    for name, info in PRODUCTS.items():
        if q in name or name in q:
            return f"{name.capitalize()}: Gang {info['gang']}, {info['preis']}, Bestand {info['bestand']}."
    return f"'{product_name}' ist nicht gelistet."


# ---- OBO tools (act as the signed-in employee) -----------------------------
def get_my_employee_info() -> str:
    """Persönliche Infos des angemeldeten Mitarbeiters (Name, Team) via Graph /me."""
    return _get_my_profile(_USER_TOKEN)


def get_my_shifts() -> str:
    """Dienstplan des angemeldeten Mitarbeiters. Identität via OBO (Graph /me)."""
    me = graph_get(_USER_TOKEN, "/me", scopes=["User.Read"])
    upn = (me.get("userPrincipalName") or "").lower()
    shifts = STORE_ROSTER.get(upn)
    if not shifts:
        return f"Keine Schichten für {me.get('displayName') or upn} hinterlegt."
    return f"Schichten für {me.get('displayName')}:\n- " + "\n- ".join(shifts)


INSTRUCTIONS = (
    "Du bist der Aldi Filial-Assistent. Beantworte allgemeine Fragen zu "
    "Öffnungszeiten und Produkten mit den entsprechenden Tools. Für persönliche "
    "Fragen wie 'Wer bin ich?', 'meine Abteilung' oder 'meine Schichten' nutze "
    "get_my_employee_info bzw. get_my_shifts — diese greifen im Namen des "
    "angemeldeten Mitarbeiters auf dessen Daten zu. Antworte kurz auf Deutsch."
)


async def main() -> None:
    global _USER_TOKEN
    _USER_TOKEN = get_user_token()  # Tc — sign in once (used by OBO tools)

    async with DefaultAzureCredential() as credential:
        client = AzureAIAgentClient(
            project_endpoint=PROJECT_ENDPOINT,
            model_deployment_name=MODEL_DEPLOYMENT_NAME,
            credential=credential,
        )
        try:
            agent = client.as_agent(
                name="Aldi-Filial-Assistent-obo",
                instructions=INSTRUCTIONS,
                tools=[get_store_hours, find_product, get_my_employee_info, get_my_shifts],
            )
            questions = sys.argv[1:] or [
                "Wann habt ihr am Samstag geöffnet?",   # mock tool, no identity
                "Wer bin ich und in welchem Team?",      # OBO -> Graph /me
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
