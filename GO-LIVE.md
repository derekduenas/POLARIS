# GO LIVE — exact steps

Three stages, in order. Stage 1 is the real "live" you can hit today: **the autonomous
agent floor running and reporting on your droplet.** Stages 2–3 add real market data and
then capped real capital, each gated on something specific. Don't skip ahead — each stage
earns the next.

---

## STAGE 1 — Agents live on the droplet (achievable today)

The floor runs, agents explore for real, the gauntlet + co-evolutionary Demiurge judge,
survivors forward-track, and every data/graduation request parks at your gate. No real
market data and no money needed for this stage.

**1. Put the package on the droplet — NOT via the web console.**
```bash
# from your machine:
scp -r ./polaris_floor you@YOUR_DROPLET_IP:~/polaris_floor
# (or: push polaris_floor + your NULLIUS to a private repo and `git clone` it on the box)
```

**2. Install and confirm it runs on the box.**
```bash
ssh you@YOUR_DROPLET_IP
cd ~/polaris_floor
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python floor.py --mode dry            # should print the board review + event gates
```

**3. Set a HARD spend cap, then turn the agents on.**
- In the Anthropic console, set a monthly usage limit on the API key you'll use. A
  self-prompting loop spends per proposal — cap the wall, don't trust the config.
```bash
export ANTHROPIC_API_KEY=sk-ant-...
python floor.py --mode live-agent --weeks 1 --iterations 6
```
This is the moment: real Claude proposing real edges across all three desks, each judged,
each desk filing the data feed it wants. Read `journal/desk_*.md` — that's your agents hunting.

**4. Make it self-prompting on a schedule (the bounded loop).**
```bash
crontab -e
# add — daily at 08:00, one bounded cycle, capped proposals, logged:
0 8 * * * cd ~/polaris_floor && . .venv/bin/activate && ANTHROPIC_API_KEY=sk-ant-... python floor.py --mode live-agent --weeks 1 --iterations 6 >> ~/polaris_floor/cron.log 2>&1
```
(If you want it to survive logout on a fresh box: `sudo loginctl enable-linger $USER`.)

**5. Wire OpenClaw to report to your Telegram (Atlas = the window, not the engine).**
In your POLARIS workspace skill, have Atlas on each run:
- read `~/polaris_floor/journal/desk_*.md` and `cron.log`,
- message you a summary: *"crypto killed 4, 1 survivor to forward-paper, adversarial
  ceiling 30%; 1 data request pending,"*
- and surface the **EVENT GATES** queue for your approval (data sources, graduations).
Keep the floor as its own process; Atlas only reads and relays. The firewall stays intact.

> ✅ After Stage 1 you have a live, scheduled, self-prompting agent floor that hunts edges,
> falsifies them, and reports to your phone — with every real-money/real-data decision
> waiting on you. Nothing can lose money. This is a real, defensible "live."

---

## STAGE 2 — Real market data (gated on YOUR data modules + your approval)

Now the verdicts become meaningful instead of illustrative. Two things gate this, both yours:

**A. Approve a data source.** In Stage 1 each desk filed a request (e.g. crypto: a perp
feed). You decide which to approve. To grant one, pass it in (or edit the registry):
```python
# in your run wrapper:
registry = DataRegistry(approved={"crypto": ["ccxt: Hyperliquid/OKX/Gate"]})
# only the desks whose feed you approve will run on real data; the rest stay in request.
```

**B. Wire YOUR verified data + strategy modules into the one fenced file.**
`live_engine.py` ships a *reference* ccxt fetcher + carry kernel. Replace the bodies of
`fetch_market_data()` and `carry_returns()` with your real `nullius/data/fetch` +
`nullius/strategy/carry`. **This is the one module to scrutinize** — a bug here silently
poisons every verdict (the Law: bad data manufactures false confidence). Then:
```bash
python live_engine.py                 # must fetch real data on the box, or STOP honestly
python floor.py --mode live --desks crypto   # real verdicts on the approved desk
```
Equities/options stay in the data gate until you approve (and likely pay for) a real feed.

> ✅ After Stage 2, survivors are forward-tracked on REAL data and accrue a real track
> record. Still no real money.

---

## STAGE 3 — Capped real capital (gated on forward evidence + you, per trade)

Only a strategy that climbed the ladder reaches here:
1. survived the gauntlet, on real data,
2. survived the co-evolutionary Demiurge (an adversarial ruin ceiling > 0),
3. accrued **weeks** of positive forward-paper evidence (belief crossed threshold),
4. → files a **GRADUATION** event at your gate.

When you approve a graduation, you open a **capped** live allocation, sized **at or below
the adversarial ruin ceiling**, **no leverage**, and **every trade Founder-confirmed**
(the floor places no orders itself — execution is a separate, human-confirmed path you
build deliberately). A kill-switch drawdown auto-halts and demotes.

> This stage is months out and that's correct. The system's job until then is to refuse to
> fool you and to build the only evidence that counts. "SURVIVED" never means "profitable."

---

## The locks that stay on, every stage
- **Bounded loop** (`--iterations`) — a self-prompting agent can't run away.
- **Hard API spend cap** at the billing level.
- **Paper-only** — no order code; real capital is a separate, human-confirmed path.
- **Data gate** — sources are agent-requested, Founder-approved (bad data poisons verdicts).
- **The firewall** — the gauntlet + Demiurge judge on data alone; performance funds
  capital, never the verdict.

*Nullius in verba.*
