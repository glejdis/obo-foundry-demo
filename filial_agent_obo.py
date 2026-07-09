# filial_agent_obo.py — Aldi Filial-Assistent with OBO (per-employee) tools,
# built with Microsoft Agent Framework (MAF).
#
# Generic tools (hours, products) use mock data — NO identity.
# Personalized tools (my info, my shifts) use the OBO flow — they call Microsoft
# Graph AS THE SIGNED-IN EMPLOYEE, so each employee sees only their own data.
#
# On top of OBO, each employee is mapped to a persona/role (USER_PERSONAS) whose
# permissions (PERSONA_PERMISSIONS) gate every tool: a tool only runs if the
# signed-in persona holds its required permission (e.g. only a Filialleiter may
# call get_team_shifts).
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
    "admin@m365cpi49218200.onmicrosoft.com": [
        "Di 09:00–17:00 (Kasse)",
        "Do 10:00–18:00 (Kasse)",
        "Fr 08:00–14:00 (Pfandannahme)",
    ],
}

# ---- Personas & permission mapping -----------------------------------------
# Map each employee (UPN) to a persona/role. Unknown users fall back to the
# DEFAULT_PERSONA. The persona is resolved once at sign-in (via Graph /me).
USER_PERSONAS = {
    "amberr@m365cpi49218200.onmicrosoft.com": "filialleiter",
    "admin@m365cpi49218200.onmicrosoft.com": "kassierer",
}
DEFAULT_PERSONA = "kassierer"

# Each persona grants a set of permissions; every tool checks its required
# permission before running, so a persona only sees what it's allowed to.
PERSONA_PERMISSIONS = {
    "kassierer":    {"store_hours", "product_lookup", "my_info", "my_shifts"},
    "lagerist":     {"store_hours", "product_lookup", "my_info", "my_shifts"},
    "filialleiter": {"store_hours", "product_lookup", "my_info", "my_shifts", "team_shifts"},
}

# Set after device-code sign-in; read by the tools below.
_USER_TOKEN: str | None = None
_USER_UPN: str | None = None
_PERSONA: str | None = None


# ---- Permission gate -------------------------------------------------------
def _denied(permission: str) -> str | None:
    """Return a refusal message if the signed-in persona lacks the permission."""
    if permission not in PERSONA_PERMISSIONS.get(_PERSONA, set()):
        return (
            f"Zugriff verweigert: Deine Rolle '{_PERSONA}' hat keine "
            f"Berechtigung für '{permission}'."
        )
    return None


# ---- Generic tools ---------------------------------------------------------
def get_store_hours(day: str) -> str:
    """Öffnungszeiten der Filiale für einen Wochentag."""
    if msg := _denied("store_hours"):
        return msg
    d = (day or "").strip().lower()
    if d in STORE_HOURS:
        return f"Öffnungszeiten {day.capitalize()}: {STORE_HOURS[d]}"
    return "Mo–Fr 07:00–21:00, Sa 07:00–20:00, So geschlossen."


def find_product(product_name: str) -> str:
    """Gang, Preis und Lagerbestand eines Produkts."""
    if msg := _denied("product_lookup"):
        return msg
    q = (product_name or "").strip().lower()
    for name, info in PRODUCTS.items():
        if q in name or name in q:
            return f"{name.capitalize()}: Gang {info['gang']}, {info['preis']}, Bestand {info['bestand']}."
    return f"'{product_name}' ist nicht gelistet."


# ---- OBO tools (act as the signed-in employee) -----------------------------
def get_my_employee_info() -> str:
    """Persönliche Infos des angemeldeten Mitarbeiters (Name, Team) via Graph /me."""
    if msg := _denied("my_info"):
        return msg
    return _get_my_profile(_USER_TOKEN)


def get_my_shifts() -> str:
    """Dienstplan des angemeldeten Mitarbeiters. Identität via OBO (Graph /me)."""
    if msg := _denied("my_shifts"):
        return msg
    me = graph_get(_USER_TOKEN, "/me", scopes=["User.Read"])
    upn = (me.get("userPrincipalName") or "").lower()
    shifts = STORE_ROSTER.get(upn)
    if not shifts:
        return f"Keine Schichten für {me.get('displayName') or upn} hinterlegt."
    return f"Schichten für {me.get('displayName')}:\n- " + "\n- ".join(shifts)


def get_team_shifts() -> str:
    """Dienstplan des gesamten Teams — nur für Filialleiter (Berechtigung team_shifts)."""
    if msg := _denied("team_shifts"):
        return msg
    if not STORE_ROSTER:
        return "Kein Team-Dienstplan hinterlegt."
    blocks = [
        f"{upn}:\n  - " + "\n  - ".join(shifts)
        for upn, shifts in STORE_ROSTER.items()
    ]
    return "Team-Dienstplan:\n" + "\n".join(blocks)


INSTRUCTIONS = (
    "Du bist der Aldi Filial-Assistent. Beantworte allgemeine Fragen zu "
    "Öffnungszeiten und Produkten mit den entsprechenden Tools. Für persönliche "
    "Fragen wie 'Wer bin ich?', 'meine Abteilung' oder 'meine Schichten' nutze "
    "get_my_employee_info bzw. get_my_shifts — diese greifen im Namen des "
    "angemeldeten Mitarbeiters auf dessen Daten zu. Für 'Dienstplan des Teams' "
    "(nur Filialleiter) nutze get_team_shifts. Manche Tools sind rollenabhängig; "
    "wenn ein Tool 'Zugriff verweigert' meldet, gib diese Meldung unverändert "
    "weiter. Antworte kurz auf Deutsch."
)


async def main() -> None:
    global _USER_TOKEN, _USER_UPN, _PERSONA
    _USER_TOKEN = get_user_token()  # Tc — sign in once (used by OBO tools)

    # Resolve the signed-in employee's identity (OBO -> Graph /me) once, then map
    # them to a persona whose permissions gate every tool below.
    _me = graph_get(_USER_TOKEN, "/me", scopes=["User.Read"])
    _USER_UPN = (_me.get("userPrincipalName") or "").lower()
    _PERSONA = USER_PERSONAS.get(_USER_UPN, DEFAULT_PERSONA)
    print(
        f"Angemeldet als {_USER_UPN or 'unbekannt'} — Rolle: {_PERSONA} "
        f"(Berechtigungen: {', '.join(sorted(PERSONA_PERMISSIONS.get(_PERSONA, set())))})"
    )

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
                tools=[get_store_hours, find_product, get_my_employee_info, get_my_shifts, get_team_shifts],
            )
            questions = sys.argv[1:] or [
                "Wann habt ihr am Samstag geöffnet?",   # generic tool (persona: store_hours)
                "Wer bin ich und in welchem Team?",      # OBO -> Graph /me (persona: my_info)
                "Welche Schichten habe ich?",            # OBO identity -> my roster (my_shifts)
                "Zeig mir den Dienstplan des Teams.",    # manager-only (persona: team_shifts)
            ]
            for q in questions:
                resp = await agent.run(q)
                print("\nQ:", q)
                print("A:", resp.text)
        finally:
            await client.close()


if __name__ == "__main__":
    asyncio.run(main())
