# Presentation transcript — "Agent OAuth flows – Protocol Steps"

Plain-language script for presenting the six-step OBO (on-behalf-of) diagram.

## The one-line idea

> We want the agent to act **as the user** — so it only ever sees what that
> specific person is allowed to see. These six steps are how the agent safely
> "borrows" the user's identity to do that.

## The three tokens (keep these in mind)

Think of tokens as **badges**:

- **Tc** — the **user's badge**. Proves *who the person is*.
- **T1** — the **agent's badge**. Proves *the agent is who it says it is*.
- **TR** — the **access badge** for the actual data (Graph, files, etc.).
  This is the one that opens the door — and it carries the user's permissions.

## One quick thing before the steps

The agent can **never show a login screen itself.** It's a background service —
there's no browser, no person clicking "sign in." So the *human login* always
happens in the **client app** (the Teams app, our demo client, or Foundry). Once
the user has signed in there, the agent only does quiet, behind-the-scenes badge
swaps — it never asks the user to log in again.

## Walking the six steps

**① The user signs in.**
The person logs in through the client app and gets their **user badge, Tc**.
This is the only step where a human actually types a password.

**② The client hands the user badge to the agent.**
The client passes **Tc** to the agent and says, "act on this person's behalf."
Now the agent knows who the user is.

**③ The agent proves its own identity.**
The agent shows its **own credential** — a secret, a certificate, or a managed
identity — and gets back its **agent badge, T1**. So now we have two badges:
one for the user, one for the agent.

**④ The agent asks to trade up.**
The agent sends **both** badges together — its own (**T1**) and the user's
(**Tc**) — to Microsoft Entra ID, and asks: "Given these two, give me access to
the data." This trade is the actual "on-behalf-of" moment.

**⑤ Entra checks both and issues the access badge.**
Entra verifies both badges belong together, then hands back the **access badge,
TR**. The key safety check: both badges have to be issued *for this same agent* —
if they don't match up, the trade is refused. That's what stops someone from
reusing a badge meant for a different app.

**⑥ The agent opens the door — as the user.**
With **TR**, the agent finally calls the real resources (Graph, Skills, Tools)
**as the user**. So it sees exactly that person's data — their calendar, their
files, their shifts — and nothing else.

## Why this matters (the close)

Everything before the last step exists to make that final call happen with the
**real person's identity**, not a shared account. That gives us:

- **Privacy** — one user can never see another user's data.
- **Least privilege** — no all-powerful service account.
- **Clear audit trails** — logs show the actual person, not a generic bot.

## 20-second version

> We want the agent to act as the user. First the person signs in and gets a
> user badge. The client hands that badge to the agent. The agent adds its own
> badge, sends both to Entra, and Entra checks they belong together and issues
> an access badge. The agent uses that to open the user's data — seeing only what
> that person is allowed to see. Result: privacy, least privilege, and clean
> audit trails.

## Tying it to the demo

- **Flow A (function-calling agent):** our **client app** does the sign-in, then
  runs the badge-trade itself.
- **Flow B (MCP server):** **Foundry** handles the sign-in and consent, and the
  **deployed MCP server** runs the badge-trade. The user is prompted to consent
  once, then it just works.
- **Flow B, MAF variant (`filial_agent_mcp.py`):** same MCP server, but a
  **Microsoft Agent Framework** client does the sign-in (like Flow A) and passes
  the user badge to the server, which runs the badge-trade (like Flow B). Handy
  when you want the MCP server's OBO without hosting the agent in Foundry.
