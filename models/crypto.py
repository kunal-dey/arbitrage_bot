from datetime import datetime
from logging import Logger
from dataclasses import dataclass, field


import pandas as pd
from dateutil.rrule import rrule, WEEKLY, MO, TU, WE, TH, FR

from constants.dcx_contexts import context
from utils.logger import get_logger

logger: Logger = get_logger(__name__)


@dataclass
class Crypto:
    crypto_name: str
    wallet: float = field(default=0.0)
    created_at: datetime = field(default=datetime.now())
    buy_price: float = field(default=0.0)
    quantity: float = field(default=0, init=False)

    @property
    def current_price(self):
        """
            returns the current price in the market or else None if the connection interrupts

            tries 4 times
        """
        try:
            price_df = pd.DataFrame(context.get_current_prices())[["market", "ask", "bid"]]
            price_df.set_index("market", inplace=True)
            return float(price_df.loc[self.crypto_name]["bid"])
        except:
            return None

    @property
    def number_of_days(self):
        """
            If today is a weekday and not a holiday, the number of days would be 1.
            If today is a weekday and a holiday, or if it's a weekend, the number of days would be 0.
        Returns:

        """
        dt_start, until = (self.created_at.date(), datetime.now().date())
        days = rrule(WEEKLY, byweekday=(MO, TU, WE, TH, FR), dtstart=dt_start, until=until).count()
        return days

