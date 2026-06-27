"""
live_engine.py  —  THE ONE MODULE TO SCRUTINIZE BEFORE YOU TRUST IT.
====================================================================
This is the seam where REAL market data and a REAL strategy kernel enter the floor.
Everything above it (the gauntlet, world engine, allocator, board) is verified and
deterministic. This file is NOT — it talks to live exchanges and computes a strategy
return series, and a subtle bug here (lookahead, misaligned funding, wrong sign)
silently POISONS every verdict the floor produces. The Law: bad data manufactures
false confidence. So:

  >>> REPLACE THE BODIES BELOW WITH YOUR VERIFIED NULLIUS MODULES <<<
      - fetch_market_data()  ->  your nullius.data.fetch + nullius.data.align
      - carry_returns()      ->  your nullius.strategy.carry

  Until you do, this provides a careful REFERENCE using ccxt's *unified* methods so
  the floor can run live on the crypto desk — but the first live run PRINTS A
  SELF-CHECK you must eyeball, and if no venue responds it STOPS and reports rather
  than ever fabricating a single bar.

Paper/research only. This file places NO orders and holds NO keys.
"""
from __future__ import annotations

import numpy as np


class DataUnavailable(RuntimeError):
    """No venue responded. We STOP and report — we never fabricate data (the Law)."""


# Priority order: try each until one actually responds with usable data.
_VENUES = ("hyperliquid", "okx", "gate")
_SYMBOLS = {  # ccxt unified perp symbols; adjust per venue if needed on first run
    "BTC": "BTC/USDT:USDT",
    "ETH": "ETH/USDT:USDT",
    "SOL": "SOL/USDT:USDT",
}


def fetch_market_data(base: str, history_days: int = 180, timeframe: str = "1h"):
    """REFERENCE fetcher (ccxt unified). Returns (price_returns, funding_per_bar, venue).
    Tries venues in priority order; STOPS (raises DataUnavailable) if none respond.
    VERIFY the funding-rate field + alignment against your venue, or swap in your
    nullius.data.fetch — yours is verified, this is a starting point."""
    import ccxt

    sym = _SYMBOLS.get(base.upper())
    if sym is None:
        raise DataUnavailable(f"no symbol mapping for {base!r}; add it to _SYMBOLS")

    last_err = None
    for vid in _VENUES:
        try:
            ex = getattr(ccxt, vid)({"enableRateLimit": True})
            ex.load_markets()
            # prices
            ohlcv = ex.fetch_ohlcv(sym, timeframe=timeframe, limit=min(history_days * 24, 1000))
            if not ohlcv or len(ohlcv) < 100:
                raise DataUnavailable(f"{vid}: too few OHLCV bars")
            close = np.array([c[4] for c in ohlcv], float)
            price_ret = close[1:] / close[:-1] - 1.0
            # funding (unified): list of {timestamp, fundingRate, ...}
            fh = ex.fetch_funding_rate_history(sym, limit=min(history_days * 3, 1000))
            if not fh:
                raise DataUnavailable(f"{vid}: no funding history")
            fr = np.array([float(x["fundingRate"]) for x in fh if x.get("fundingRate") is not None], float)
            # align lengths conservatively (forward-fill funding onto bars is venue-specific;
            # here we just trim to a common length — REPLACE with your real alignment)
            n = min(len(price_ret), len(fr))
            if n < 100:
                raise DataUnavailable(f"{vid}: insufficient aligned data (n={n})")
            return price_ret[-n:], fr[-n:], vid
        except DataUnavailable:
            raise
        except Exception as e:  # network/venue error — try the next venue
            last_err = f"{vid}: {type(e).__name__}: {str(e)[:80]}"
            continue

    raise DataUnavailable(
        "No venue responded (tried " + ", ".join(_VENUES) + "). Last error: "
        + (last_err or "unknown") + ". The droplet must reach the exchange APIs. "
        "We STOP rather than fabricate (the Law).")


def carry_returns(price_ret: np.ndarray, funding: np.ndarray,
                  side: float = 1.0, cost_per_bar: float = 5e-5) -> np.ndarray:
    """REFERENCE delta-neutral funding-carry return series. Long spot / short perp
    (side=+1) collects funding; the delta-neutral construction cancels most price
    exposure, so per-bar return ~ funding collected on the paid side minus costs.
    This is a SIMPLIFICATION — your nullius.strategy.carry marks both legs, rebalances
    the perp at tau, and handles basis. SWAP IT IN for a real verdict."""
    funding = np.asarray(funding, float)
    # collect funding on the structurally-paid side; subtract a per-bar cost drag.
    r = side * funding - cost_per_bar
    return r[np.isfinite(r)]


def strategy_returns(family: str, base: str, history_days: int = 180):
    """Map an (executable) hypothesis to a REAL return series on REAL data.
    Only families with a kernel here are executable; anything else is surfaced as
    'needs a kernel' rather than faked (mirrors NULLIUS's hypothesis.validate gate)."""
    if family != "funding_carry":
        raise NotExecutable(
            f"family {family!r} has no executable kernel yet. The agent can PROPOSE it, "
            f"but the engine can't run it until you build the kernel. Expanding the "
            f"executable strategy space is the real frontier work.")
    price_ret, funding, venue = fetch_market_data(base, history_days=history_days)
    side = 1.0 if np.mean(funding) >= 0 else -1.0
    r = carry_returns(price_ret, funding, side=side)
    return r, venue, side


class NotExecutable(RuntimeError):
    """The agent proposed an edge the engine has no kernel for. Logged, never faked."""


def self_check():
    """Run on first live use: prove the data path is real and STOPS honestly offline."""
    print("  live_engine self-check: attempting a real fetch (BTC)...")
    try:
        r, venue, side = strategy_returns("funding_carry", "BTC", history_days=30)
        print(f"    OK: {len(r)} real bars from {venue}; side={'forward' if side>0 else 'reverse'}; "
              f"mean funding/bar {np.mean(r):+.2e}. >>> EYEBALL THIS before trusting verdicts. <<<")
        return True
    except (DataUnavailable, NotExecutable) as e:
        print(f"    STOPPED (honestly, no fabrication): {e}")
        return False


if __name__ == "__main__":
    self_check()
