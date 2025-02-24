from logging import Logger
import numpy as np
import pandas as pd

from utils.logger import get_logger

logger: Logger = get_logger(__name__)


def predict_running_df(day_based_data, model, params):

    def get_slope(col):
        index = list(col.index)
        coefficient = np.polyfit(index, col.values, 1)
        ini = coefficient[0]*index[0]+coefficient[1]
        return coefficient[0]/ini

    mu, sigma = params
    mu = mu.iloc[:-1]
    sigma = sigma.iloc[:-1]

    def predict_stocks(min_based_data):

        # stocks_df = pd.concat([day_based_data, min_based_data.iloc[-1:]], ignore_index=True)
        stocks_df = min_based_data.copy()

        if stocks_df is None:
            return []

        col_with_period = {
            '3mo': 90,
            '2mo': 60,
            '1mo': 30,
            '3wk': 21
        }

        shifts = [sh for sh in range(3)]
        gen_cols = []

        concat_lst = []
        for shift in shifts:
            for key, val in col_with_period.items():
                gen_cols.append(f"{key}_{shift}")
                concat_lst.append(stocks_df.reset_index(drop=True).iloc[-val:].apply(get_slope))

        running_df = pd.concat(concat_lst, axis=1)
        running_df.columns = gen_cols

        running_df.dropna(inplace=True)
        running_df_s = (running_df-mu)/sigma
        running_df['prob'] = model.predict(running_df_s)
        running_df['position'] = np.where(running_df['prob'] > 0.49, 1, 0)

        selected = []
        predictions = list(running_df[running_df['position'] == 1].index)

        return predictions

    return predict_stocks
