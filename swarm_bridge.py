"""
swarm_bridge.py — THE LEAN SWARM'S NERVOUS SYSTEM
=================================================
Runs ONE Floor cycle (the cold engine) and writes its output into the shared
BLACKBOARD (swarm/) in a structured form the CSO agent and Atlas agent read.

The message bus is the FILESYSTEM. No Rust kernel, no parallel fan-out, no idle
agents burning tokens — deterministic and near-free. This is Ruflo's *shape*
(agents + shared memory + handoffs) sized to a small, sequential finance chain.

THE FLOW
  Atlas agent runs:   python swarm_bridge.py --mode live-agent
    -> the Floor hunts + falsifies (cold; only the Theorist costs API)
    -> this writes:  swarm/desks/desk_<asset>_report.md   (per-desk: killed + survivors)
                     swarm/gates/pending.md               (human-gated events)
                     swarm/STATUS.md                       (the signal board: who's up next)
    -> Atlas reads STATUS; if survivors exist, signals the CSO agent
  CSO agent (separate) reads swarm/desks/*, independently CHALLENGES each survivor,
    writes swarm/cso/picks.md, signals Atlas
  Atlas agent reads picks, convenes the board lens, reports to the Founder on Telegram,
    and relays any pending GATES for approval

THE LAW holds end to end: survived = "not yet disproven", never profitable. The CSO and
board may only KILL or pass — never bless. Real capital + new data are Founder gates.
"""
from __future__ import annotations

import argparse
import datetime
import os

from floor import (Atlas, Board, CapitalAllocator, DataRegistry, Demiurge, Desk,
                   Gauntlet, WorldEngine)

HERE = os.path.dirname(os.path.abspath(__file__))
SWARM = os.path.join(HERE, "swarm")


def _ts() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def export(desks, board, mode, swarm=SWARM) -> int:
    for sub in ("desks", "cso", "board", "gates"):
        os.makedirs(os.path.join(swarm, sub), exist_ok=True)
    synthetic = mode != "live"
    total_survivors = 0

    for d in desks:
        L = [f"# Desk report — {d.ac.upper()}",
             f"_generated {_ts()} by the Floor (deterministic; "
             f"{'SYNTHETIC judging data — verdicts illustrative' if synthetic else 'REAL data'})_", ""]
        if d.data_request:
            L += [f"## DATA REQUEST (Founder gate)",
                  f"- This desk wants: **{d.data_request[0]}**",
                  f"- {d.data_request[1]}", ""]
        L += [f"## Killed ({len(d.graveyard)}) — the graveyard"]
        L += [f"- {g['family']}" for g in d.graveyard] or ["- (none)"]
        L += ["", f"## Survivors — NOT YET DISPROVEN ({len(d.forward_book)})"]
        if not d.forward_book:
            L += ["- (none — every proposal killed. That is the system working.)"]
        for s in d.forward_book:
            total_survivors += 1
            L += [f"- **{s.family}**  | ruin-ceiling {s.ruin_ceiling:.0%} | belief {s.belief:.2f} "
                  f"| fwd-Sharpe {s.forward_sharpe:+.2f}",
                  f"    - rationale: {s.rationale[:220]}",
                  f"    - **CSO task:** challenge this. Is the edge STRUCTURAL and real, or curve-fit / "
                  f"a synthetic artifact? Does the ruin ceiling justify any capital? Survived ≠ profitable."]
        L += ["", "_Law: 'survived' means only 'not yet disproven'. Belief rises only on real forward evidence._"]
        with open(os.path.join(swarm, "desks", f"desk_{d.ac}_report.md"), "w") as f:
            f.write("\n".join(L) + "\n")

    # gates (human decisions)
    G = [f"# Pending Founder gates — {_ts()}", "", "These STOP the org until the Founder decides.", ""]
    G += [f"- [{e['status']}] **{e['kind']}** — {e['detail']}" for e in board.event_queue] or ["- (none)"]
    with open(os.path.join(swarm, "gates", "pending.md"), "w") as f:
        f.write("\n".join(G) + "\n")

    # the signal board — who is up next
    nxt = ("CSO REVIEW NEEDED → read swarm/desks/*, write swarm/cso/picks.md"
           if total_survivors else "no survivors this cycle → Atlas reports the graveyard to the Founder")
    S = [f"# SWARM STATUS — {_ts()}", "",
         f"- Floor ran (mode: {mode}). Survivors across all desks: **{total_survivors}**.",
         f"- Pending Founder gates: **{len(board.event_queue)}** (see swarm/gates/pending.md).",
         f"- NEXT: {nxt}.", "",
         f"_Verdicts are on {'SYNTHETIC data — illustrative until real feeds wired' if synthetic else 'REAL data'}. "
         f"Nothing here is profitable._"]
    with open(os.path.join(swarm, "STATUS.md"), "w") as f:
        f.write("\n".join(S) + "\n")
    return total_survivors


def main() -> None:
    ap = argparse.ArgumentParser(description="POLARIS lean swarm — run a Floor cycle and update the blackboard.")
    ap.add_argument("--mode", choices=["dry", "live-agent", "live"], default="live-agent")
    ap.add_argument("--weeks", type=int, default=1)
    ap.add_argument("--iterations", type=int, default=6, help="HARD cap on proposals/desk (bounded)")
    ap.add_argument("--desks", default="crypto,equities,options")
    args = ap.parse_args()

    registry, gauntlet, we, dm = DataRegistry(), Gauntlet(), WorldEngine(), Demiurge()
    acs = [a.strip() for a in args.desks.split(",") if a.strip()]
    mode = args.mode
    try:
        desks = [Desk(ac, mode, registry, gauntlet, we, dm) for ac in acs]
    except Exception as e:
        print(f"[swarm] live agent unavailable ({type(e).__name__}: {e}); set ANTHROPIC_API_KEY. Using --mode dry.")
        mode = "dry"
        desks = [Desk(ac, "dry", registry, gauntlet, we, dm) for ac in acs]

    board = Board()
    Atlas(desks, CapitalAllocator(), board).run_week(args.weeks, args.iterations)
    n = export(desks, board, mode)
    print(f"\n[swarm] blackboard updated → {SWARM}/")
    print(f"[swarm] {n} survivor(s) written for CSO review. Atlas: read swarm/STATUS.md for next step.")


if __name__ == "__main__":
    main()
