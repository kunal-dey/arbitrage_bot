import hmac
import hashlib
import json
import time
from logging import Logger
import re

import requests

from constants.dcx_credentials import API_KEY, API_SECRET
from constants.enums.position_type import PositionType
from utils.logger import get_logger


logger: Logger = get_logger(__name__)

class DcxContexts:
    def __init__(self):
        self.BASE_URL = "https://api.coindcx.com"
        self.PUBLIC_URL = "https://public.coindcx.com"
        self._get_active_markets = None

    @property
    def market_details_url(self):
        return f"{self.BASE_URL}/exchange/v1/markets_details"

    @property
    def current_prices_url(self):
        return f"{self.BASE_URL}/exchange/ticker"

    @property
    def recent_trades(self):
        return f"{self.PUBLIC_URL}/market_data/trade_history"

    @property
    def active_markets(self):
        return f"{self.BASE_URL}/exchange/v1/markets"

    @property
    def order_books(self):
        return f"{self.PUBLIC_URL}/market_data/orderbook"

    @property
    def candles(self):
        return f"{self.PUBLIC_URL}/market_data/candles"

    @property
    def user_balance_url(self):
        return f"{self.BASE_URL}/exchange/v1/users/balances"

    @property
    def create_order_url(self):
        return f"{self.BASE_URL}/exchange/v1/orders/create"

    @staticmethod
    def get_response(endpoint_url, method='GET', payload=None):
        secret_bytes = bytes(API_SECRET, encoding='utf-8')
        json_body = json.dumps(payload)
        signature = hmac.new(secret_bytes, json_body.encode(), hashlib.sha256).hexdigest()

        headers = {
            'Content-Type': 'application/json',
            'X-AUTH-APIKEY': API_KEY,
            'X-AUTH-SIGNATURE': signature
        }

        response = requests.request(method=method, url=endpoint_url, data=json_body, headers=headers)
        # response = requests.post(endpoint_url, data = json_body, headers = headers)
        return response.json()

    def get_active_markets(self):
        self.get_yahoo_symbols()
        return self._get_active_markets

    def user_balance(self):
        timestamp = int(round(time.time() * 1000))

        body = {
            'timestamp': timestamp
        }
        return self.get_response(self.user_balance_url, method='POST', payload=body)

    def get_yahoo_symbols(self):
        common_symbols = ["INR"]
        filtered_pairs = []
        new_pairs = []
        market_details = self.get_market_details()
        for pair in self.get_response(self.active_markets, "GET"):
            for currency in common_symbols:
                filtered_pair = list(filter(lambda x: x["coindcx_name"] == pair and "market_order" in x["order_types"], market_details))
                if len(filtered_pair) > 0:
                    trimmed_currency = currency[:-1] if currency == "USDT" else currency
                    if pair.startswith(currency):
                        filtered_pairs.append(pair)
                        new_pairs.append(f"{trimmed_currency}-{pair[len(currency):]}")
                    elif pair.endswith(currency):
                        new_pairs.append(f"{pair[:-len(currency)]}-{trimmed_currency}")
                        filtered_pairs.append(pair)
        self._get_active_markets = filtered_pairs
        return new_pairs

    def get_market_details(self):
        return self.get_response(self.market_details_url, method='GET')

    def get_current_prices(self):
        # return list(filter(lambda x: "INR" in x["market"] and "_" not in x["market"], self.get_response(self.current_prices_url)))
        return self.get_response(self.current_prices_url)

    def create_order(self, position:PositionType, symbol:str, quantity:int, rounding=None):
        timestamp = int(round(time.time() * 1000))

        body = {
            "side": position.value,  # Toggle between 'buy' or 'sell'.
            "order_type": "market_order",  # Toggle between a 'market_order' or 'limit_order'.
            "market": symbol,  # Replace 'SNTBTC' with your desired market pair.
            "total_quantity": round(float(quantity), rounding) if rounding is not None else float(quantity),  # Replace this with the quantity you want
            "timestamp": timestamp
            # "client_order_id": "kd_2206_01"  # Replace this with the client order id you want
        }

        response = self.get_response(self.create_order_url, method='POST', payload=body)
        logger.info(f"response -> {response}")

        if "orders" not in response.keys():
            if response["code"] != 200 and "precision should be" in response["message"]:
                message = response.get("message", "")
                match = re.search(r'(\d+)', message)
                rounding_value = int(match.group(1)) if match else None
                if rounding_value is not None:
                    return self.create_order(PositionType.LONG, symbol, quantity, rounding=rounding_value)

        return response

context = DcxContexts()