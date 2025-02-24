from logging import Logger
from quart import Quart
from quart_cors import cors
import pandas as pd

from constants.dcx_contexts import context
from constants.enums.position_type import PositionType
from services.background_task import background_task
from utils.logger import get_logger

from datetime import datetime

from utils.training_modules.trained_model import train_model

app = Quart(__name__)
app.config["PROPAGATE_EXCEPTIONS"] = True
app = cors(app, allow_origin="*")

logger: Logger = get_logger(__name__)


@app.get("/")
async def home():
    """
    home route
    :return:
    """
    return {"message": "Welcome to the Coindcx trading system"}


@app.route("/time")
def get_time():
    return {"current_time": datetime.now()}


@app.get("/start")
async def start_process():
    """
    route checks whether login has been done and then starts the background task
    :return:
    """
    # starting the background task which will run the entire process
    app.add_background_task(background_task)
    return {"message": "Background process started"}

@app.get("/square_off")
async def square_off():
    for currency in context.user_balance():
        if currency["balance"] > 0:
            context.create_order(PositionType.SHORT, f"{currency["currency"]}INR", currency["balance"])
    return {"message": "all currencies have been sold", "data": context.user_balance()}

@app.get("/train")
async def train():
    async def training():
        yahoo_cryptos = context.get_yahoo_symbols()
        train_model(yahoo_cryptos)

    # starting the training process
    app.add_background_task(training)
    return {"message": "Training started"}


if __name__ == "__main__":
    app.run(port=8081)
