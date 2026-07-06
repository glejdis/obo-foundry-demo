# consent.py — one-time: make the signed-in user consent to Graph User.Read
# for the obo-demo app. Required because admin consent isn't available.
# After running this once (and accepting), the OBO exchange in obo.py works.
import msal

from auth import AUTHORITY, CLIENT_ID


def grant_graph_consent() -> None:
    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
    flow = app.initiate_device_flow(scopes=["User.Read"])
    if "user_code" not in flow:
        raise RuntimeError(f"Failed to start device flow: {flow}")
    print(flow["message"])
    print("\n>>> On the sign-in page, ACCEPT the consent prompt for 'obo-demo'.\n")
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        raise RuntimeError(result.get("error_description", "Consent failed"))
    print("Consent granted — Graph User.Read is now consented for your user.")
    print("You can now run:  python obo.py")


if __name__ == "__main__":
    grant_graph_consent()
