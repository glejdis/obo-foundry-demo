# OBO Foundry Demo

Demonstrates the **On-Behalf-Of (OBO) / OAuth identity passthrough** flow with
Microsoft Foundry agents built on the **Microsoft Agent Framework (MAF)**, in two
flavours — the difference is **where the OBO exchange runs**:

- **Flow A** — OBO with no MCP: the agent's own client code does the exchange
  in-process (`filial_agent_obo.py`).
- **Flow B** — a custom **MCP server** on Azure Container Apps does the exchange;
  the MAF agent passes the user's token to it (`filial_agent_mcp.py`).

### Two OBO agents (where does OBO happen?)

Both are built with the Microsoft Agent Framework — MAF always runs the
tool-calling loop and each tool that touches user data runs the OBO exchange so
the call hits Microsoft Graph **as the signed-in employee**:

| Agent (file) | Custom MCP? | Where the OBO exchange runs |
|------|:---:|------|
| `filial_agent_obo.py` (Flow A) | ❌ | **in the MAF client** (in-process tool) |
| `filial_agent_mcp.py` (Flow B) | ✅ | **in the MCP server** (client passes the token) |

Both hit the same downstream (Graph `/me` + the employee's roster); they only
differ in *who* performs the token exchange.

Foundry project: `aldi-workshop`. Entra app: `obo-demo`
(`d03a0769-69cf-4601-afd6-2ba5f92aeadd`). Deployed MCP server:
`https://aldi-store-ops-mcp.blackbeach-39f4dfc4.swedencentral.azurecontainerapps.io/mcp`

## Architecture

Two OBO variants (source: [docs/obo-architecture.drawio](docs/obo-architecture.drawio)):

### Flow A — function-calling agent (`filial_agent_obo.py`)

The agent definition and model are hosted in Foundry; the function tools and the
OBO exchange run in the client (MAF) app, which holds the user token **Tc**.

![OBO Flow A — function-calling agent (OBO runs in the client app)](docs/obo-architecture-flow-a.png)

### Flow B — custom MCP agent (`filial_agent_mcp.py`)

The MAF client signs the user in and attaches the token to every request; the
deployed **MCP server** performs the OBO exchange as the signed-in employee.

![OBO Flow B — custom MCP agent (OBO runs in the MCP server)](docs/obo-architecture-flow-b.png)

## Setup

1. `cp .env.example .env` and fill in `TENANT`, `CLIENT_ID`, `CLIENT_SECRET`,
   `PROJECT_ENDPOINT`, `MODEL_DEPLOYMENT_NAME`.
2. `python -m pip install --only-binary=:all: -r requirements.txt`
   (force wheels; the machine builds native deps from source otherwise).
3. `az login` (the MAF agents use `DefaultAzureCredential` for the Foundry project).

## Files

| File | Role |
|------|------|
| `auth.py` | Device-code sign-in → user token (**Tc**) |
| `consent.py` | One-time Graph `User.Read` consent (no admin consent needed) |
| `obo.py` | OBO exchange (**Tc + secret → TR**) + Graph helpers |
| `filial_agent_obo.py` | **Flow A** — store assistant (MAF) + OBO tools, in-process exchange |
| `filial_agent_mcp.py` | **Flow B** — store assistant (MAF) that gets its tools from the **custom MCP** server |
| `mcp_server/` | The MCP server (OBO passthrough) + Dockerfile + deploy script |

## Flow A — run the in-process OBO agent

```
python filial_agent_obo.py "Welche Schichten habe ich?"
```
Signs you in (device code), then the OBO exchange runs in-process and calls Graph
as you. General questions (hours, products) use mock tools with no identity.

## Flow B — run the custom MCP agent

`filial_agent_mcp.py` is a MAF agent that connects to the MCP server via
`MCPStreamableHTTPTool`. The client signs the user in and attaches the token as an
`Authorization` header; the **MCP server** runs the OBO exchange.

Local (start the server in another terminal, then run the agent):
```
python mcp_server/server.py
python filial_agent_mcp.py "Welche Schichten habe ich?"
```

Deployed — build & push the server once, then point the agent at it:
```
./mcp_server/deploy.ps1        # az containerapp up, public HTTPS, secret for CLIENT_SECRET
# set MCP_SERVER_URL to the printed Container Apps /mcp URL, then:
python filial_agent_mcp.py "Welche Schichten habe ich?"
```
`MCP_SERVER_URL` defaults to `http://127.0.0.1:8000/mcp`.

## Notes
- The MCP server validates each caller's token audience (`obo-demo`) before any
  OBO exchange (`MCP_VERIFY_SIGNATURE=true`).
- Both flows reuse the same `obo-demo` Entra app and the OBO helpers in `obo.py`;
  only the location of the exchange differs (client vs. MCP server).

See the [MCP authentication docs](https://learn.microsoft.com/azure/ai-foundry/agents/how-to/mcp-authentication).
