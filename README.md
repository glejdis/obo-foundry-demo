# OBO Foundry Demo

A minimal demonstration of the **On-Behalf-Of (OBO) / OAuth identity passthrough**
flow with a Microsoft Foundry agent.

## Phase 1 — OBO with no MCP, no server (this repo)

An agent answers *"who am I?"* by calling Microsoft Graph `/me` **as the signed-in
user**, using a client-side function tool. Your own code performs the OBO token
exchange — nothing to host.

### Token flow

| Step | Token | Where |
|------|-------|-------|
| 1–2  | **Tc** — user token | `auth.py` (device-code sign-in) |
| 3–5  | **Tc + secret → TR** | `obo.py` (`acquire_token_on_behalf_of`) |
| 6    | **TR → Graph** | `obo.py` (`GET /me`) |

The agent (`agent.py`) orchestrates: it emits a `get_my_profile` function call,
your handler runs the OBO exchange, and the result is returned to the model.

## Setup

1. **Entra app registration** (`obo-demo`):
   - Authentication → Allow public client flows = **Yes**
   - Expose an API → Application ID URI `api://<client-id>` → scope `access_as_user`
     (Admins and users)
   - Certificates & secrets → new client secret (copy the **Value**)
   - API permissions → Microsoft Graph (Delegated): `User.Read`, `offline_access`,
     `openid`, `profile`
2. Copy `.env.example` → `.env` and fill in `TENANT`, `CLIENT_ID`, `CLIENT_SECRET`,
   and your Foundry `PROJECT_ENDPOINT` / `MODEL_DEPLOYMENT_NAME`.
3. Install deps:
   ```
   pip install -r requirements.txt
   ```

## Run

```
python auth.py     # Step 1: prove you can get the user token (Tc)
python obo.py      # Steps 1-6 without the agent: OBO + Graph /me
python agent.py    # Full loop: Foundry agent + OBO function tool
```

Sign in via the printed device-code URL and accept the one-time consent.

## Phase 2 — add a custom MCP server (next)

Move `get_my_profile` into a remote MCP server and let Foundry manage the OBO
exchange via **OAuth identity passthrough** (custom OAuth). See the
[MCP authentication docs](https://learn.microsoft.com/azure/ai-foundry/agents/how-to/mcp-authentication).
