#!/usr/bin/env python3
"""
CLI entry point for the Binance Futures Testnet trading bot.

Usage examples:
    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
    python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 60000
"""
import argparse
import os
import sys

from bot.client import BinanceFuturesClient
from bot.logging_config import setup_logger
from bot.orders import place_order

logger = setup_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Place MARKET or LIMIT orders on Binance Futures Testnet (USDT-M)."
    )
    parser.add_argument("--symbol", required=True, help="Trading pair symbol, e.g. BTCUSDT")
    parser.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"], help="Order side")
    parser.add_argument(
        "--type", dest="order_type", required=True,
        choices=["MARKET", "LIMIT", "market", "limit"], help="Order type"
    )
    parser.add_argument("--quantity", required=True, help="Order quantity")
    parser.add_argument("--price", required=False, default=None, help="Price (required for LIMIT orders)")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    api_key = os.environ.get("BINANCE_API_KEY")
    api_secret = os.environ.get("BINANCE_API_SECRET")

    if not api_key or not api_secret:
        print(
            "[FAILED] Missing credentials. Set BINANCE_API_KEY and BINANCE_API_SECRET "
            "environment variables (see README.md)."
        )
        sys.exit(1)

    if args.order_type.upper() == "LIMIT" and args.price is None:
        print("[FAILED] --price is required when --type is LIMIT.")
        sys.exit(1)

    try:
        client = BinanceFuturesClient(api_key=api_key, api_secret=api_secret)
    except ValueError as exc:
        logger.error("Failed to initialize client: %s", exc)
        print(f"[FAILED] {exc}")
        sys.exit(1)

    result = place_order(
        client=client,
        symbol=args.symbol,
        side=args.side,
        order_type=args.order_type,
        quantity=args.quantity,
        price=args.price,
    )

    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
