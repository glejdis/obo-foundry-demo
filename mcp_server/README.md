# Aldi Store Ops — MCP Server (Phase 2)

A remote **MCP server** (streamable-HTTP) exposing the Aldi Filial-Assistent
tools. The personalized tools use the **OBO / OAuth identity passthrough** flow:
the server reads the caller's user token from the `Authorization` header and
calls Microsoft Graph **as the signed-in employee**.

## Tools

| Tool | Type | Identity |
|------|------|----------|
| `get_store_hours(day)` | generic | none |
| `find_product(product_name)` | generic | none |
| `get_my_employee_info()` | **OBO** | Graph `/me` as the user |
| `get_my_shifts()` | **OBO** | identity via `/me`, then the user's roster |

## Run locally

Terminal 1 — start the server:
```
python mcp_server/server.py
```
Serves streamable-HTTP at `http://127.0.0.1:8000/mcp`.

Terminal 2 — test client (signs you in, passes the token as Foundry would):
```
python mcp_server/local_client.py
```

The client injects `Authorization: Bearer <user-token>` — the same mechanism
Foundry uses when OAuth identity passthrough is configured.

Terminal 2 (alternative) — a **Microsoft Agent Framework** agent that consumes
this server via `MCPStreamableHTTPTool` (from the repo root):
```
python filial_agent_mcp.py "Welche Schichten habe ich?"
```
It signs the user in and attaches the token as an `Authorization` header, so the
server runs the OBO exchange as that employee. Set `MCP_SERVER_URL` to target the
deployed server instead of the local default (`http://127.0.0.1:8000/mcp`).

## Deploy to Azure Container Apps

From the repo root:
```
./mcp_server/deploy.ps1
```
This builds the image in the cloud (ACR Tasks — no local Docker push), creates
the Container Apps environment, exposes public HTTPS on port 8000, and stores
`CLIENT_SECRET` as a Container Apps secret. It prints the public endpoint:
```
https://<app>.<region>.azurecontainerapps.io/mcp
```
Defaults: resource group `rg-Foundry`, region `swedencentral`, app
`aldi-store-ops-mcp`. Override via `-ResourceGroup` / `-Location` / `-AppName`.

The public endpoint validates that each caller's token audience matches the
`obo-demo` app (`MCP_VERIFY_SIGNATURE=true`) before running any OBO exchange.

## Next: register in Foundry

1. In Foundry, add an MCP tool pointing at the public URL, with **Custom OAuth**
   identity passthrough reusing the `obo-demo` Entra app.
2. Add Foundry's redirect URL to the app registration.
3. Use `foundry_mcp_client.py` to surface the one-time
   `oauth_consent_request.consent_link` and resubmit with `previous_response_id`.

See the [MCP authentication docs](https://learn.microsoft.com/azure/ai-foundry/agents/how-to/mcp-authentication).
