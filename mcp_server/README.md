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

## Next: deploy + register in Foundry

1. Containerize and deploy to Azure Container Apps (public ingress).
2. In Foundry, add an MCP tool pointing at the public URL, with **Custom OAuth**
   identity passthrough reusing the `obo-demo` Entra app.
3. Add Foundry's redirect URL to the app registration.
4. In the client, surface the one-time `oauth_consent_request.consent_link` and
   resubmit with `previous_response_id`.

See the [MCP authentication docs](https://learn.microsoft.com/azure/ai-foundry/agents/how-to/mcp-authentication).
