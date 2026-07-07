"""
Interactive CLI mode: numbered menus and re-prompting input, for people
who'd rather be guided through placing an order than remember flag names.

Triggered automatically when cli.py is run with no arguments.
"""
from bot.validators import (
    ValidationError,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_symbol,
)

BANNER = """
==================================================
   Binance Futures Demo Trading Bot - Interactive
==================================================
"""


def prompt_until_valid(prompt_text: str, validator, *validator_args):
    """Keep asking until the validator accepts the input, showing the
    specific validation error each time so the user knows exactly what
    to fix (rather than a generic 'invalid input, try again')."""
    while True:
        raw = input(prompt_text).strip()
        try:
            return validator(raw, *validator_args) if validator_args else validator(raw)
        except ValidationError as exc:
            print(f"  \u2717 {exc}\n")


def choose_from_menu(prompt_text: str, options: list) -> str:
    """Show a numbered menu and return the chosen option (uppercase)."""
    while True:
        print(prompt_text)
        for i, option in enumerate(options, start=1):
            print(f"  {i}. {option}")
        raw = input("Enter a number: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1].upper()
        print(f"  \u2717 Please enter a number between 1 and {len(options)}.\n")


def run_interactive_flow():
    """Walk the user through building a valid order request.

    Returns a dict with symbol, side, order_type, quantity, price
    (price is None for MARKET orders), or None if the user cancels.
    """
    print(BANNER)
    print("Fill in each field below. Invalid entries will re-prompt with a specific reason.\n")

    symbol = prompt_until_valid("Symbol (e.g. BTCUSDT): ", validate_symbol)
    side = choose_from_menu("\nSelect order side:", ["BUY", "SELL"])
    order_type = choose_from_menu("\nSelect order type:", ["MARKET", "LIMIT"])
    quantity = prompt_until_valid("\nQuantity (e.g. 0.01): ", validate_quantity)

    price = None
    if order_type == "LIMIT":
        price = prompt_until_valid("Price (required for LIMIT): ", validate_price, order_type)

    print("\n--- Review your order ---")
    print(f"  Symbol   : {symbol}")
    print(f"  Side     : {side}")
    print(f"  Type     : {order_type}")
    print(f"  Quantity : {quantity}")
    if price is not None:
        print(f"  Price    : {price}")

    confirm = input("\nSubmit this order? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Cancelled. No order was sent.")
        return None

    return {
        "symbol": symbol,
        "side": side,
        "order_type": order_type,
        "quantity": quantity,
        "price": price,
    }
