# POLARIS Lean Swarm — The Blackboard Protocol

The swarm coordinates through **files in `swarm/`** — the shared blackboard. No heavy
framework; the filesystem is the message bus. Agents wake at handoffs, do one focused
pass, write their output, and signal the next. Deterministic, debuggable (`cat` any
message), near-free.

## The roles
- **The Floor** (`floor.py`, run via `swarm_bridge.py`) — the cold engine. Hunts +
  falsifies + forward-tracks. Writes the desk reports. Not an agent; never blesses.
- **Atlas** (OpenClaw agent — the one you talk to) — CEO. Runs the swarm cycle, plays
  the board lens, reports to the Founder on Telegram, relays gates. Reads the whole board.
- **The CSO** (OpenClaw agent — separate, for genuine independence) — Chief Strategy
  Officer. Independently challenges the survivors, decides which are worth pitching up.
- **The Founder** (you) — approves data sources and capital. The only one who can.

## The blackboard (`swarm/`)
```
swarm/
  STATUS.md              the signal board — what just happened, who is up next
  desks/desk_*_report.md per-desk: killed + survivors + a CSO task on each survivor   (Floor writes)
  cso/picks.md           the CSO's vetted picks + its challenges                       (CSO writes)
  board/decisions.md     the board's verdict per pick                                   (Atlas writes)
  gates/pending.md       human-gated events: data requests + graduations               (Floor/Atlas write)
```

## The handoff sequence (one cycle)
1. **Atlas** runs `python swarm_bridge.py --mode live-agent`. The Floor hunts + falsifies;
   the bridge writes `desks/*`, `gates/pending.md`, and `STATUS.md`.
2. **Atlas** reads `STATUS.md`. If survivors > 0 → signal the **CSO** ("review needed").
   If 0 → Atlas reports the graveyard to the Founder; cycle ends (most cycles end here —
   that is the system working).
3. **CSO** reads every `desks/desk_*_report.md`. For each survivor it CHALLENGES: is the
   edge structural or curve-fit? does the ruin ceiling justify capital? It writes its
   verdict — **PASS UP** or **KILL** with reasoning — to `cso/picks.md`. The CSO may only
   kill or pass; it can never bless. Then it signals **Atlas**.
4. **Atlas** reads `cso/picks.md`, applies the board lens (governance / risk / capital),
   writes `board/decisions.md`, and **reports to the Founder on Telegram**: what was
   killed, what the CSO passed up, the board's read, and any **pending gates**.
5. **Founder** approves/denies gates in Telegram → Atlas records the decision in `gates/`.

## The Laws (every agent, always)
- A simulation may only KILL a belief, never BLESS one. "SURVIVED"/"PASS UP" = *not yet
  disproven*, never "profitable" or "will make money".
- Paper/research only. No agent places a trade, moves money, or holds a key.
- The firewall: the Floor's gauntlet + Demiurge judge on data alone. The CSO and board add
  *human-style scrutiny on top* — they can kill a survivor, never overturn a kill, never
  pressure the engine, never bless. Performance funds capital; it never funds the verdict.
- Human-gated events (new data source, graduation to real capital) STOP and wait for the
  Founder. Agents surface them; agents never approve them.

## Cost discipline (why this is lean)
- The Floor runs cold — only the Theorist's proposals cost API.
- The CSO wakes for ONE pass per cycle, only when there are survivors. No idle loop.
- Atlas wakes to run the cycle and report. No idle loop.
- Two live agents, event-triggered, a folder of files. That is the whole swarm.

*Nullius in verba.*
