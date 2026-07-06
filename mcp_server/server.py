# mcp_server/server.py — Aldi Store Ops MCP server (streamable-HTTP) with OBO.
#
# OBO tools read the caller's user token from the Authorization header and run
# the on-behalf-of exchange to call Microsoft Graph AS THE SIGNED-IN EMPLOYEE.
# Generic tools (hours, products) use mock data and need no identity.
#
# Locally: our test client passes the token in the Authorization header.
# In Foundry: OAuth identity passthrough injects the user's token the same way.
import os
import sys
from pathlib import Path

import jwt
from mcp.server.fastmcp import Context, FastMCP

# Reuse the OBO helpers + app config from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auth import CLIENT_ID, TENANT  # noqa: E402
from obo import get_my_profile, graph_get  # noqa: E402

mcp = FastMCP("aldi-store-ops")

# Accepted audiences for the incoming user token (v1 uses api://<id>, v2 <id>).
_VALID_AUDIENCES = [CLIENT_ID, f"api://{CLIENT_ID}"]
_JWKS_URI = f"https://login.microsoftonline.com/{TENANT}/discovery/v2.0/keys"
_VERIFY_SIGNATURE = os.environ.get("MCP_VERIFY_SIGNATURE", "true").lower() == "true"
_jwks_client = jwt.PyJWKClient(_JWKS_URI)

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
STORE_ROSTER = {
    "amberr@m365cpi49218200.onmicrosoft.com": [
        "Mo 07:00–15:00 (Kasse)",
        "Mi 12:00–20:00 (Warenannahme)",
        "Sa 07:00–13:00 (Kasse)",
    ],
}


def _bearer_token(ctx: Context) -> str:
    """Extract and validate the caller's user token from the Authorization header.

    Validates that the token is intended for THIS API (audience == our app) so a
    public endpoint won't accept tokens minted for some other resource. This is
    the safety check the plan calls for on the public ingress.
    """
    request = ctx.request_context.request  # Starlette request (HTTP transport)
    auth = request.headers.get("authorization", "") if request else ""
    if not auth.lower().startswith("bearer "):
        raise ValueError("Missing bearer token — OAuth identity passthrough required.")
    token = auth.split(" ", 1)[1]

    try:
        if _VERIFY_SIGNATURE:
            signing_key = _jwks_client.get_signing_key_from_jwt(token).key
            jwt.decode(token, signing_key, algorithms=["RS256"], audience=_VALID_AUDIENCES)
        else:
            claims = jwt.decode(token, options={"verify_signature": False})
            if claims.get("aud") not in _VALID_AUDIENCES:
                raise ValueError("Token audience does not match this MCP server.")
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Invalid user token: {exc}") from exc

    return token


# ---- Generic tools ---------------------------------------------------------
@mcp.tool()
def get_store_hours(day: str) -> str:
    """Öffnungszeiten der Filiale für einen Wochentag."""
    d = (day or "").strip().lower()
    if d in STORE_HOURS:
        return f"Öffnungszeiten {day.capitalize()}: {STORE_HOURS[d]}"
    return "Mo–Fr 07:00–21:00, Sa 07:00–20:00, So geschlossen."


@mcp.tool()
def find_product(product_name: str) -> str:
    """Gang, Preis und Lagerbestand eines Produkts."""
    q = (product_name or "").strip().lower()
    for name, info in PRODUCTS.items():
        if q in name or name in q:
            return f"{name.capitalize()}: Gang {info['gang']}, {info['preis']}, Bestand {info['bestand']}."
    return f"'{product_name}' ist nicht gelistet."


# ---- OBO tools (act as the signed-in employee) -----------------------------
@mcp.tool()
def get_my_employee_info(ctx: Context) -> str:
    """Persönliche Infos des angemeldeten Mitarbeiters (via Graph /me, OBO)."""
    return get_my_profile(_bearer_token(ctx))


@mcp.tool()
def get_my_shifts(ctx: Context) -> str:
    """Dienstplan des angemeldeten Mitarbeiters. Identität via OBO (Graph /me)."""
    token = _bearer_token(ctx)
    me = graph_get(token, "/me", scopes=["User.Read"])
    upn = (me.get("userPrincipalName") or "").lower()
    shifts = STORE_ROSTER.get(upn)
    if not shifts:
        return f"Keine Schichten für {me.get('displayName') or upn} hinterlegt."
    return f"Schichten für {me.get('displayName')}:\n- " + "\n- ".join(shifts)


if __name__ == "__main__":
    # Bind on 0.0.0.0 and honor PORT for Azure Container Apps; serves /mcp.
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = int(os.environ.get("PORT", "8000"))
    mcp.run(transport="streamable-http")
