from logging import Logger

import yfinance as yf
import pandas as pd

import numpy as np
from utils.logger import get_logger

logger: Logger = get_logger(__name__)


def generate_data(stock_df):
    """
        stock_df should contain price as one column
    """

    def get_slope(col):
        index = list(col.index)
        coefficient = np.polyfit(index, col.values, 1)
        ini = coefficient[0]*index[0]+coefficient[1]
        return coefficient[0]/ini

    def position(x):
        """
        given a series it finds whether there was increase of given value eg 1.05
        :param x:
        :return:
        """
        returns = (x.pct_change()+1).cumprod()
        return 0 if returns[returns > 1.06].shape[0] == 0 else 1

    col_with_period = {
        '3mo': 90,
        '2mo': 60,
        '1mo': 30,
        '3wk': 21
    }

    shifts = [sh for sh in range(3)]
    gen_cols = []

    for shift in shifts:
        for key, val in col_with_period.items():
            gen_cols.append(f"{key}_{shift}")
            stock_df.insert(
                len(stock_df.columns),
                f"{key}_{shift}",
                stock_df.reset_index(drop=True).shift(shift).price.rolling(val).apply(get_slope).values
            )

    stock_df.insert(
                len(stock_df.columns),
                'dir',
                stock_df.reset_index(drop=True).price.shift(-14).rolling(14).apply(lambda x: position(x)).values
            )
    gen_cols.append("dir")

    return stock_df[gen_cols].dropna()


def training_data(tickers: list):
    """
    non_be_tickers: this should contain the list of all non -BE stocks to start with
    :return:
    """

    stocks_df = yf.download(tickers=tickers, interval='1d', period='6mo')
    stocks_df.index = pd.to_datetime(stocks_df.index)
    # stocks_df = stocks_df.loc[:TRAINING_DATE]
    stocks_df = stocks_df['Close'].bfill().ffill().dropna(axis=1)

    stocks_list = list(stocks_df.columns)

    # generating the dataframe having both the input and output

    data_df = None
    for st in stocks_list:
        stock_df = stocks_df[[st]]
        stock_df.columns = ['price']
        if data_df is not None:
            data_df = pd.concat([data_df, generate_data(stock_df)]).reset_index(drop=True)
        else:
            data_df = generate_data(stock_df)
    return data_df

