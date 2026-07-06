# obo.py — Step 4: OBO exchange (Tc + secret -> TR) and call Graph as the user
import msal
import requests

from auth import AUTHORITY, CLIENT_ID, CLIENT_SECRET

GRAPH = "https://graph.microsoft.com/v1.0"


def obo_graph_token(user_token: str, scopes: list[str]) -> str:
    """Middle-tier: Tc + secret -> downstream Graph token (TR) for the user."""
    cca = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
    )
    tr = cca.acquire_token_on_behalf_of(user_assertion=user_token, scopes=scopes)
    if "access_token" not in tr:
        raise RuntimeError(tr.get("error_description", "OBO exchange failed"))
    return tr["access_token"]


def graph_get(user_token: str, path: str, scopes: list[str], params: dict | None = None):
    """Call a Graph endpoint on behalf of the user and return parsed JSON."""
    token = obo_graph_token(user_token, scopes)
    resp = requests.get(
        f"{GRAPH}{path}",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=30,
    )
    return resp.json()


def get_my_profile(user_token: str) -> str:
    me = graph_get(user_token, "/me", scopes=["User.Read"])
    return (
        f"{me.get('displayName')} — {me.get('jobTitle') or 'no title'} "
        f"in {me.get('department') or 'no department'} ({me.get('userPrincipalName')})"
    )


if __name__ == "__main__":
    from auth import get_user_token

    print(get_my_profile(get_user_token()))
