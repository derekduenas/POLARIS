# NULLIUS × POLARIS — The Falsification Floor

A multi-desk autonomous research engine. **The agents explore edges; a deterministic,
incorruptible gauntlet judges them.** Three asset-class desks (crypto, equities,
options), each running propose → falsify → forward-track. POLARIS governs; NULLIUS
judges. Paper/research only — no orders, no keys held, real capital human-gated.

---

## What this is — and honestly, what it isn't

- **It runs today** and demonstrates the whole organism: desks proposing, the gauntlet
  killing, survivors taking ruin ceilings and entering forward-paper, the allocator
  funding by track record, the board steering, and money/data parking at the Founder gate.
- **The agents genuinely explore** in `--mode live-agent` / `live` (live Claude Theorist
  proposing creative, structured hypotheses).
- **It does NOT manufacture profit.** "SURVIVED" means *not yet disproven* — never
  "profitable". Belief rises only on real forward evidence accruing over time.
- **Real-market verdicts depend on `live_engine.py`**, which is a *reference* you must
  verify or replace with your own NULLIUS `data.fetch` + `strategy.carry`. A bug there
  silently poisons every verdict — it's the one module to scrutinize.

## Run modes

```bash
python floor.py --mode dry          # stub proposer + synthetic data — proves the machinery, zero cost
python floor.py --mode live-agent   # LIVE Claude proposer + synthetic judging — agents explore for REAL,
                                     #   verdicts illustrative. The most you can verifiably run today.
python floor.py --mode live          # LIVE proposer + REAL data via live_engine.py — verdicts meaningful,
                                     #   ONLY after you verify/replace live_engine.
# flags: --weeks N (forward cycles), --iterations N (HARD cap on proposals/desk/week), --desks crypto,equities,options
```

`live-agent` and `live` need `export ANTHROPIC_API_KEY=sk-ant-...`. Without it, each desk
falls back to the stub and tells you so (it never crashes).

---

## Deploy to the droplet

The DigitalOcean **web console works fine** for this — the thing to avoid is *hand-pasting
large files* into it (a browser terminal can truncate a long paste). `git clone` runs
perfectly in the console, so the repo path sidesteps that entirely. Two clean ways in:

**Option A — git (recommended; lets your real NULLIUS live beside the floor):**
```bash
# locally: put this folder + your full NULLIUS package in a private repo, then on the droplet
# (web console OR ssh — either works):
git clone <your-private-repo> polaris && cd polaris
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python floor.py --mode dry                       # confirm it runs on the box
export ANTHROPIC_API_KEY=sk-ant-...
python floor.py --mode live-agent --weeks 1      # watch the agents actually propose
```

**Option B — scp from your own machine (if you'd rather not use a repo):**
```bash
scp -r ./polaris_floor you@droplet:~/polaris_floor
ssh you@droplet 'cd polaris_floor && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && python floor.py --mode dry'
```

### Going to real crypto data (`--mode live`)
1. First, run the data self-check on the droplet (it must reach the exchanges):
   ```bash
   python live_engine.py        # prints a real fetch + a line to EYEBALL, or STOPS honestly
   ```
2. **Verify or replace** `live_engine.py`'s `fetch_market_data` + `carry_returns` with your
   verified NULLIUS modules. Do not trust verdicts until this is your real, checked engine.
3. Then: `python floor.py --mode live --desks crypto` (equities/options will hit the data
   gate and file a Founder-approval request for a real feed — that's the gate working).

---

## The OpenClaw layer (Atlas as interface, not engine)

Keep the engine and the agent **separate**. The floor runs as its own scheduled process;
OpenClaw/Atlas *reads its journal and talks to you*. Don't make the chat agent be the
trading engine — let it be the window into it.

1. **Schedule the floor** (bounded loop — it can never run away):
   ```bash
   # cron, e.g. daily at 08:00 — one forward cycle, capped proposals:
   0 8 * * * cd ~/polaris && . .venv/bin/activate && python floor.py --mode live-agent --weeks 1 --iterations 6 >> ~/polaris/cron.log 2>&1
   ```
   (Or a systemd timer; enable linger so it survives logout.)
2. **Point Atlas at the journal.** Add to the POLARIS workspace skill: each run, Atlas reads
   `journal/desk_*.md`, summarizes to you on Telegram — *"crypto killed 4, 1 survivor to
   forward-paper, 0 graduation gates pending"* — and **carries the EVENT-GATE queue to you
   for approval** (data-source requests, graduation-to-real-capital). Those stop and wait.
3. **The firewall stays intact end to end:** the gauntlet runs in the Python process,
   untouched by the agent; Atlas only reports and relays gates. Performance funds capital;
   it never touches the verdict.

### Safety locks (keep these on)
- **Bounded loop** via `--iterations` — a self-prompting agent can't run away.
- **Spend ceiling at the billing level** — set a hard cap on your Anthropic API key, not
  just in config. A live-agent loop spends per proposal; cap the wall.
- **Paper-only** — this code places no orders. Real capital is a separate, human-confirmed
  path that only opens after a strategy graduates the ladder.
- **Data gate** — new data sources are Founder-approved events (bad data poisons verdicts).

---

## Files
```
floor.py         the engine: desks, sacred gauntlet, world engine, allocator, two-channel board
theorist.py      StubTheorist (dry) + ClaudeTheorist (the live agent that explores)
live_engine.py   >>> SCRUTINIZE <<< reference ccxt fetcher + carry kernel; replace with your NULLIUS
requirements.txt numpy, anthropic, ccxt
journal/         auto-written per-desk logs = your forward track record AND content inventory
```

*Nullius in verba. The agents hunt with full freedom; the gauntlet rules without mercy;
real dollars are earned in forward light, never blessed in the dark.*
