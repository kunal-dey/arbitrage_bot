from constants.dcx_contexts import context
from models.crypto import Crypto
from dataclasses import dataclass, field
from logging import Logger

from utils.logger import get_logger

from constants.enums.position_type import PositionType
from constants.settings import INITIAL_RETURN, INCREMENTAL_RETURN

logger: Logger = get_logger(__name__)


@dataclass
class Position:
    position_price: float
    quantity: float
    position_type: PositionType
    crypto: None | Crypto = None
    current_price: float = field(default=None, init=False)
    last_price: float = field(default=None, init=False)
    trigger: float | None = field(default=None)
    cost: float = field(default=None, init=False)

    def set_trigger(self, crypto_price: float):
        """
            in case of cumulative position the cost is given by
            cost = sum_i(b_i*q_i)/sum_i(q_i)  + sum_i(f(b_i, q_i, s))/sum_i(q_i)
            where f is an intraday function
            i -> 1 to n.
            n being the number of positions
            b_i is the buying price of the ith position
            q_i is the quantity bought for the ith position

            this can be divided in average buying price(A) + average transaction cost (B)

            Since the cumulative only have LONG as of now so the code for short selling is unchanged
        """
        global logger

        if self.position_type == PositionType.LONG:
            # this handles part A
            buy_price = self.position_price
            selling_price = crypto_price
        else:
            buy_price = crypto_price
            selling_price = self.position_price

        # this handles the B part
        tx_cost = 0

        logger.info(f"the total transaction cost for {self.crypto.crypto_name} is {tx_cost * self.quantity}")

        cost = buy_price + tx_cost
        self.cost = cost

        counter = 1
        earlier_trigger = self.trigger

        logger.info(f"current : {INITIAL_RETURN}")

        # this section iterates and finds the current trigger achieved
        logger.info(
            f"cost tracking {cost * (1 + INITIAL_RETURN + counter * INCREMENTAL_RETURN)}")
        while cost * (1 + INITIAL_RETURN + counter * INCREMENTAL_RETURN) < selling_price:
            if self.position_type == PositionType.SHORT:

                self.trigger = selling_price / (
                        1 + INITIAL_RETURN + counter * INCREMENTAL_RETURN)
            else:
                self.trigger = cost * (1 + INITIAL_RETURN + counter * INCREMENTAL_RETURN)
            counter += 1

        if earlier_trigger is not None:
            if self.position_type == PositionType.LONG:
                if crypto_price > self.trigger:
                    self.trigger = crypto_price
                if earlier_trigger > self.trigger:
                    self.trigger = earlier_trigger
                if cost * (1 + INITIAL_RETURN) > crypto_price:
                    self.trigger = None
            else:
                if crypto_price < self.trigger:
                    self.trigger = crypto_price
                if earlier_trigger < self.trigger:
                    self.trigger = earlier_trigger

    def sell(self, force=False):
        # this has been done because if there is error while selling it still says it sold
        # suppose the crypto is not even bought but still it tries to sell in that case it may fail

        logger.info(f"Selling {self.crypto.crypto_name} at {self.current_price} Quantity:{self.quantity}")
        context.create_order(PositionType.SHORT, self.crypto.crypto_name, self.crypto.quantity)

        return True

    def breached(self):
        """
            if the current price is less than the previous trigger, then it sells else it updates the trigger
        """
        global logger

        latest_price = self.crypto.current_price  # the latest price can be None or float

        if latest_price:
            self.last_price = self.current_price
            self.current_price = latest_price

        if self.current_price is None and self.last_price is None:
            return "CONTINUE"

        # if the position was long then on achieving the trigger, it should sell otherwise it should buy
        # to clear the position
        if (self.position_type == PositionType.LONG) and (self.current_price is not None):

            logger.info(f"{self.crypto.crypto_name} Earlier trigger:  {self.trigger}, latest price:{self.current_price}")
            if self.trigger is not None:
                # if it hits trigger then square off else reset a new trigger
                if self.current_price < self.trigger * (1 - INCREMENTAL_RETURN):
                    if self.sell():
                        return "SELL_PROFIT"

            self.set_trigger(self.current_price)
            return "CONTINUE"

