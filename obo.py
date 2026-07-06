# obo.py — Step 4: OBO exchange (Tc + secret -> TR) and call Graph /me as the user
import msal
import requests

from auth import AUTHORITY, CLIENT_ID, CLIENT_SECRET


def get_my_profile(user_token: str) -> str:
    """Middle-tier: Tc + secret -> Graph token (TR) -> call /me as the user."""
    cca = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
    )
    tr = cca.acquire_token_on_behalf_of(
        user_assertion=user_token,
        scopes=["User.Read"],
    )
    if "access_token" not in tr:
        raise RuntimeError(tr.get("error_description", "OBO exchange failed"))

    me = requests.get(
        "https://graph.microsoft.com/v1.0/me",
        headers={"Authorization": f"Bearer {tr['access_token']}"},
        timeout=30,
    ).json()
    return (
        f"{me.get('displayName')} — {me.get('jobTitle') or 'no title'} "
        f"in {me.get('department') or 'no department'} ({me.get('userPrincipalName')})"
    )


if __name__ == "__main__":
    from auth import get_user_token

    print(get_my_profile(get_user_token()))
