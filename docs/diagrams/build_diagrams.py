#!/usr/bin/env python
"""Render the OBO architecture diagrams (Flow A + Flow B) to PNG.

Source of truth for docs/obo-architecture-flow-a.png and
docs/obo-architecture-flow-b.png. Pure matplotlib — no browser / drawio needed.

    python docs/diagrams/build_diagrams.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib import patches  # noqa: E402
from matplotlib import pyplot as plt  # noqa: E402

W, H = 1500, 900  # screen-style canvas (y grows downward)

# ---- palette (matches the drawio pastel scheme) ---------------------------
BLUE_F, BLUE_S = "#dae8fc", "#6c8ebf"
GREEN_F, GREEN_S = "#d5e8d4", "#82b366"
PURPLE_F, PURPLE_S = "#e1d5e7", "#9673a6"
YELLOW_F, YELLOW_S = "#fff2cc", "#d6b656"
ORANGE_F, ORANGE_S = "#ffe6cc", "#d79b00"
GRAY_F, GRAY_S = "#f5f5f5", "#999999"
WHITE_F = "#ffffff"
TITLE_C = "#1f6feb"
SUB_C = "#555555"
INK = "#222222"

C_MAIN = "#333333"     # main flow arrows
C_DASH = "#8a8a8a"     # token-return (dashed)
C_T1 = "#3fa34d"       # get app token T1 (green)
C_OBO = "#e08e0b"      # OBO exchange + TR return (orange)


def _y(v: float) -> float:
    """Convert screen-y (top-down) to matplotlib-y (bottom-up)."""
    return H - v


def container(ax, x, y, w, h, title, fill=GRAY_F, stroke=GRAY_S, title_c=INK):
    """A swimlane-style box with a header strip + title."""
    ax.add_patch(
        patches.FancyBboxPatch(
            (x + 8, _y(y + h) + 8), w - 16, h - 16,
            boxstyle="round,pad=8,rounding_size=10",
            fc=fill, ec=stroke, lw=1.6, zorder=2,
        )
    )
    ax.plot([x + 10, x + w - 10], [_y(y + 40), _y(y + 40)], color=stroke, lw=1.2, zorder=3)
    ax.text(x + w / 2, _y(y + 22), title, ha="center", va="center",
            fontsize=13, fontweight="bold", color=title_c, zorder=4)


def box(ax, x, y, w, h, text, fill=WHITE_F, stroke=INK, tc=INK, fs=12, bold=False):
    ax.add_patch(
        patches.FancyBboxPatch(
            (x + 9, _y(y + h) + 9), w - 18, h - 18,
            boxstyle="round,pad=9,rounding_size=9",
            fc=fill, ec=stroke, lw=1.5, zorder=6,
        )
    )
    ax.text(x + w / 2, _y(y + h / 2), text, ha="center", va="center",
            fontsize=fs, fontweight="bold" if bold else "normal",
            color=tc, zorder=7, linespacing=1.35)


def chip(ax, cx, cy, text, tc=INK):
    """A small label pill sitting on an arrow."""
    ax.text(
        cx, _y(cy), text, ha="center", va="center", fontsize=10.5,
        fontweight="bold", color=tc, zorder=12,
        bbox=dict(boxstyle="round,pad=0.32", fc="white", ec="#c8c8c8", lw=1.0),
    )


def badge(ax, cx, cy, n):
    ax.add_patch(patches.Circle((cx, _y(cy)), 13, fc=TITLE_C, ec="white",
                                lw=1.5, zorder=13))
    ax.text(cx, _y(cy), str(n), ha="center", va="center", fontsize=11.5,
            fontweight="bold", color="white", zorder=14)


def arrow(ax, p1, p2, color=C_MAIN, dashed=False, rad=0.0, lw=2.0):
    ax.add_patch(
        patches.FancyArrowPatch(
            (p1[0], _y(p1[1])), (p2[0], _y(p2[1])),
            arrowstyle="-|>", mutation_scale=16, lw=lw, color=color,
            linestyle="--" if dashed else "-",
            connectionstyle=f"arc3,rad={rad}", zorder=5,
            shrinkA=2, shrinkB=2,
        )
    )


def base(ax, title, subtitle):
    ax.text(W / 2, _y(38), title, ha="center", va="center", fontsize=21,
            fontweight="bold", color=TITLE_C)
    ax.text(W / 2, _y(72), subtitle, ha="center", va="center", fontsize=12.5,
            color=SUB_C)


def legend(ax):
    items = [
        ("Tc = user token", GRAY_F, GRAY_S),
        ("TR = resource token (Graph)", ORANGE_F, ORANGE_S),
        ("green = hosted in Foundry", GREEN_F, GREEN_S),
    ]
    lx = 60
    for text, fc, ec in items:
        box(ax, lx, 848, 300, 44, text, fill=fc, stroke=ec, fs=11)
        lx += 330


# ---------------------------------------------------------------------------
def flow_a(ax):
    base(
        ax,
        "OBO Flow A — Function-calling agent",
        "filial_agent_obo.py \u00b7 the model runs in Foundry; the client app executes the tools "
        "and performs the OBO exchange in-process (it holds Tc)",
    )

    container(ax, 55, 140, 300, 185, "Client — local app (auth.py)")
    box(ax, 100, 210, 210, 95, "User\n(store employee)", BLUE_F, BLUE_S, bold=True)
    box(ax, 955, 138, 350, 90, "Microsoft Entra ID", BLUE_F, BLUE_S, fs=14, bold=True)

    container(ax, 55, 380, 340, 400, "MAF app (local) \u00b7 holds Tc", PURPLE_F, PURPLE_S)
    box(ax, 92, 445, 265, 82, "OBO handler\n(obo-demo client secret)", YELLOW_F, YELLOW_S)
    box(ax, 92, 545, 265, 68, "function tools\n(hours \u00b7 products \u00b7 shifts)", WHITE_F, PURPLE_S)
    box(ax, 92, 632, 265, 68, "agent identity\n(DefaultAzureCredential)", YELLOW_F, YELLOW_S)

    container(ax, 500, 615, 390, 190, "Microsoft Foundry — Agent Service",
              GREEN_F, GREEN_S)
    box(ax, 525, 663, 340, 52, "ChatAgent \u00b7 Aldi-Filial-Assistent-obo",
        WHITE_F, GREEN_S, bold=True, fs=11)
    box(ax, 525, 727, 340, 50, "model deployment \u00b7 gpt-4.1-mini", WHITE_F, GREEN_S, fs=11.5)

    container(ax, 1180, 380, 280, 245, "Resources")
    box(ax, 1210, 440, 220, 62, "Microsoft Graph\n/me", GREEN_F, GREEN_S)
    box(ax, 1210, 522, 220, 62, "store roster\n(keyed by UPN)", GREEN_F, GREEN_S)

    # sign-in + Tc return
    arrow(ax, (355, 235), (955, 188))
    chip(ax, 665, 196, "sign in (device code)")
    badge(ax, 500, 190, 1)
    arrow(ax, (955, 218), (355, 300), color=C_DASH, dashed=True, rad=-0.1)
    chip(ax, 665, 280, "Tc (user token)", tc=C_DASH)

    # model reasoning in Foundry
    arrow(ax, (395, 688), (500, 688))
    chip(ax, 448, 660, "message \u2192 run agent")
    badge(ax, 428, 688, 2)
    arrow(ax, (500, 722), (395, 722), color=C_DASH, dashed=True, rad=-0.0)
    chip(ax, 448, 748, "tool-call request", tc=C_DASH)

    # OBO exchange (client <-> Entra), across the open top-middle
    arrow(ax, (360, 458), (958, 226), color=C_T1, rad=0.10)
    chip(ax, 690, 322, "get app token T1", tc=C_T1)
    badge(ax, 560, 388, 3)
    arrow(ax, (360, 485), (988, 230), color=C_OBO, rad=0.16)
    chip(ax, 748, 378, "OBO: Tc + T1", tc=C_OBO)
    badge(ax, 602, 430, 4)
    arrow(ax, (1018, 230), (362, 502), color=C_OBO, dashed=True, rad=0.22)
    chip(ax, 812, 452, "TR (Graph token)", tc=C_OBO)
    badge(ax, 668, 468, 5)

    # call Graph as the user
    arrow(ax, (395, 470), (1180, 460))
    chip(ax, 792, 432, "call Graph as the user (TR)")
    badge(ax, 505, 452, 6)

    legend(ax)


def flow_b(ax):
    base(
        ax,
        "OBO Flow B — Custom MCP agent",
        "filial_agent_mcp.py \u00b7 the MAF client passes Tc to the deployed MCP server, "
        "which performs the OBO exchange as the employee",
    )

    container(ax, 55, 140, 290, 180, "Client — local app (auth.py)")
    box(ax, 95, 212, 205, 92, "User\n(store employee)", BLUE_F, BLUE_S, bold=True)
    box(ax, 1080, 140, 340, 88, "Microsoft Entra ID", BLUE_F, BLUE_S, fs=14, bold=True)

    container(ax, 470, 330, 360, 168, "Microsoft Foundry — Agent Service",
              GREEN_F, GREEN_S)
    box(ax, 495, 378, 310, 50, "ChatAgent \u00b7 Aldi-Filial-Assistent-mcp",
        WHITE_F, GREEN_S, bold=True, fs=11)
    box(ax, 495, 434, 310, 48, "model deployment \u00b7 gpt-4.1-mini", WHITE_F, GREEN_S, fs=11.5)

    container(ax, 55, 560, 320, 250, "MAF app (local) \u00b7 holds Tc", PURPLE_F, PURPLE_S)
    box(ax, 90, 620, 250, 148,
        "MCPStreamableHTTPTool\n\nattaches\nAuthorization: Bearer Tc",
        WHITE_F, PURPLE_S, fs=11.5)

    container(ax, 560, 560, 390, 240, "Aldi Store Ops MCP server", ORANGE_F, ORANGE_S)
    box(ax, 590, 618, 330, 72, "OBO handler\n(holds obo-demo client secret)",
        YELLOW_F, YELLOW_S)
    box(ax, 590, 702, 330, 58, "generic tools (hours \u00b7 products)\n+ OBO tools",
        WHITE_F, ORANGE_S, fs=11)

    container(ax, 1120, 560, 290, 250, "Resources")
    box(ax, 1150, 620, 230, 60, "Microsoft Graph\n/me", GREEN_F, GREEN_S)
    box(ax, 1150, 702, 230, 60, "store roster\n(keyed by UPN)", GREEN_F, GREEN_S)

    # sign-in + Tc return (clear across the top, above Foundry)
    arrow(ax, (345, 240), (1080, 188))
    chip(ax, 700, 200, "sign in (device code)")
    badge(ax, 505, 204, 1)
    arrow(ax, (1080, 214), (345, 300), color=C_DASH, dashed=True, rad=-0.08)
    chip(ax, 700, 272, "Tc (user token)", tc=C_DASH)

    # model reasoning in Foundry
    arrow(ax, (215, 560), (540, 498))
    chip(ax, 360, 520, "message \u2192 run agent")
    badge(ax, 318, 545, 2)
    arrow(ax, (585, 498), (300, 560), color=C_DASH, dashed=True, rad=-0.12)
    chip(ax, 470, 548, "tool-call request", tc=C_DASH)

    # token passthrough to the MCP server
    arrow(ax, (375, 655), (560, 655))
    chip(ax, 467, 698, "call tool +\nAuthorization: Bearer Tc")
    badge(ax, 467, 655, 3)

    # OBO exchange runs in the MCP server
    arrow(ax, (935, 600), (1185, 228), color=C_OBO, rad=-0.16)
    chip(ax, 1010, 432, "OBO: Tc + secret", tc=C_OBO)
    badge(ax, 1058, 505, 4)
    arrow(ax, (1205, 228), (945, 615), color=C_OBO, dashed=True, rad=-0.24)
    chip(ax, 1120, 332, "TR (Graph token)", tc=C_OBO)
    badge(ax, 1165, 432, 5)

    # call Graph as the user
    arrow(ax, (950, 645), (1120, 645))
    chip(ax, 1035, 688, "call Graph\nas the user (TR)")
    badge(ax, 1035, 645, 6)

    legend(ax)


def render(fn, out: Path):
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=150)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    fn(ax)
    fig.savefig(out, dpi=150, facecolor="white")
    plt.close(fig)
    print("wrote", out)


if __name__ == "__main__":
    docs = Path(__file__).resolve().parent.parent
    render(flow_a, docs / "obo-architecture-flow-a.png")
    render(flow_b, docs / "obo-architecture-flow-b.png")
