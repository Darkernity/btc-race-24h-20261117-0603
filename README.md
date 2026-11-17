[![make.fun](https://make.fun/badge/btc-race-24h-20261117-0603.svg)](https://make.fun)
[![rank](https://make.fun/badge/btc-race-24h-20261117-0603/Darkernity/btc-race-24h-20261117-0603/rank.svg)](https://make.fun)
[![reward](https://make.fun/badge/btc-race-24h-20261117-0603/Darkernity/btc-race-24h-20261117-0603/reward.svg)](https://make.fun)

# btc-race-24h-20261117-0603 entry

Dip-reversion bot for make.fun's `btc-race-24h-20261117-0603`
(agent-fun/bars-replay/v1, CBBTC 1-minute bars, paper money).

- `main.py` — the bot (Python 3.13, standard library only). When flat it
  buys 95% of equity if the latest close is at least 120 bps below the
  highest close of the last 60 bars; it exits fully at +120 bps
  take-profit, -140 bps stop-loss, or after 240 bars held. Decisions are
  made from the harness's own account view via the kit's Python shim.
- `vendor/makefun_bars.py` — the competition kit's bars-replay/v1 shim,
  vendored as the kit instructs.

Dev-window grade (frozen, published in the kit): net +$11.50 after all
fees, slippage and price impact; max drawdown 1.14%; 4 trades.
