"""
NULLIUS x POLARIS — THE MULTI-DESK FALSIFICATION FLOOR  (deployable)
====================================================================
Three desks (asset classes). Each runs propose -> falsify -> forward-track.
POLARIS governs; NULLIUS judges. THE AGENTS EXPLORE; the gauntlet rules.

RUN MODES (python floor.py --mode ...):
  dry         : stub proposer + SYNTHETIC data. Proves the machinery, zero cost.
  live-agent  : LIVE Claude proposer (agents genuinely explore) + SYNTHETIC judging
                data. Verdicts are ILLUSTRATIVE (synthetic), exploration is REAL.
                >>> This is the most you can verifiably run TODAY. <<<
  live        : LIVE Claude proposer + REAL market data via live_engine.py.
                Verdicts are MEANINGFUL — but only as good as live_engine, which you
                must verify/replace with your NULLIUS data+strategy modules first.

THE LAWS (enforced in code): (1) a sim may only KILL, never BLESS; "SURVIVED" = "not
yet disproven". Belief rises ONLY on real forward evidence. (2) THE FIREWALL:
performance funds CAPITAL, never the VERDICT — the gauntlet sees only (hypothesis,
data). (3) Paper-only; real capital + new data sources are human-gated events.
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np

from theorist import StubTheorist, ClaudeTheorist, DESK_FAMILIES

SEED = 11
RNG = np.random.default_rng(SEED)
TD = 252
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "journal")
os.makedirs(OUT, exist_ok=True)


# ============================ SYNTHETIC DATA STAND-IN ============================
def _garch_t(n, mu=0.0, omega=3e-6, alpha=0.09, beta=0.90, nu=5.0, rng=RNG):
    scale = np.sqrt(nu / (nu - 2.0))
    z = rng.standard_t(nu, size=n) / scale
    eps = np.empty(n); s2 = np.empty(n)
    s2[0] = omega / (1 - alpha - beta); eps[0] = np.sqrt(s2[0]) * z[0]
    for t in range(1, n):
        s2[t] = omega + alpha * eps[t - 1] ** 2 + beta * s2[t - 1]
        eps[t] = np.sqrt(s2[t]) * z[t]
    return mu + eps


def synth_returns(profile, n=1500, rng=RNG):
    base = _garch_t(n, rng=rng); vol = base.std()
    if profile == "noise":      return base
    if profile == "regime":     return base + np.concatenate([np.full(n//2, 0.9*vol), np.zeros(n-n//2)])
    if profile == "structural": return base + 0.35*vol
    raise ValueError(profile)


# a desk's family -> synthetic profile (dry/live-agent only). Unknown agent-proposed
# families default to a noise-weighted draw so the demo graveyard looks realistic.
_PROFILE = {"funding_carry":"regime","xvenue_spread":"structural","overnight_drift":"structural",
            "vol_risk_premium":"structural"}
def _synth_for(family, rng):
    if family in _PROFILE: return _PROFILE[family]
    return rng.choice(["noise","noise","noise","structural"])   # mostly dies, as it should


# ============================ THE SACRED GATE (referee) ============================
def _sharpe(r):
    r = np.asarray(r, float)
    return 0.0 if r.std()==0 else float(r.mean()/r.std()*np.sqrt(TD))

def _norm_cdf(x):
    import math; return 0.5*(1+math.erf(x/np.sqrt(2)))


class Verdict:
    def __init__(self, killed, kills, is_s, oos_s, wf_s, p):
        self.killed, self.kills = killed, kills
        self.is_sharpe, self.oos_sharpe, self.wf_sharpe, self.selection_p = is_s, oos_s, wf_s, p
    @property
    def survived(self): return not self.killed


class Gauntlet:
    """The Inquisitor. adjudicate() takes ONLY (returns). No performance/capital/
    incentive parameter exists — the firewall is the signature itself."""
    def __init__(self, cost=5e-5, trials=24): self.cost, self.trials = cost, trials
    def adjudicate(self, returns) -> Verdict:
        r = np.asarray(returns, float); kills = []
        cut = int(0.7*len(r)); is_s, oos_s = _sharpe(r[:cut]), _sharpe(r[cut:])
        if oos_s < max(0.0, 0.4*is_s): kills.append("holdout")
        seg = len(r)//6
        wf_s = _sharpe(np.concatenate([r[(i+1)*seg:(i+2)*seg] for i in range(5)]))
        if wf_s <= 0.15: kills.append("walk_forward")
        if _sharpe(r - 2*self.cost) <= 0.0: kills.append("cost_stress")
        t = abs(r.mean())/(r.std()/np.sqrt(len(r))+1e-18)
        p_sel = 1-(1-float(2*(1-_norm_cdf(t))))**self.trials
        if p_sel > 0.05: kills.append("selection")
        return Verdict(bool(kills), tuple(kills), is_s, oos_s, wf_s, p_sel)


# ============================ THE WORLD ENGINE (Nemesis) ============================
def _stylized_facts(rets):
    """The Gate's measurement (NULLIUS world-engine, verbatim): fat tails (excess
    kurtosis) + volatility clustering (autocorrelation of squared returns)."""
    flat = rets.reshape(-1)
    z = (flat - flat.mean()) / (flat.std() + 1e-18)
    excess_kurt = float(np.mean(z ** 4) - 3.0)
    r2 = rets ** 2
    a, b = r2[:, 1:], r2[:, :-1]
    am, bm = a.mean(1, keepdims=True), b.mean(1, keepdims=True)
    acf1 = float(np.mean(((a - am) * (b - bm)).mean(1) / (a.std(1) * b.std(1) + 1e-18)))
    return excess_kurt, acf1


class WorldEngine:
    def __init__(self, n=4000, h=180, cp=0.006, cm=1.5, block=24):
        self.n, self.h, self.cp, self.cm, self.block = n, h, cp, cm, block

    def stress(self, returns):
        r = np.asarray(returns, float); r = r[np.isfinite(r)]
        rng = np.random.default_rng(SEED + 7)
        # BLOCK bootstrap: sample contiguous blocks so volatility clustering SURVIVES.
        # (An IID resample would destroy clustering and the Gate would rightly reject it.)
        b = min(self.block, max(2, len(r) // 4))
        n_blocks = self.h // b + 1
        starts = rng.integers(0, max(1, len(r) - b), size=(self.n, n_blocks))
        idx = (starts[:, :, None] + np.arange(b)[None, None, :]).reshape(self.n, -1)[:, :self.h]
        w = r[idx]
        w[rng.random((self.n, self.h)) < self.cp] = self.cm * r.min()   # worse-than-history crashes

        # THE GATE: the forger only gets a vote if its worlds reproduce real texture.
        ek, ac = _stylized_facts(w)
        gate_passed = ek > 1.0 and ac > 0.02
        if not gate_passed:
            # the Law: a bad generator's verdicts are thrown out. No ruin ceiling granted;
            # fall back to the most conservative sizing and flag it.
            return {"gate_passed": False, "ek": ek, "ac": ac, "ruin_ceiling": 0.05,
                    "shape": {"skew": 0.0, "right_over_left": 0.0}}

        ceiling = 0.0
        for f in (0.05, 0.10, 0.20, 0.30, 0.50):
            eq = np.cumprod(1.0 + f * w, axis=1)
            dd = (eq / np.maximum.accumulate(eq, axis=1) - 1.0).min(axis=1)
            if float((dd < -0.50).mean()) <= 0.05: ceiling = f
        eq = np.cumprod(1.0 + 0.20 * w, axis=1); term = eq[:, -1] - 1.0
        shape = {"skew": float(((term - term.mean()) ** 3).mean() / (term.std() ** 3 + 1e-18)),
                 "right_over_left": float(abs(np.percentile(term, 95)) / (abs(np.percentile(term, 5)) + 1e-12))}
        return {"gate_passed": True, "ek": ek, "ac": ac, "ruin_ceiling": ceiling, "shape": shape}


# ============================ THE CO-EVOLUTIONARY DEMIURGE ============================
class Demiurge:
    """The learning adversary (the World Engine doc's co-evolutionary Demiurge — built).
    Instead of forging RANDOM hostile worlds, it SEARCHES (learns, via the cross-entropy
    method; adversary = reality) for the world-generation parameters that MAXIMIZE a
    strategy's probability of ruin — bounded so every world it builds still passes the
    Gate (it may only forge REALISTIC worlds; it cannot cheat with absurd ones). A
    strategy that survives the WORST world the adversary can construct is robust to
    path-luck in a way random forging can never show.

    THE LAW: this only ever LOWERS the ruin ceiling / kills. Surviving the adversary is
    'not yet broken' — never 'profitable'. Belief still comes only from forward data."""

    # the bounded, Gate-realistic world-parameter space the adversary searches:
    #   block      : bootstrap block length (longer -> losses cluster -> deeper drawdowns)
    #   crash_prob : frequency of worse-than-history crashes
    #   crash_mult : crash magnitude (x the worst realized return)
    #   bad_bias   : prob of starting blocks in the worst-return regions (adversarial timing)
    LO = np.array([5.0, 0.000, 1.0, 0.0])
    HI = np.array([60.0, 0.040, 3.0, 1.0])

    def __init__(self, n_worlds=1000, horizon=120, ref_lev=1.0,
                 pop=28, gens=6, elite=0.25, seed=SEED + 13):
        self.n, self.h, self.ref = n_worlds, horizon, ref_lev
        self.pop, self.gens, self.elite, self.seed = pop, gens, elite, seed

    def _forge(self, r, theta, rng):
        block = int(round(np.clip(theta[0], 5, min(60, max(5, len(r) // 4)))))
        crash_prob = float(np.clip(theta[1], 0.0, 0.04))
        crash_mult = float(np.clip(theta[2], 1.0, 3.0))
        bad_bias = float(np.clip(theta[3], 0.0, 1.0))
        roll = np.convolve(r, np.ones(block), "valid")          # block-sum at each start
        n_starts = len(roll)
        worst = np.argsort(roll)[: max(1, n_starts // 5)]        # worst-quintile starts
        n_blocks = self.h // block + 1
        use_bad = rng.random((self.n, n_blocks)) < bad_bias
        starts = np.empty((self.n, n_blocks), dtype=int)
        starts[use_bad] = rng.choice(worst, size=int(use_bad.sum()))
        starts[~use_bad] = rng.integers(0, max(1, n_starts), size=int((~use_bad).sum()))
        idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(self.n, -1)[:, :self.h]
        w = r[idx]
        w[rng.random((self.n, self.h)) < crash_prob] = crash_mult * r.min()
        return w

    def _p_ruin(self, w, lev):
        eq = np.cumprod(1.0 + lev * w, axis=1)
        dd = (eq / np.maximum.accumulate(eq, axis=1) - 1.0).min(axis=1)
        return float((dd < -0.50).mean())

    def _fragility(self, r, theta, rng):
        w = self._forge(r, theta, rng)
        ek, ac = _stylized_facts(w)
        if not (ek > 1.0 and ac > 0.02):     # the Gate: an unrealistic world is an invalid attack
            return -1.0
        return self._p_ruin(w, self.ref)

    def coevolve(self, returns):
        r = np.asarray(returns, float); r = r[np.isfinite(r)]
        if len(r) < 30:
            return {"adversarial_ceiling": 0.05, "worst_p_ruin": 1.0, "theta": None}
        rng = np.random.default_rng(self.seed)
        mean, std = (self.LO + self.HI) / 2.0, (self.HI - self.LO) / 4.0
        best_theta, best_frag = mean.copy(), -1.0
        for g in range(self.gens):                              # CEM: learn toward breaking worlds
            samp = np.clip(rng.normal(mean, std, size=(self.pop, 4)), self.LO, self.HI)
            if g == 0:        # first gen: also spray the corners so the search can find narrow ones
                samp = np.clip(rng.uniform(self.LO, self.HI, size=(self.pop, 4)), self.LO, self.HI)
            frags = np.array([self._fragility(r, th, rng) for th in samp])
            order = np.argsort(frags)[::-1]
            elite = samp[order[: max(3, int(self.elite * self.pop))]]
            if frags[order[0]] > best_frag:
                best_frag, best_theta = float(frags[order[0]]), samp[order[0]].copy()
            # learn toward the elite, but keep a floor on std so we don't collapse off a narrow peak
            mean = elite.mean(0)
            std = np.maximum(elite.std(0), (self.HI - self.LO) / 8.0)
        wworst = self._forge(r, best_theta, rng)                # the worst world it found
        ceiling = 0.0
        for f in (0.05, 0.10, 0.20, 0.30, 0.50):
            if self._p_ruin(wworst, f) <= 0.05:
                ceiling = f
        return {"adversarial_ceiling": ceiling, "worst_p_ruin": best_frag, "theta": best_theta}

    @staticmethod
    def describe(theta):
        if theta is None:
            return "n/a"
        block, cp, cm, bb = theta
        return (f"losses cluster in ~{int(round(block))}-bar regimes, {cp*100:.1f}% crashes "
                f"at {cm:.1f}x worst, {bb*100:.0f}% adversarial timing")


# ============================ BELIEF + JOURNAL ============================
class Strategy:
    def __init__(self, key, family, rationale, verdict, ruin_ceiling, shape):
        self.key, self.family, self.rationale = key, family, rationale
        self.verdict, self.ruin_ceiling, self.shape = verdict, ruin_ceiling, shape
        self.belief, self.forward_days, self.forward_sharpe = 0.10, 0, 0.0
    def forward_tick(self, series):
        s = _sharpe(series); self.forward_days += len(series); self.forward_sharpe = s
        self.belief = min(1.0, self.belief+0.12) if s>0 else max(0.0, self.belief-0.05)


class Journal:
    def __init__(self, name): self.path=os.path.join(OUT,f"{name}.md"); self.entries=[]
    def write(self, line): self.entries.append(line)
    def flush(self, header):
        with open(self.path,"w") as f: f.write(f"# {header}\n\n"+"\n".join(self.entries)+"\n")


# ============================ DATA REGISTRY (the data GATE) ============================
class DataRegistry:
    """The vetted allowlist. NOTHING is pre-approved — every desk, crypto included,
    must REQUEST its data source; the Founder approves it onto this allowlist before
    that desk can run. Data sourcing is agent-driven and human-gated, exactly like
    capital (bad data poisons every verdict, so it's gated the same way).

    approve(asset_class, feed) is what the Founder calls to grant a requested source."""
    def __init__(self, approved=None):
        # approved: {asset_class: [feed, ...]}. Empty by default — agents must ask.
        self.approved = dict(approved or {})

    def approve(self, asset_class, feed):
        self.approved.setdefault(asset_class, []).append(feed)

    def feed_for(self, ac):
        f = self.approved.get(ac, []); return f[0] if f else None


# ============================ THE DESK ============================
class Desk:
    def __init__(self, ac, mode, registry, gauntlet, world_engine, demiurge):
        self.ac, self.mode = ac, mode
        self.registry, self.gauntlet, self.we, self.demiurge = registry, gauntlet, world_engine, demiurge
        self.theorist = (ClaudeTheorist(ac) if mode in ("live-agent","live") else StubTheorist(ac))
        self.graveyard, self.forward_book = [], []
        self.journal = Journal(f"desk_{ac}"); self.data_request = None
        self._rng = np.random.default_rng(SEED + hash(ac) % 1000)

    @property
    def has_data(self): return self.registry.feed_for(self.ac) is not None

    def _returns_for(self, family):
        """Get a return series to judge. Synthetic in dry/live-agent; REAL in live."""
        if self.mode == "live":
            import live_engine
            r, venue, side = live_engine.strategy_returns(family, "BTC")  # crypto desk ref
            return r, f"REAL:{venue}"
        return synth_returns(_synth_for(family, self._rng)), "SYNTHETIC"

    def run_cycle(self, iterations):
        if not self.has_data:
            # The desk has no approved feed. It identifies what it needs and FILES a
            # request for you to approve or deny — data sourcing is agent-driven, human-
            # gated, like capital. In LIVE mode this also BLOCKS the desk (real verdicts
            # require real approved data). In dry/live-agent the agent still explores on
            # explicitly-illustrative synthetic data so you can watch it hunt first.
            src = {"crypto":   "a crypto perp feed (e.g. ccxt: Hyperliquid/OKX/Gate) for funding+price",
                   "equities": "an equities feed (e.g. Polygon.io / Databento, point-in-time)",
                   "options":  "an options feed (e.g. ORATS / Cboe DataShop, IV surfaces)"}.get(
                       self.ac, "a vetted point-in-time data feed")
            self.data_request = (src, "Agent needs this to hunt for real; un-vetted data manufactures "
                                      "false confidence, so it's gated like capital. Awaiting Founder.")
            self.journal.write(f"- DATA REQUEST: {src}. {'BLOCKED until approved.' if self.mode=='live' else 'Exploring on synthetic meanwhile.'}")
            if self.mode == "live":
                return   # real verdicts require approved data — stop and wait.

        seen = {g["key"] for g in self.graveyard} | {s.key for s in self.forward_book}
        for _ in range(iterations):
            try:
                prop = self.theorist.propose(seen)
            except Exception as e:
                # live proposer failed (e.g. no ANTHROPIC_API_KEY / SDK / network).
                # Degrade gracefully: fall this desk back to the stub and tell the user.
                if not isinstance(self.theorist, StubTheorist):
                    self.journal.write(f"- PROPOSER FELL BACK to stub: {type(e).__name__}: {str(e)[:80]}")
                    print(f"  !! {self.ac}: live proposer failed ({type(e).__name__}). "
                          f"Set ANTHROPIC_API_KEY for live agents. Using stub for this desk.")
                    self.theorist = StubTheorist(self.ac)
                    prop = self.theorist.propose(seen)
                else:
                    break
            if prop is None: break
            family, rationale = prop["family"], prop["rationale"]
            key = f"{self.ac}:{family}"
            if key in seen: continue
            seen.add(key)
            try:
                returns, src = self._returns_for(family)
            except Exception as e:
                # agent proposed an edge with no executable kernel, or data STOPPED.
                self.journal.write(f"- NOT-RUN  {family:16s} — {type(e).__name__}: {str(e)[:70]}")
                continue
            v = self.gauntlet.adjudicate(returns)            # referee sees ONLY the data
            tag = "" if src.startswith("REAL") else " [synthetic verdict — illustrative]"
            if v.killed:
                self.graveyard.append({"key":key,"family":family})
                self.journal.write(f"- KILLED  {family:16s} IS {v.is_sharpe:+.2f} -> OOS {v.oos_sharpe:+.2f}"
                                   f" | wf {v.wf_sharpe:+.2f} | {', '.join(v.kills)}{tag}")
            else:
                st = self.we.stress(returns)
                adv = self.demiurge.coevolve(returns)           # the learning adversary attacks
                # the adversary can only LOWER the ceiling (the Law): worst of random vs adversarial.
                ceiling = min(st["ruin_ceiling"], adv["adversarial_ceiling"])
                s = Strategy(key, family, rationale, v, ceiling, st["shape"])
                s.forward_tick(synth_returns("structural", n=120, rng=np.random.default_rng(SEED+99)))
                self.forward_book.append(s)
                gate = ("" if st.get("gate_passed", True)
                        else f" | !! forger REJECTED by Gate — ceiling capped")
                self.journal.write(f"- SURVIVED {family:14s} (not yet disproven) | random-ceiling "
                                   f"{st['ruin_ceiling']:.0%} -> ADVERSARIAL {adv['adversarial_ceiling']:.0%} "
                                   f"| shape skew {st['shape']['skew']:+.2f} | -> forward-paper, "
                                   f"belief {s.belief:.2f}{tag}{gate}")
                self.journal.write(f"    Demiurge worst world ({adv['worst_p_ruin']:.0%} ruin @20%): "
                                   f"{Demiurge.describe(adv['theta'])}")
            self.journal.write(f"    rationale: {rationale[:140]}")

    def track_score(self): return sum(s.belief*s.ruin_ceiling for s in self.forward_book)


# ============================ CAPITAL ALLOCATOR (firewall: capital only) ============================
class CapitalAllocator:
    def __init__(self, budget=100_000.0, floor=1e-9): self.budget, self.floor = budget, floor
    def allocate(self, desks):
        scores = {d.ac: d.track_score() for d in desks}; total = sum(scores.values())
        alloc, pruned = {}, []
        for d in desks:
            if d.has_data and scores[d.ac] <= self.floor: pruned.append(d.ac)
            alloc[d.ac] = (self.budget*scores[d.ac]/total) if total>0 else 0.0
        return alloc, scores, pruned


# ============================ THE BOARD (event gates + weekly review) ============================
class Board:
    def __init__(self): self.event_queue = []
    def file_event(self, kind, detail):
        if not any(e["detail"]==detail for e in self.event_queue):
            self.event_queue.append({"kind":kind,"detail":detail,"status":"PENDING-FOUNDER-APPROVAL"})
    def weekly_review(self, desks, alloc, scores, pruned, tail):
        print("\n"+"="*78+"\nBOARD — WEEKLY STRATEGY REVIEW  (steering; not a gate)\n"+"="*78)
        for d in desks:
            status = "NO DATA (gated)" if (d.mode=="live" and not d.has_data) else (
                "PRUNE CANDIDATE" if d.ac in pruned else f"{len(d.forward_book)} on forward-paper")
            print(f"  {d.ac:9s} | killed {len(d.graveyard):2d} | {status:18s} | "
                  f"track {scores[d.ac]:.3f} | paper-capital ${alloc[d.ac]:,.0f}")
        print(f"\n  CROSS-DESK TAIL: {tail}")
        print("  DIRECTION: hunt on funded desks; gated desks idle until their feed clears;")
        print("             prune anything bearing nothing.")
    def show_queue(self):
        print("\n"+"="*78+f"\nEVENT GATES — AWAITING FOUNDER  ({len(self.event_queue)} pending; these STOP the org)\n"+"="*78)
        if not self.event_queue: print("  (none)")
        for e in self.event_queue:
            print(f"  [{e['status']}]  {e['kind']}\n        {e['detail']}")


# ============================ ATLAS (CEO orchestrator) ============================
class Atlas:
    def __init__(self, desks, allocator, board): self.desks,self.allocator,self.board=desks,allocator,board
    def _tail(self):
        books = [s for d in self.desks for s in d.forward_book]
        if len(books) < 2: return "only one survivor across the floor — no diversification yet."
        rng = np.random.default_rng(SEED+3); shared = rng.standard_normal(2000); L=[]
        for _ in books:
            x = 0.6*shared + 0.4*rng.standard_normal(2000); L.append(x < np.percentile(x,5))
        co = np.mean([np.mean(L[i]&L[j])/0.05 for i in range(len(L)) for j in range(i+1,len(L))])
        return f"survivors co-crash ~{co:.1f}x independence — {'diversified' if co<1.5 else 'secretly one bet; size as one'}."
    def run_week(self, weeks, iterations):
        for _ in range(weeks):
            for d in self.desks: d.run_cycle(iterations)
        for d in self.desks:
            if d.data_request:
                self.board.file_event("DATA-SOURCE", f"{d.ac}: approve `{d.data_request[0]}` — {d.data_request[1]}")
            for s in d.forward_book:
                if s.belief >= 0.30 and s.forward_sharpe > 0:
                    self.board.file_event("GRADUATION",
                        f"{d.ac}/{s.family}: fwd belief {s.belief:.2f}, fwd-Sharpe {s.forward_sharpe:+.2f}, "
                        f"ceiling {s.ruin_ceiling:.0%}. Requests CAPPED live capital (<=ceiling, no leverage, "
                        f"each trade Founder-confirmed).")
        alloc, scores, pruned = self.allocator.allocate(self.desks)
        self.board.weekly_review(self.desks, alloc, scores, pruned, self._tail())
        self.board.show_queue()
        for d in self.desks: d.journal.flush(f"Desk: {d.ac}")


# ============================ MAIN ============================
def main():
    ap = argparse.ArgumentParser(description="NULLIUS x POLARIS — the falsification floor.")
    ap.add_argument("--mode", choices=["dry","live-agent","live"], default="dry")
    ap.add_argument("--weeks", type=int, default=4, help="forward cycles to run")
    ap.add_argument("--iterations", type=int, default=4, help="HARD cap on proposals/desk/week (bounded loop)")
    ap.add_argument("--desks", default="crypto,equities,options")
    args = ap.parse_args()

    print("="*78)
    print(f"NULLIUS x POLARIS — THE FALSIFICATION FLOOR   [mode: {args.mode}]")
    print("Law: a sim may only KILL, never BLESS. Firewall: performance funds capital,")
    print("     never the verdict. Real capital + new data = human-gated events.")
    if args.mode == "live-agent":
        print("NOTE: agents explore for REAL; judging data is SYNTHETIC -> verdicts illustrative.")
    if args.mode == "dry":
        print("NOTE: deterministic stub proposer + synthetic data. Proves the machinery.")
    print("="*78)

    registry, gauntlet, we, dm = DataRegistry(), Gauntlet(), WorldEngine(), Demiurge()
    acs = [a.strip() for a in args.desks.split(",") if a.strip()]
    try:
        desks = [Desk(ac, args.mode, registry, gauntlet, we, dm) for ac in acs]
    except Exception as e:
        print(f"\n!! Could not start desks: {type(e).__name__}: {e}")
        print("   For --mode live/live-agent you need ANTHROPIC_API_KEY set "
              "(export ANTHROPIC_API_KEY=sk-ant-...). Falling back to --mode dry.")
        desks = [Desk(ac, "dry", registry, gauntlet, we, dm) for ac in acs]

    Atlas(desks, CapitalAllocator(), Board()).run_week(args.weeks, args.iterations)

    print("\n"+"="*78+"\nHONEST STATUS\n"+"="*78)
    print("  - The machine ran end to end: desks proposed, the gauntlet killed, survivors")
    print("    took ruin ceilings + entered forward-paper, the allocator funded by track")
    print("    record, the board steered, money/data parked at the Founder gate.")
    print("  - 'SURVIVED' = not yet disproven. Nothing here is profitable or proven.")
    if args.mode != "live":
        print("  - Judging data is SYNTHETIC. Real verdicts need --mode live + a VERIFIED")
        print("    live_engine.py (replace its bodies with your NULLIUS data+strategy modules).")
    print(f"  - Belief rises only on real forward evidence over time. Journals: {OUT}/")
    print("="*78)


if __name__ == "__main__":
    main()
