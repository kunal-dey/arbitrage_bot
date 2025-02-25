from dataclasses import dataclass, field
from logging import Logger

from constants.enums.position_type import PositionType

from constants.settings import get_allocation
from models.position import Position
from models.crypto import Crypto
from utils.logger import get_logger
from constants.dcx_contexts import context

logger: Logger = get_logger(__name__)


def get_available_cash():
    return float(list(filter(lambda x: x["currency"] == "INR", context.user_balance()))[0]["balance"])


@dataclass
class Account:
    cryptos_to_track: dict[str, Crypto] = field(default_factory=dict, init=False)
    positions: dict[str, Position] = field(default_factory=dict, init=False)
    available_cash: float = field(default_factory=get_available_cash)
    starting_cash: float = field(default_factory=get_available_cash)
    cryptos_to_add: dict = field(default_factory=dict, init=False)

    def add_crypto(self):
        """
        if it satisfies all the buying criteria then it buys the stock
        :return: None
        """
        cryptos_to_delete = []

        # adding cryptos to the cryptos_to_track
        for currency in context.user_balance():
            if currency.get("currency") != "INR"  and currency.get("balance") > 0:
                if f"{currency.get("currency")}INR" not in self.cryptos_to_track.keys():
                    crypto = Crypto(crypto_name=f"{currency.get("currency")}INR")
                    crypto.quantity = currency.get("balance")
                    try:
                        crypto.buy_price = self.cryptos_to_add[crypto.crypto_name]
                        del self.cryptos_to_add[crypto.crypto_name]
                        self.cryptos_to_track[crypto.crypto_name] = crypto
                    except:
                        logger.info(f"Crypto {crypto.crypto_name} not found, skipping")
                else:
                    # update the quantity
                    self.cryptos_to_track[f"{currency.get("currency")}INR"].quantity = currency.get("balance")
                    self.positions[f"{currency.get("currency")}INR"].quantity = currency.get("balance")
                    self.positions[f"{currency.get("currency")}INR"].crypto = self.cryptos_to_track[f"{currency.get("currency")}INR"]


        # adding them as position
        for crypto_key in list(self.cryptos_to_track.keys()):
            if crypto_key not in list(self.positions.keys()):
                self.positions[crypto_key] = Position(
                    position_price=self.cryptos_to_track[crypto_key].buy_price,
                    crypto=self.cryptos_to_track[crypto_key],
                    position_type=PositionType.LONG,
                    quantity=self.cryptos_to_track[crypto_key].quantity
                )

