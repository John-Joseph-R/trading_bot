"""
Thin REST client for Binance Futures Testnet (USDT-M).

Implements request signing (HMAC SHA256) and handles the low-level HTTP
concerns (timeouts, network errors, non-2xx responses) so the rest of the
app never talks to `requests` directly.
"""
import hashlib
import hmac
import time
from urllib.parse import urlencode

import requests

from bot.logging_config import setup_logger

logger = setup_logger(__name__)


class BinanceAPIError(Exception):
    """Raised when Binance returns a non-2xx / error response."""

    def __init__(self, status_code, payload):
        self.status_code = status_code
        self.payload = payload
        super().__init__(f"Binance API error [{status_code}]: {payload}")


class BinanceNetworkError(Exception):
    """Raised for connection/timeout issues talking to Binance."""


class BinanceFuturesClient:
    """Minimal signed REST client for Binance USDT-M Futures Testnet."""

    # Binance retired the old browser-based testnet.binancefuture.com site;
    # the REST API for Futures Demo Trading now lives at demo-fapi.binance.com.
    BASE_URL = "https://demo-fapi.binance.com"
    RECV_WINDOW = 5000

    def __init__(self, api_key: str, api_secret: str, base_url: str = None, timeout: int = 10):
        if not api_key or not api_secret:
            raise ValueError("API key and secret must both be provided.")
        self.api_key = api_key
        self.api_secret = api_secret.encode("utf-8")
        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})

    def _sign(self, params: dict) -> str:
        query_string = urlencode(params)
        signature = hmac.new(self.api_secret, query_string.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{query_string}&signature={signature}"

    def _request(self, method: str, path: str, params: dict = None, signed: bool = False):
        params = dict(params or {})
        url = f"{self.base_url}{path}"

        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["recvWindow"] = self.RECV_WINDOW
            query_string = self._sign(params)
            full_url = f"{url}?{query_string}"
            log_params = {k: v for k, v in params.items()}
            logger.debug("REQUEST %s %s | params=%s", method, path, log_params)
            try:
                response = self.session.request(method, full_url, timeout=self.timeout)
            except requests.exceptions.RequestException as exc:
                logger.error("Network error calling %s %s: %s", method, path, exc)
                raise BinanceNetworkError(str(exc)) from exc
        else:
            logger.debug("REQUEST %s %s | params=%s", method, path, params)
            try:
                response = self.session.request(method, url, params=params, timeout=self.timeout)
            except requests.exceptions.RequestException as exc:
                logger.error("Network error calling %s %s: %s", method, path, exc)
                raise BinanceNetworkError(str(exc)) from exc

        logger.debug("RESPONSE %s %s | status=%s body=%s", method, path, response.status_code, response.text)

        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text}

        if not response.ok:
            logger.error("API error %s %s | status=%s body=%s", method, path, response.status_code, payload)
            raise BinanceAPIError(response.status_code, payload)

        return payload

    # ------------------------------------------------------------------
    # Public endpoints
    # ------------------------------------------------------------------
    def ping(self):
        return self._request("GET", "/fapi/v1/ping")

    def get_symbol_price(self, symbol: str):
        return self._request("GET", "/fapi/v1/ticker/price", {"symbol": symbol})

    # ------------------------------------------------------------------
    # Signed (account) endpoints
    # ------------------------------------------------------------------
    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price: float = None):
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }
        if order_type == "LIMIT":
            params["price"] = price
            params["timeInForce"] = "GTC"

        return self._request("POST", "/fapi/v1/order", params, signed=True)

    def get_order_status(self, symbol: str, order_id: int):
        return self._request("GET", "/fapi/v1/order", {"symbol": symbol, "orderId": order_id}, signed=True)
