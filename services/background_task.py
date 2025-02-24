import os
import pickle
from asyncio import sleep
from itertools import combinations
from logging import Logger
import pandas as pd
import yfinance as yf
from datetime import datetime

from keras.src.saving import load_model

from constants.enums.position_type import PositionType
from constants.settings import SLEEP_INTERVAL, get_old_date, update_old_date, get_allocation
from models.account import Account
from models.position import Position
from utils.logger import get_logger
from constants.dcx_contexts import context
from utils.precision_based_amount import find_best_amount
from utils.select_stocks import predict_running_df

logger: Logger = get_logger(__name__)


async def background_task():
    """
        all the tasks mentioned here will be running in the background
    """
    global logger

    logger.info("BACKGROUND TASK STARTED")

    logger.info(f"starting amount {float(
        list(filter(lambda x: x["currency"] == "INR", context.user_balance()))[0]["balance"])}")

    account: Account = Account()

    model = load_model(os.getcwd() + "/temp/DNN_model.h5")

    logger.info(f"model loaded: {model}")

    params = pickle.load(open(os.getcwd() + "/temp/params.pkl", "rb"))

    logger.info(f"mu and sigma loaded: {params}")
    predicted_stocks = []

    while True:
        await sleep(SLEEP_INTERVAL)
        logger.info(get_old_date())

        if datetime.now().date() > get_old_date():
            yahoo_cryptos = context.get_yahoo_symbols()

            try:
                prediction_df = \
                    yf.download(tickers=yahoo_cryptos, period='1mo', interval='1d')['Close']
                prediction_df = prediction_df.ffill().bfill()
                prediction_df.index = pd.to_datetime(prediction_df.index)
                prediction_df = prediction_df.loc[:str(datetime.now().date())]
                prediction_df.dropna(axis=1, inplace=True)
                prediction_df.reset_index(drop=True, inplace=True)
                prediction_df.columns = prediction_df.columns.str.replace('-', '')
                prediction_df.to_csv(f"temp/prediction_df.csv")
            except:
                try:
                    prediction_df = pd.read_csv(f"temp/prediction_df.csv", index_col=0)
                except:
                    prediction_df = None

            logger.info(f"prediction_df: {prediction_df}")

            update_old_date(datetime.now().date())

            predict_stocks = predict_running_df(prediction_df, model, params)

            data_resampled = prediction_df.iloc[::60, :]
            log_returns = data_resampled.pct_change()
            var_95 = log_returns.quantile(0.005, interpolation='lower')

            stock_list = predict_stocks(prediction_df)
            predicted_stocks = list(var_95[stock_list].sort_values(ascending=False).index)

        logger.info(f"predicted_stocks: {predicted_stocks}")

        # find out all the pairs where the currency of the predicted stock is present

        market_details_df = pd.DataFrame(context.get_market_details())[
            ["coindcx_name", "order_types", "min_quantity", "target_currency_precision", "step"]]

        def find_pairs(row):
            for pred_st in predicted_stocks:
                if pred_st[:-3] in row["coindcx_name"] or "INR" in row["coindcx_name"]:
                    return 1
            return 0

        market_details_df["contains"] = market_details_df.apply(
            find_pairs,
            axis=1)
        market_crypto_list = market_details_df[market_details_df["contains"] > 0]["coindcx_name"].to_list()
        logger.info(f"market crypto list {market_crypto_list}")

        available_symbols = []
        for pair in market_crypto_list:
            if "INR" in pair:
                if pair.startswith("INR"):
                    available_symbols.append(pair[len("INR"):])
                elif pair.endswith("INR"):
                    available_symbols.append(pair[:-len("INR")])

        # check whether all permutation present or not  if not remove that symbol
        combinations_list = list(combinations(available_symbols, 2))
        new_combinations_list = []
        for combination in combinations_list:
            if (f"{combination[0]}{combination[1]}" in market_crypto_list) or (
                    f"{combination[1]}{combination[0]}" in market_crypto_list):
                new_combinations_list.append(combination)

        # get pair list
        pair_list = {}
        for combination in new_combinations_list:
            single_pair = []
            if f"{combination[0]}{combination[1]}" in market_crypto_list:
                single_pair.append(f"{combination[0]}{combination[1]}")
            elif f"{combination[1]}{combination[0]}" in market_crypto_list:
                single_pair.append(f"{combination[1]}{combination[0]}")

            if f"{combination[0]}INR" in market_crypto_list:
                single_pair.append(f"{combination[0]}INR")
            elif f"INR{combination[0]}" in market_crypto_list:
                single_pair.append(f"INR{combination[0]}")

            if f"{combination[1]}INR" in market_crypto_list:
                single_pair.append(f"{combination[1]}INR")
            elif f"INR{combination[1]}" in market_crypto_list:
                single_pair.append(f"INR{combination[1]}")

            pair_list[combination] = single_pair

        price_df = pd.DataFrame(context.get_current_prices())[["market", "ask", "bid"]]
        price_df.set_index("market", inplace=True)

        market_details_df.set_index("coindcx_name", inplace=True)

        # check whether min quantity can be bought or not
        for currency in context.user_balance():
            if currency.get("currency") == "INR":
                account.available_cash = currency.get("balance")

        cryptos_to_add = {}

        logger.info(pair_list)

        for pair_key, list_to_test in pair_list.items():

            inr_pair, non_inr_pair = None, None
            first_buy_pair, second_buy_pair = None, None

            if f"{pair_key[0]}{pair_key[1]}" in list_to_test:
                inr_pair, non_inr_pair = f"{pair_key[1]}INR", f"{pair_key[0]}{pair_key[1]}"
                first_buy_pair, second_buy_pair = pair_key[1], pair_key[0]

            elif f"{pair_key[1]}{pair_key[0]}" in list_to_test:
                inr_pair, non_inr_pair = f"{pair_key[0]}INR", f"{pair_key[1]}{pair_key[0]}"
                first_buy_pair, second_buy_pair = pair_key[0], pair_key[1]

            inr_pair_value = float(price_df.loc[inr_pair]["ask"])
            non_inr_pair_value = float(price_df.loc[non_inr_pair]["ask"])
            inr_pair_precision = int(market_details_df.loc[inr_pair]["target_currency_precision"])
            non_inr_pair_precision = int(market_details_df.loc[non_inr_pair]["target_currency_precision"])
            min_possible_inr_pair_quantity = float(market_details_df.loc[inr_pair]["min_quantity"])
            min_possible_non_inr_pair_quantity = float(market_details_df.loc[non_inr_pair]["min_quantity"])
            amount = find_best_amount(inr_pair_value, non_inr_pair_value, inr_pair_precision, non_inr_pair_precision,
                                      min_possible_inr_pair_quantity=min_possible_inr_pair_quantity,
                                      min_possible_non_inr_pair_quantity=min_possible_non_inr_pair_quantity)

            if amount > account.available_cash:
                continue

            inr_pair_quantity = amount / inr_pair_value
            non_inr_pair_quantity = inr_pair_quantity / non_inr_pair_value

            if inr_pair_quantity > min_possible_inr_pair_quantity and non_inr_pair_quantity > min_possible_non_inr_pair_quantity:
                price_df = pd.DataFrame(context.get_current_prices())[["market", "ask", "bid"]]
                price_df.set_index("market", inplace=True)

                if float(price_df.loc[non_inr_pair]["bid"]) * float(
                        price_df.loc[inr_pair]["bid"]) > float(price_df.loc[f"{second_buy_pair}INR"]["ask"]):
                    if f"{second_buy_pair}INR" in predicted_stocks:
                        logger.info(f"arbitrage for {first_buy_pair} {second_buy_pair}")
                        if f"{second_buy_pair}INR" not in account.cryptos_to_track.keys():
                            buying_price = float(price_df.loc[f"{second_buy_pair}INR"]["ask"]) * 1.005
                            buying_quantity = amount / float(price_df.loc[f"{second_buy_pair}INR"]["ask"])
                            logger.info(f"buying pair {second_buy_pair}INR")
                            response = context.create_order(PositionType.LONG, f"{second_buy_pair}INR", buying_quantity, buying_price, order_type="limit_order")
                            account.available_cash -= get_allocation()

                            if response is not None and "orders" in response.keys():
                                logger.info(f"actual buy for {second_buy_pair}INR")
                                cryptos_to_add[f"{second_buy_pair}INR"] = float(price_df.loc[f"{second_buy_pair}INR"]["ask"])


        try:
            # logic to buy any coin which might have arbitrage benefit

            account.add_crypto()
            account.cryptos_to_add.update(cryptos_to_add)

            positions_to_delete = []  # this is needed or else it will alter the length during loop

            for position_name in account.positions.keys():
                position: Position = account.positions[position_name]
                status = position.breached()
                match status:
                    case "SELL_PROFIT":
                        logger.info(f" profit -->sell {position.crypto.crypto_name} at {position.crypto.current_price}")
                        # if its in holding then fund is added next day else for position its added same day
                        positions_to_delete.append(position_name)

                    case "CONTINUE":
                        continue

            for position_name in positions_to_delete:
                del account.positions[position_name]
                del account.cryptos_to_track[position_name]  # delete from stocks to track



        except:
            logger.exception("Kite error may have happened")