# auth.py — Step 3: get the user token (Tc)
import os

import msal
from dotenv import load_dotenv

load_dotenv()

TENANT = os.environ["TENANT"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
AUTHORITY = f"https://login.microsoftonline.com/{TENANT}"


def get_user_token() -> str:
    """Simulates the client app signing the user in -> Tc."""
    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
    flow = app.initiate_device_flow(scopes=[f"api://{CLIENT_ID}/access_as_user"])
    if "user_code" not in flow:
        raise RuntimeError(f"Failed to start device flow: {flow}")
    print(flow["message"])  # user opens the URL + enters the code
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        raise RuntimeError(result.get("error_description", "Failed to get user token"))
    return result["access_token"]


if __name__ == "__main__":
    token = get_user_token()
    print("\nGot user token (Tc):", token[:40], "...")
