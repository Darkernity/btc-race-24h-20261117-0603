#!/usr/bin/env python3
"""btc-race-24h-20261117-0603 entry bot (main.py) — stdlib only, deterministic.

Strategy: dip-reversion on CBBTC 1-minute bars. Parameters frozen from
the 2026-11-17 dev-window screen (integer-exact replay, cross-checked
to the official grade-local to the unit): net +$11.50 on the dev
window, +$13.92 under 2x fees, +$11.22 under half pool depth,
max drawdown 1.14%, 4 trades.

Rules: when flat, buy 95% of equity if the latest close is at least
120 bps below the highest close of the last 60 bars. When holding,
exit fully at +120 bps take-profit, -140 bps stop-loss, or after
240 bars held.

Wire protocol: agent-fun/bars-replay/v1 via the kit's own Python shim
(vendor/makefun_bars.py). The bot is state-driven: every decision is
made from the harness's own account view (cash, position quantity and
cost basis) exactly as the screening oracle modelled it — the entry
price basis is the filled notional over the filled quantity, a sell
is always the entire held quantity, and every order carries
max_slippage_bps = 500, so an order the market would fill beyond that
bound is rejected and simply re-decided on the next bar's true state.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "vendor"))
import makefun_bars  # noqa: E402

SYMBOL = "CBBTC"
QTY_SCALE = 1e8       # cbBTC has 8 decimals
QUOTE_SCALE = 1e6     # USDC has 6 decimals
SLIP_CAP = 500        # max_slippage_bps on every order
MIN_NOTIONAL_UNITS = 1_000_000  # official min_notional = 1 USDC

# Frozen screening winner (dip family).
LOOKBACK = 60
DIP_BPS = 120
SIZE = 0.95
TP_BPS = 120
SL_BPS = 140
MAX_HOLD = 240


class DipBot:
    """Dip-reversion decided from the observed account, wire-style."""

    def __init__(self):
        self.closes = []        # dollar closes, one per bar seen
        self.entry_price = None  # dollars, filled notional / filled qty
        self.entry_bar = None    # batch seq at which the fill was seen
        self.pending = None      # ("buy", notional_units) | ("sell", qty)
        self.prev_qty = 0

    def _target(self, held, bars_held):
        closes = self.closes
        t = len(closes) - 1
        if held and self.entry_price:
            chg = closes[-1] / self.entry_price - 1.0
            if chg >= TP_BPS / 1e4 or chg <= -SL_BPS / 1e4 \
                    or bars_held >= MAX_HOLD:
                return 0.0
            return None  # hold
        if t < LOOKBACK:
            return 0.0
        ref = max(closes[-LOOKBACK:])
        if closes[-1] > ref * (1 - DIP_BPS / 1e4):
            return 0.0
        return SIZE

    def on_batch(self, state, batch):
        held_pos = state.positions.get(SYMBOL)
        qty = held_pos.qty if held_pos is not None else 0
        # Reconcile last batch's order against the observed account:
        # a filled buy sets the entry basis from what actually filled.
        if self.pending is not None:
            kind, amt = self.pending
            if kind == "buy" and qty > self.prev_qty:
                dq = qty - self.prev_qty
                self.entry_price = (amt / QUOTE_SCALE) / (dq / QTY_SCALE)
                self.entry_bar = state.seq
            elif kind == "sell" and qty == 0:
                self.entry_price = None
                self.entry_bar = None
            self.pending = None
        self.prev_qty = qty

        bar = state.latest.get(SYMBOL)
        if bar is not None and any(b["symbol"] == SYMBOL
                                   for b in batch["bars"]):
            # Price ints are dollars scaled by the symbol's own
            # price_scale from the hello (1e5 for CBBTC): read it from
            # the session state, never assume it.
            scale = 10 ** int(state.symbols[SYMBOL]["price_scale"])
            self.closes.append(int(bar["c"]) / scale)
        if not self.closes:
            return []
        held = qty > 0
        bars_held = (state.seq - self.entry_bar) \
            if held and self.entry_bar is not None else 0
        tgt = self._target(held, bars_held)
        if tgt is None:
            return []
        if held:
            if tgt == 0.0:
                self.pending = ("sell", qty)
                return [{"side": "sell", "symbol": SYMBOL, "qty": qty,
                         "max_slippage_bps": SLIP_CAP}]
            return []
        if tgt > 0.0:
            notional = int(tgt * state.equity)
            if notional > state.cash:
                notional = state.cash
            if notional < MIN_NOTIONAL_UNITS:
                return []
            self.pending = ("buy", notional)
            return [{"side": "buy", "symbol": SYMBOL,
                     "notional_quote_units": notional,
                     "max_slippage_bps": SLIP_CAP}]
        return []


_bot = DipBot()


def on_batch(state, batch):
    return _bot.on_batch(state, batch)


if __name__ == "__main__":
    makefun_bars.run(on_batch)
