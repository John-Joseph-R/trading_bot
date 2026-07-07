"""
Order placement logic: ties together validation, the API client, and
presenting a clean summary of what was requested vs. what happened.
"""
import time

from bot.client import BinanceAPIError, BinanceNetworkError, BinanceFuturesClient
from bot.logging_config import setup_logger
from bot.validators import ValidationError, validate_order_params

logger = setup_logger(__name__)

# Binance's order-placement response is sometimes just the initial
# acknowledgment (status NEW) even for MARKET orders, with the actual
# fill confirmed a moment later. These control a brief re-check so the
# printed/logged result reflects the settled outcome rather than just
# the instant of submission.
STATUS_POLL_ATTEMPTS = 3
STATUS_POLL_DELAY_SECONDS = 1


class OrderResult:
    """Simple container for a normalized order outcome."""

    def __init__(self, success: bool, request: dict, response: dict = None, error: str = None):
        self.success = success
        self.request = request
        self.response = response or {}
        self.error = error


def print_order_request(symbol, side, order_type, quantity, price):
    print("\n=== Order Request ===")
    print(f"  Symbol     : {symbol}")
    print(f"  Side       : {side}")
    print(f"  Type       : {order_type}")
    print(f"  Quantity   : {quantity}")
    if order_type == "LIMIT":
        print(f"  Price      : {price}")
    print("======================\n")


def print_order_response(response: dict):
    print("=== Order Response ===")
    print(f"  Order ID     : {response.get('orderId', 'N/A')}")
    print(f"  Status       : {response.get('status', 'N/A')}")
    print(f"  Executed Qty : {response.get('executedQty', 'N/A')}")
    avg_price = response.get("avgPrice")
    if avg_price is not None:
        print(f"  Avg Price    : {avg_price}")
    print("=======================\n")


def place_order(client: BinanceFuturesClient, symbol, side, order_type, quantity, price=None) -> OrderResult:
    """Validate input, place the order, log everything, and return a result.

    Handles three failure modes distinctly: bad input, API-level errors
    (e.g. insufficient balance, invalid symbol), and network failures.
    """
    request_summary = {
        "symbol": symbol,
        "side": side,
        "order_type": order_type,
        "quantity": quantity,
        "price": price,
    }

    try:
        symbol, side, order_type, quantity, price = validate_order_params(
            symbol, side, order_type, quantity, price
        )
    except ValidationError as exc:
        logger.error("Validation failed for request %s: %s", request_summary, exc)
        print(f"\n[FAILED] Invalid input: {exc}\n")
        return OrderResult(success=False, request=request_summary, error=str(exc))

    print_order_request(symbol, side, order_type, quantity, price)
    logger.info("Placing order: %s", request_summary)

    try:
        response = client.place_order(symbol, side, order_type, quantity, price)
    except BinanceAPIError as exc:
        logger.error("Order rejected by Binance: %s", exc.payload)
        print(f"[FAILED] Binance rejected the order: {exc.payload}\n")
        return OrderResult(success=False, request=request_summary, error=str(exc))
    except BinanceNetworkError as exc:
        logger.error("Network failure placing order: %s", exc)
        print(f"[FAILED] Network error: {exc}\n")
        return OrderResult(success=False, request=request_summary, error=str(exc))

    logger.info("Order placed successfully: %s", response)

    # MARKET orders can come back as NEW/0 executedQty even though they
    # fill almost instantly - re-check briefly so we report the real outcome.
    if order_type == "MARKET" and response.get("status") == "NEW":
        response = _poll_for_fill(client, symbol, response)

    print_order_response(response)
    print("[SUCCESS] Order placed successfully.\n")
    return OrderResult(success=True, request=request_summary, response=response)


def _poll_for_fill(client: BinanceFuturesClient, symbol: str, response: dict) -> dict:
    """Re-query an order a few times to catch the settled fill status.

    Returns the latest response seen; falls back to the original response
    if polling fails or the status never updates (e.g. network hiccup) -
    this is a best-effort check, not a hard requirement for success.
    """
    order_id = response.get("orderId")
    if order_id is None:
        return response

    for attempt in range(1, STATUS_POLL_ATTEMPTS + 1):
        time.sleep(STATUS_POLL_DELAY_SECONDS)
        try:
            latest = client.get_order_status(symbol, order_id)
        except (BinanceAPIError, BinanceNetworkError) as exc:
            logger.warning("Status poll attempt %s failed for order %s: %s", attempt, order_id, exc)
            continue

        logger.info("Status poll attempt %s for order %s: %s", attempt, order_id, latest)
        if latest.get("status") != "NEW":
            return latest

    logger.info("Order %s still NEW after %s poll attempts; reporting last known state.",
                order_id, STATUS_POLL_ATTEMPTS)
    return response
