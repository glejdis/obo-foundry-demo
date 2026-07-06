# filial_agent.py — Aldi Filial-Assistent (store assistant) built with
# Microsoft Agent Framework (MAF). Generic tools use mock data, no identity.
import asyncio
import os
import sys

from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
MODEL_DEPLOYMENT_NAME = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4.1-mini")

# ---- Mock store data -------------------------------------------------------
STORE_HOURS = {
    "montag": "07:00–21:00", "dienstag": "07:00–21:00", "mittwoch": "07:00–21:00",
    "donnerstag": "07:00–21:00", "freitag": "07:00–21:00", "samstag": "07:00–20:00",
    "sonntag": "geschlossen",
}
PRODUCTS = {
    "milch": {"gang": "3 (Kühlregal)", "preis": "0,95 €", "bestand": 120},
    "brot": {"gang": "1 (Backwaren)", "preis": "1,29 €", "bestand": 45},
    "bananen": {"gang": "0 (Obst & Gemüse)", "preis": "1,49 €/kg", "bestand": 80},
    "schokolade": {"gang": "5 (Süßwaren)", "preis": "0,99 €", "bestand": 200},
    "eier": {"gang": "3 (Kühlregal)", "preis": "1,79 €", "bestand": 60},
    "kaffee": {"gang": "6 (Getränke)", "preis": "4,99 €", "bestand": 30},
}


# ---- Tools (MAF introspects type hints + docstrings) -----------------------
def get_store_hours(day: str) -> str:
    """Öffnungszeiten der Filiale für einen Wochentag abrufen."""
    d = (day or "").strip().lower()
    if d in STORE_HOURS:
        return f"Öffnungszeiten {day.capitalize()}: {STORE_HOURS[d]}"
    return "Mo–Fr 07:00–21:00, Sa 07:00–20:00, So geschlossen."


def find_product(product_name: str) -> str:
    """Gang, Preis und Lagerbestand eines Produkts nachschlagen."""
    q = (product_name or "").strip().lower()
    for name, info in PRODUCTS.items():
        if q in name or name in q:
            return f"{name.capitalize()}: Gang {info['gang']}, {info['preis']}, Bestand {info['bestand']} Stück."
    return f"'{product_name}' ist nicht im Sortiment gelistet."


INSTRUCTIONS = (
    "Du bist der Aldi Filial-Assistent, ein freundlicher Assistent für "
    "Mitarbeiter und Kunden einer Aldi-Filiale. Beantworte Fragen zu "
    "Öffnungszeiten, Produktstandorten (Gang), Preisen und Lagerbeständen mit "
    "den Tools. Antworte kurz und höflich auf Deutsch."
)


async def main() -> None:
    async with DefaultAzureCredential() as credential:
        client = AzureAIAgentClient(
            project_endpoint=PROJECT_ENDPOINT,
            model_deployment_name=MODEL_DEPLOYMENT_NAME,
            credential=credential,
        )
        try:
            agent = client.as_agent(
                name="Aldi-Filial-Assistent-demo",
                instructions=INSTRUCTIONS,
                tools=[get_store_hours, find_product],
            )
            questions = sys.argv[1:] or [
                "Wann habt ihr am Samstag geöffnet?",
                "In welchem Gang finde ich Kaffee und was kostet er?",
                "Habt ihr Bananen vorrätig?",
            ]
            for q in questions:
                resp = await agent.run(q)
                print("\nQ:", q)
                print("A:", resp.text)
        finally:
            await client.close()


if __name__ == "__main__":
    asyncio.run(main())
