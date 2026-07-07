# Binance Futures Testnet Trading Bot

A small, structured Python CLI application for placing MARKET and LIMIT
orders (BUY/SELL) on Binance Futures Testnet (USDT-M), with input
validation, logging, and clean error handling.

## Project Structure

```
trading_bot/
  bot/
    __init__.py
    client.py         # Signed REST client for Binance Futures Demo Trading
    orders.py         # Order placement logic + request/response printing
    validators.py      # Input validation (shared by both CLI modes)
    interactive.py     # Guided interactive menu mode
    logging_config.py  # Logging setup (console + rotating file handler)
  cli.py               # CLI entry point (argparse + interactive mode)
  requirements.txt
  .env.example
  README.md
```

## Setup

### 1. Get Binance Futures Demo Trading API credentials

**Note:** Binance retired the old standalone testnet site (`testnet.binancefuture.com`
with its own GitHub-based signup). Futures paper trading is now called
**Demo Trading** and lives inside your regular Binance account:

1. Log into (or create) a regular Binance account at https://www.binance.com.
2. Go to **Futures** and enable **Demo Trading** (sometimes labeled "Mock
   Trading"). It auto-allocates virtual USDT — no real funds needed.
3. Inside Demo Trading, go to **API Management** and generate a **Demo
   Trading API Key + Secret** (this is separate from any real-money API key).

The REST base URL used by this app is `https://demo-fapi.binance.com`,
which is Binance's current official endpoint for Futures Demo Trading
(this replaced the old `testnet.binancefuture.com` REST API).

### 2. Install dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure credentials
Copy `.env.example` to `.env` and fill in your keys, then export them
before running (this app reads plain environment variables, not a
`.env` file directly — use `python-dotenv` or export manually):

```bash
export BINANCE_API_KEY="your_testnet_api_key"
export BINANCE_API_SECRET="your_testnet_api_secret"
```

On Windows (PowerShell):
```powershell
$env:BINANCE_API_KEY="your_testnet_api_key"
$env:BINANCE_API_SECRET="your_testnet_api_secret"
```

## Usage

### Interactive mode (guided menus + validation messages)
For a friendlier, no-flags-to-remember experience, just run:
```bash
python cli.py
```
This walks you through symbol, side, order type, quantity, and price
(if applicable) via numbered menus, re-prompting with a specific error
message on invalid input, and shows a review + confirmation step before
anything is actually sent to Binance.

### Flag-based mode (scriptable)

#### Market order (BUY)
```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

### Limit order (SELL)
```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 65000
```

### CLI arguments
| Argument      | Required          | Description                          |
|---------------|-------------------|---------------------------------------|
| `--symbol`    | Yes               | Trading pair, e.g. `BTCUSDT`          |
| `--side`      | Yes               | `BUY` or `SELL`                       |
| `--type`      | Yes               | `MARKET` or `LIMIT`                   |
| `--quantity`  | Yes               | Order quantity (float, > 0)           |
| `--price`     | Only for LIMIT    | Limit price (float, > 0)              |

### Sample output
```
=== Order Request ===
  Symbol     : BTCUSDT
  Side       : BUY
  Type       : MARKET
  Quantity   : 0.01
======================

=== Order Response ===
  Order ID     : 12345678
  Status       : FILLED
  Executed Qty : 0.01
  Avg Price    : 60123.40
=======================

[SUCCESS] Order placed successfully.
```

## Logging

All requests, responses, and errors are logged to `logs/trading_bot.log`
(created automatically on first run). The file handler captures
DEBUG-level detail (full request params and raw API responses); the
console only shows INFO-level summaries so normal usage isn't noisy.

The log file rotates at 5MB with 3 backups kept, so it won't grow
unbounded during extended testing.

## Error Handling

The app distinguishes between three failure modes and reports each clearly:
- **Invalid input** — caught before any API call (e.g. bad symbol format,
  missing price on a LIMIT order, non-positive quantity).
- **API-level errors** — Binance rejects the order (e.g. insufficient
  testnet balance, invalid symbol, filters not met). The raw Binance
  error payload is logged and shown.
- **Network errors** — timeouts or connection failures talking to the
  testnet endpoint.

In all cases the CLI exits with a non-zero status code on failure, so it
can be scripted/CI-checked.

## Assumptions

- Only USDT-M Futures Demo Trading is targeted (`https://demo-fapi.binance.com`,
  Binance's current endpoint after retiring the old standalone
  `testnet.binancefuture.com` site), not Spot Testnet or Coin-M Futures.
- LIMIT orders are placed with `timeInForce=GTC` (Good-Till-Cancelled),
  since the task didn't specify a different policy.
- Credentials are read from environment variables rather than a config
  file, to avoid ever committing secrets to source control.
- No position-sizing or risk-management logic is included — the bot
  places exactly the order it's told to, which matches the "simplified
  trading bot" scope of this task.
- Direct REST calls (via `requests`) were used instead of the
  `python-binance` library, to keep the signing/request logic fully
  visible and dependency-light.

## Bonus Features Implemented
- **Enhanced CLI UX**: running `python cli.py` with no arguments launches
  an interactive guided mode (`bot/interactive.py`) — numbered menus for
  side/order type, re-prompting with specific validation messages on bad
  input, and a review + y/N confirmation step before the order is sent.

## Possible Further Extensions
- Add a `STOP` order type in `bot/client.py` (Binance Futures supports
  `STOP`, `STOP_MARKET`, `TAKE_PROFIT`, etc. — same signed endpoint,
  different `type` + extra params like `stopPrice`).
- Add a `--dry-run` flag that prints the request without calling the API.
